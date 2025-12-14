#!/bin/bash
# Database Backup Script for JoveHeal
# Creates a PostgreSQL dump that can be downloaded or transferred

echo "=========================================="
echo "  JoveHeal Database Backup"
echo "=========================================="

# Check if DATABASE_URL exists
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not found in environment!"
    exit 1
fi

# Create backups directory if it doesn't exist
mkdir -p backups

# Generate timestamp for filename
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
BACKUP_FILE="backups/joveheal_db_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

echo ""
echo "Creating database backup..."
echo "Timestamp: ${TIMESTAMP}"

# Run pg_dump using DATABASE_URL
pg_dump "$DATABASE_URL" --no-owner --no-acl --clean --if-exists > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Get file size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    
    echo ""
    echo "=========================================="
    echo "  BACKUP SUCCESSFUL!"
    echo "=========================================="
    echo ""
    echo "  File: ${COMPRESSED_FILE}"
    echo "  Size: ${COMPRESSED_SIZE}"
    echo ""
    echo "=========================================="
    echo "  HOW TO DOWNLOAD:"
    echo "=========================================="
    echo ""
    echo "  Option 1: Replit File Browser"
    echo "  - Open the 'backups' folder in Replit"
    echo "  - Right-click the .sql.gz file"
    echo "  - Click 'Download'"
    echo ""
    echo "  Option 2: Transfer to VPS via SCP"
    echo "  Run this from your VPS:"
    echo "  scp user@replit:~/backups/${COMPRESSED_FILE##*/} /path/on/vps/"
    echo ""
    echo "=========================================="
    
    # List recent backups
    echo ""
    echo "Recent backups:"
    ls -lh backups/*.gz 2>/dev/null | tail -5
else
    echo "ERROR: Database backup failed!"
    rm -f "$BACKUP_FILE"
    exit 1
fi
