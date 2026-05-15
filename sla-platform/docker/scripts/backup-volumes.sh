#!/bin/bash
# Docker volume backup — archives all named volumes to host directory.
# Usage: ./backup-volumes.sh [backup_dir]
# Default backup_dir: /data/backups/volumes

set -euo pipefail

BACKUP_DIR="${1:-/data/backups/volumes}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE_PROJECT="${COMPOSE_PROJECT:-sla-platform}"

mkdir -p "$BACKUP_DIR"

VOLUMES=$(docker volume ls --filter "name=${COMPOSE_PROJECT}" --format "{{.Name}}")

if [ -z "$VOLUMES" ]; then
    echo "No volumes found for project '$COMPOSE_PROJECT'"
    exit 0
fi

for volume in $VOLUMES; do
    echo "Backing up volume: $volume"
    docker run --rm \
        -v "$volume:/source" \
        -v "$BACKUP_DIR:/backup" \
        alpine:3.19 \
        tar czf "/backup/${volume}_${TIMESTAMP}.tar.gz" -C /source .
done

echo "Removing volume backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "*.tar.gz" -type f -mtime "+$RETENTION_DAYS" -delete

echo "Volume backups complete: $BACKUP_DIR"
