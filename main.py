import configparser
import itertools
import json
import os
import smtplib
import sys
import time
from pathlib import Path
from typing import Union
import time

import oci
import paramiko
from dotenv import load_dotenv
import requests


# Load environment variables from .env file
load_dotenv('oci.env')

ARM_SHAPE = "VM.Standard.A1.Flex"
E2_MICRO_SHAPE = "VM.Standard.E2.1.Micro"

# Access loaded environment variables and strip white spaces
OCI_CONFIG = os.getenv("OCI_CONFIG", "").strip()
OCT_FREE_AD = os.getenv("OCT_FREE_AD", "").strip()
DISPLAY_NAME = os.getenv("DISPLAY_NAME", "").strip()
WAIT_TIME = int(os.getenv("REQUEST_WAIT_TIME_SECS", "30").strip())
SSH_PUNLIC_KEY_FILE = os.getenv("SSH_PUNLIC_KEY_FILE", "").strip()
OCI_IMAGE_ID = os.getenv("OCI_IMAGE_ID", None).strip() if os.getenv("OCI_IMAGE_ID") else None
OCI_COMPUTE_SHAPE = os.getenv("OCI_COMPUTE_SHAPE", ARM_SHAPE).strip()
SECOND_MICRO_INSTANCE = os.getenv("SECOND_MICRO_INSTANCE", 'False').strip().lower() == 'true'
OCI_SUBNET_ID = os.getenv("OCI_SUBNET_ID", None).strip() if os.getenv("OCI_SUBNET_ID") else None
OPERATING_SYSTEM = os.getenv("OPERATING_SYSTEM", "").strip()
OS_VERSION = os.getenv("OS_VERSION", "").strip()
ASSIGN_PUBLIC_IP = os.getenv("ASSIGN_PUBLIC_IP", "false").strip()
BOOT_VOLUME_SIZE = os.getenv("BOOT_VOLUME_SIZE", "50").strip()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

