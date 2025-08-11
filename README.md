# Oracle Free Tier Instance Creation (Docker & Podman)

This project automates the creation of Oracle Cloud Free Tier compute instances using containerization. All configuration and credentials are managed via mounted files for security and portability.

## Prerequisites

- [Docker](https://www.docker.com/get-started) or [Podman](https://podman.io/) installed on your system.
- Oracle Cloud account with required API credentials.
- The following files in your project directory:
  - `oci.env`: Environment variables for OCI
  - `oci_config`: Oracle Cloud Infrastructure config file
  - `oci_api_private_key.pem`: Private API key
  - `ssh_public_key.pub`: SSH public key for instance access

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
