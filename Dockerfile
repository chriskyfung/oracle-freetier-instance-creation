FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV OCI_CONFIG=/app/oci_config
ENV SSH_PUNLIC_KEY_FILE=/app/ssh_public_key.pub

CMD ["python", "main.py"]