def send_discord_message(message):
    if DISCORD_WEBHOOK:
        payload = {"content": message}
        try:
            response = requests.post(DISCORD_WEBHOOK, json=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to send Discord message: {e}")

iam_client = None
network_client = None
compute_client = None
OCI_USER_ID = None

def init_oci_clients():
    global iam_client, network_client, compute_client, OCI_USER_ID
    # Set up OCI Config and Clients
    config = oci.config.from_file(OCI_CONFIG)
    iam_client = oci.identity.IdentityClient(config)
    network_client = oci.core.VirtualNetworkClient(config)
    compute_client = oci.core.ComputeClient(config)
    OCI_USER_ID = config.get('user')

IMAGE_LIST_KEYS = [
    "lifecycle_state",
    "display_name",
    "id",
    "operating_system",
    "operating_system_version",
    "size_in_mbs",
    "time_created",
]

def write_into_file(file_path, data):
    with open(file_path, mode="a", encoding="utf-8") as file_writer:
        file_writer.write(data)


def list_all_instances(compartment_id):
    list_instances_response = compute_client.list_instances(compartment_id=compartment_id)
    return list_instances_response.data

def check_instance_state_and_write(compartment_id, shape, states=('RUNNING', 'PROVISIONING'), tries=3):
    for _ in range(tries):
        instance_list = list_all_instances(compartment_id=compartment_id)
        if shape == ARM_SHAPE:
            running_arm_instance = next((instance for instance in instance_list if
                                         instance.shape == shape and instance.lifecycle_state in states), None)
            if running_arm_instance:
                create_instance_details_file_and_notify(running_arm_instance, shape)
                return True
        else:
            micro_instance_list = [instance for instance in instance_list if
                                   instance.shape == shape and instance.lifecycle_state in states]
            if len(micro_instance_list) > 1 and SECOND_MICRO_INSTANCE:
                create_instance_details_file_and_notify(micro_instance_list[-1], shape)
                return True
            if len(micro_instance_list) == 1 and not SECOND_MICRO_INSTANCE:
                create_instance_details_file_and_notify(micro_instance_list[-1], shape)
                return True
        if tries - 1 > 0:
            time.sleep(60)

    return False


def execute_oci_command(client, method, *args, **kwargs):
    while True:
        try:
            response = getattr(client, method)(*args, **kwargs)
            data = response.data if hasattr(response, "data") else response
            return data
        except oci.exceptions.ServiceError as srv_err:
            data = {"status": srv_err.status,
                    "code": srv_err.code,
                    "message": srv_err.message}
            send_discord_message(
                f"❗️ Error encountered while executing OCI command: {method}\n"
                f"Status: {data['status']}, Code: {data['code']}, Message: {data['message']}"
            )


def read_ssh_public_key(public_key_file: Union[str, Path]):
    public_key_path = Path(public_key_file)

    if not public_key_path.is_file():
        raise FileNotFoundError(f"SSH public key file not found: {public_key_path}")

    with open(public_key_path, "r", encoding="utf-8") as pub_key_file:
        ssh_public_key = pub_key_file.read()

    return ssh_public_key


def launch_instance():
    # Step 1 - Get TENANCY
    #user_info = execute_oci_command(iam_client, "get_user", OCI_USER_ID)
    user_info = iam_client.get_user(OCI_USER_ID).data
    oci_tenancy = user_info.compartment_id

    # Step 2 - Get AD Name
    availability_domains = execute_oci_command(iam_client,
                                               "list_availability_domains",
                                               compartment_id=oci_tenancy)
    oci_ad_name = [item.name for item in availability_domains if
                   any(item.name.endswith(oct_ad) for oct_ad in OCT_FREE_AD.split(","))]
    oci_ad_names = itertools.cycle(oci_ad_name)

    # Step 3 - Get Subnet ID
    oci_subnet_id = OCI_SUBNET_ID
    if not oci_subnet_id:
        subnets = execute_oci_command(network_client,
                                      "list_subnets",
                                      compartment_id=oci_tenancy)
        oci_subnet_id = subnets[0].id

    # Step 4 - Get Image ID of Compute Shape
    if not OCI_IMAGE_ID:
        images = execute_oci_command(
            compute_client,
            "list_images",
            compartment_id=oci_tenancy,
            shape=OCI_COMPUTE_SHAPE,
        )
        shortened_images = [{key: json.loads(str(image))[key] for key in IMAGE_LIST_KEYS
                             } for image in images]
        write_into_file('images_list.json', json.dumps(shortened_images, indent=2))
        oci_image_id = next(image.id for image in images if
                            image.operating_system == OPERATING_SYSTEM and
                            image.operating_system_version == OS_VERSION)
    else:
        oci_image_id = OCI_IMAGE_ID

    assign_public_ip = ASSIGN_PUBLIC_IP.lower() in [ "true", "1", "y", "yes" ]

    boot_volume_size = max(50, int(BOOT_VOLUME_SIZE))

    ssh_public_key = read_ssh_public_key(SSH_PUNLIC_KEY_FILE)

    # Step 5 - Launch Instance if it's not already exist and running
    instance_exist_flag = check_instance_state_and_write(oci_tenancy, OCI_COMPUTE_SHAPE, tries=1)

    if OCI_COMPUTE_SHAPE == "VM.Standard.A1.Flex":
        shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=4, memory_in_gbs=24)
    else:
        shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=1, memory_in_gbs=1)

    while not instance_exist_flag:
        time.sleep(WAIT_TIME)
        try:
            launch_instance_response = compute_client.launch_instance(
                launch_instance_details=oci.core.models.LaunchInstanceDetails(
                    availability_domain=next(oci_ad_names),
                    compartment_id=oci_tenancy,
                    create_vnic_details=oci.core.models.CreateVnicDetails(
                        assign_public_ip=assign_public_ip,
                        assign_private_dns_record=True,
                        display_name=DISPLAY_NAME,
                        subnet_id=oci_subnet_id,
                    ),
                    display_name=DISPLAY_NAME,
                    shape=OCI_COMPUTE_SHAPE,
                    availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(
                        recovery_action="RESTORE_INSTANCE"
                    ),
                    instance_options=oci.core.models.InstanceOptions(
                        are_legacy_imds_endpoints_disabled=False
                    ),
                    shape_config=shape_config,
                    source_details=oci.core.models.InstanceSourceViaImageDetails(
                        source_type="image",
                        image_id=oci_image_id,
                        boot_volume_size_in_gbs=boot_volume_size,
                    ),
                    metadata={
                        "ssh_authorized_keys": ssh_public_key},
                )
            )
            if launch_instance_response.status == 200:
                instance_exist_flag = check_instance_state_and_write(oci_tenancy, OCI_COMPUTE_SHAPE)

        except oci.exceptions.ServiceError as srv_err:
            if srv_err.code == "LimitExceeded":
                instance_exist_flag = check_instance_state_and_write(oci_tenancy, OCI_COMPUTE_SHAPE)
                if instance_exist_flag:
                    sys.exit()
            data = {
                "status": srv_err.status,
                "code": srv_err.code,
                "message": srv_err.message,
            }
            send_discord_message(
                f"❗️ Error encountered while launching instance: {data['code']}\n"
                f"Status: {data['status']}, Message: {data['message']}"
            )



def create_instance_details_file_and_notify(instance, shape):
    instance_details = {
        "display_name": instance.display_name,
        "shape": instance.shape,
        "id": instance.id,
        "lifecycle_state": instance.lifecycle_state,
        "time_created": str(instance.time_created),
    }
    file_name = f"instance_details_{shape.replace('.', '_')}.json"
    with open(file_name, "w") as f:
        json.dump(instance_details, f, indent=4)

    send_discord_message(
        f"✅ Great news! An instance with shape `{shape}` is now available."
        f"Details saved to `{file_name}`."
    )


if __name__ == "__main__":
    init_oci_clients()
    send_discord_message("🚀 OCI Instance Creation Script: Starting up! Let's create some cloud magic!")
    try:
        launch_instance()
        send_discord_message("🎉 Success! OCI Instance has been created. Time to celebrate!")
    except Exception as e:
        error_message = f"😱 Oops! Something went wrong with the OCI Instance Creation Script:\n{str(e)}"
        send_discord_message(error_message)
        raise

