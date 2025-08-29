# Oracle Free Tier Instance Creation (Docker & Podman)

This project automates the creation of Oracle Cloud Free Tier compute instances using containerization. It is designed to run continuously, polling the OCI API until an instance is successfully provisioned.

All configuration and credentials are managed via mounted files for security and portability.

## Features

- **Automated Instance Creation**: Automatically polls OCI until a free tier instance (ARM A1 or x86 Micro) is successfully provisioned.
- **Resilient**: Designed to run for long periods. It is resilient to transient network errors and temporary OCI API issues, retrying automatically.
- **Notifications**: Sends real-time status notifications to a Discord webhook (optional).
- **Secure**: Manages all credentials and sensitive files through read-only volume mounts, ensuring they are not stored in the container image.

## Prerequisites

- [Docker](https://www.docker.com/get-started) or [Podman](https://podman.io/) installed on your system.
- An Oracle Cloud account with the required API credentials.
- The following files created in your project directory:
  - `oci.env`: Contains environment variables for the script. See `oci.env.example` for a full list of options, including compute shape, image ID, and the optional `DISCORD_WEBHOOK` URL.
  - `oci_config`: Your Oracle Cloud Infrastructure config file.
  - `oci_api_private_key.pem`: The private API key associated with your OCI user.
  - `ssh_public_key.pub`: The SSH public key to be installed on the created instance.

## Usage with Docker

You do **not** need to build the image yourself. To launch the script, use the public Docker image provided on GitHub Container Registry.

Create a `docker-compose.yml` file with the following content:

```yaml
services:
  oracle-freetier:
    image: ghcr.io/nyamort/oracle-freetier-instance-creation:latest
    container_name: oci-vm-creator
    volumes:
      - ./oci.env:/app/oci.env:ro
      - ./oci_config:/app/oci_config:ro
      - ./oci_api_private_key.pem:/app/oci_api_private_key.pem:ro
      - ./ssh_public_key.pub:/app/ssh_public_key.pub:ro
    environment:
      - OCI_ENV_FILE=/app/oci.env
```

Then, simply run:

```bash
docker-compose up
```

## Usage with Podman

If you prefer to use Podman, you can use one of the provided scripts.

**For Linux/macOS:**

```bash
./run_podman.sh
```

**For Windows:**

```powershell
.\run_podman.ps1
```

These scripts are direct equivalents of the `docker-compose` command.

## Development

If you are developing the script and want to test local changes to `main.py` without rebuilding the container image, you can bind mount your local `main.py` file.

**For Docker:**

Add the following line to the `volumes` section in your `docker-compose.yml`:

```yaml
      - ./main.py:/app/main.py:ro
```

**For Podman:**

The provided `run_podman.sh` and `run_podman.ps1` scripts already include the mount for `main.py`. If you need to remove it for production-like testing, you can delete the following part from the script:

```bash
-v ./main.py:/app/main.py:ro,z
```