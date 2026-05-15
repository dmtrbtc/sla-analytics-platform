#!/bin/bash
# PostgreSQL database restore from pg_dump custom format.
# Usage: ./restore.sh <backup_file.dump> [target_db]
#   backup_file.dump: path to pg_dump custom-format backup
#   target_db: database to restore into (default: sla_platform)

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.dump> [target_db]"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${2:-sla_platform}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-sla_user}"
DB_PASSWORD="${DB_PASSWORD:-sla_password}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: backup file not found: $BACKUP_FILE"
    exit 1
fi

export PGPASSWORD="$DB_PASSWORD"

echo "WARNING: This will DROP and recreate the '$DB_NAME' database."
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "Terminating existing connections to $DB_NAME"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres <<SQL
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
SQL

echo "Dropping database $DB_NAME"
dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

echo "Creating database $DB_NAME"
createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

echo "Restoring from $BACKUP_FILE"
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl \
    --exit-on-error \
    "$BACKUP_FILE"

echo "Restore complete: $BACKUP_FILE -> $DB_NAME"
