#!/bin/bash
# Second Brain - CouchDB Initialization Script
# Run after docker compose up -d
# Usage: bash init-couchdb.sh

set -e

echo "=========================================="
echo "  CouchDB Initialization"
echo "=========================================="

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

COUCHDB_URL="http://localhost:5984"

echo -e "${YELLOW}Waiting for CouchDB to start...${NC}"
sleep 10

# Check if CouchDB is running
for i in {1..30}; do
    if curl -s "$COUCHDB_URL/_up" > /dev/null 2>&1; then
        echo -e "${GREEN}CouchDB is running${NC}"
        break
    fi
    echo "Waiting for CouchDB... ($i/30)"
    sleep 2
done

echo -e "${YELLOW}Step 1: Configuring CouchDB for single node...${NC}"
curl -X PUT "$COUCHDB_URL/_users" \
    -u "$COUCHDB_USER:$COUCHDB_PASSWORD" \
    2>/dev/null || echo "(may already exist)"

curl -X PUT "$COUCHDB_URL/_replicator" \
    -u "$COUCHDB_USER:$COUCHDB_PASSWORD" \
    2>/dev/null || echo "(may already exist)"

curl -X PUT "$COUCHDB_URL/_global_changes" \
    -u "$COUCHDB_USER:$COUCHDB_PASSWORD" \
    2>/dev/null || echo "(may already exist)"

echo -e "${YELLOW}Step 2: Creating notes database...${NC}"
curl -X PUT "$COUCHDB_URL/$COUCHDB_DATABASE" \
    -u "$COUCHDB_USER:$COUCHDB_PASSWORD" \
    2>/dev/null || echo "(may already exist)"

echo -e "${YELLOW}Step 3: Creating indexes for search...${NC}"

# Index for mtime (for recent documents)
curl -X POST "$COUCHDB_URL/$COUCHDB_DATABASE/_index" \
    -u "$COUCHDB_USER:$COUCHDB_PASSWORD" \
    -H "Content-Type: application/json" \
    -d '{
        "index": {
            "fields": ["mtime"]
        },
        "name": "mtime-index",
        "type": "json"
    }' 2>/dev/null

# Index for type (for filtering)
curl -X POST "$COUCHDB_URL/$COUCHDB_DATABASE/_index" \
    -u "$COUCHDB_USER:$COUCHDB_PASSWORD" \
    -H "Content-Type: application/json" \
    -d '{
        "index": {
            "fields": ["type"]
        },
        "name": "type-index",
        "type": "json"
    }' 2>/dev/null

echo -e "${YELLOW}Step 4: Verifying setup...${NC}"
echo ""
echo "Databases:"
curl -s "$COUCHDB_URL/_all_dbs" -u "$COUCHDB_USER:$COUCHDB_PASSWORD"
echo ""
echo ""
echo "Database info:"
curl -s "$COUCHDB_URL/$COUCHDB_DATABASE" -u "$COUCHDB_USER:$COUCHDB_PASSWORD"
echo ""

echo ""
echo -e "${GREEN}=========================================="
echo "  CouchDB initialization complete!"
echo "==========================================${NC}"
echo ""
echo "Your CouchDB is ready for Obsidian Livesync"
echo ""
echo "Connection details for Obsidian:"
echo "  URI: https://$DOMAIN"
echo "  Username: $COUCHDB_USER"
echo "  Database: $COUCHDB_DATABASE"
echo ""
