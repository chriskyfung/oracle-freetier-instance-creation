# Oracle Free Tier Instance Creation (Docker Only)

This project automates the creation of Oracle Cloud Free Tier compute instances using Docker. All configuration and credentials are managed via mounted files for security and portability.

## Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your system
- Oracle Cloud account with required API credentials
- The following files in your project directory:
  - `oci.env`: Environment variables for OCI
  - `oci_config`: Oracle Cloud Infrastructure config file
  - `oci_api_private_key.pem`: Private API key
  - `ssh_public_key.pub`: SSH public key for instance access

## Usage with Public Docker Image

You do **not** need to build the image yourself. To launch the script, use the public Docker image provided on GitHub Container Registry.

Create a `docker-compose.yml` file with the following content:

```yaml
services:
  oracle-freetier:
    image: ghcr.io/nyamort/oracle-freetier-instance-creation:latest
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