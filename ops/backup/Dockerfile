FROM postgres:15

RUN apt-get update \
    && apt-get install -y --no-install-recommends awscli ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY scripts/ops/backup_postgres.py /app/backup_postgres.py
COPY scripts/ops/restore_postgres.py /app/restore_postgres.py

CMD ["python3", "/app/backup_postgres.py", "--output-dir", "/tmp/backups"]
