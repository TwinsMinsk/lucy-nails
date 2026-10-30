FROM postgres:17

RUN apt-get update \
    && apt-get install -y --no-install-recommends awscli ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

# AWS CLI 2.23+ adds CRC64NVME headers by default, which S3-compatible storage
# does not always document. Archives are verified by their own SHA-256 files.
ENV AWS_REQUEST_CHECKSUM_CALCULATION=when_required \
    AWS_RESPONSE_CHECKSUM_VALIDATION=when_required

WORKDIR /app
COPY scripts/ops/backup_postgres.py /app/backup_postgres.py
COPY scripts/ops/restore_postgres.py /app/restore_postgres.py

CMD ["python3", "/app/backup_postgres.py", "--output-dir", "/tmp/backups"]
