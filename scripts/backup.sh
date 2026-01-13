#!/bin/bash
# Second Brain - Backup Script
# Usage: bash backup.sh

set -e

BACKUP_DIR="${HOME}/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Creating backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup CouchDB data
docker exec secondbrain-couchdb tar czf /tmp/couchdb-backup.tar.gz /opt/couchdb/data
docker cp secondbrain-couchdb:/tmp/couchdb-backup.tar.gz "$BACKUP_DIR/couchdb-$DATE.tar.gz"
docker exec secondbrain-couchdb rm /tmp/couchdb-backup.tar.gz

echo "Backup saved to: $BACKUP_DIR/couchdb-$DATE.tar.gz"

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t couchdb-*.tar.gz | tail -n +8 | xargs -r rm --

echo "Done! Current backups:"
ls -lh "$BACKUP_DIR"/couchdb-*.tar.gz
