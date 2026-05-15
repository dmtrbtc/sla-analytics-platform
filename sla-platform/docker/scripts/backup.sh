#!/bin/bash
# PostgreSQL database backup with retention rotation.
# Usage: ./backup.sh [backup_dir]
# Default backup_dir: /data/backups/postgres

set -euo pipefail

BACKUP_DIR="${1:-/data/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-sla_platform}"
DB_USER="${DB_USER:-sla_user}"
DB_PASSWORD="${DB_PASSWORD:-sla_password}"

mkdir -p "$BACKUP_DIR"

export PGPASSWORD="$DB_PASSWORD"

echo "Backing up $DB_NAME to $BACKUP_DIR/backup_$TIMESTAMP.sql.gz"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/backup_$TIMESTAMP.dump"

echo "Generating plain SQL backup"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl \
    | gzip > "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

echo "Removing backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "backup_*.dump" -type f -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime "+$RETENTION_DAYS" -delete

echo "Backup complete: $BACKUP_DIR/backup_$TIMESTAMP"
