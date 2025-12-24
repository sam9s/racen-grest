#!/bin/bash
# GRESTA Database Backup Script
# Backs up PostgreSQL and ChromaDB for UAT to Production transfer

BACKUP_DIR="backups"
CHROMA_DIR="chroma_db"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_PATH="${BACKUP_DIR}/gresta_backup_${TIMESTAMP}"

echo ""
echo "============================================================"
echo "GRESTA Database Backup"
echo "============================================================"

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not found!"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_PATH"
echo "Backup directory: $BACKUP_PATH"

# 1. PostgreSQL Backup
echo ""
echo "[1/2] Backing up PostgreSQL database..."
SQL_FILE="${BACKUP_PATH}/postgres_backup.sql"

pg_dump "$DATABASE_URL" --no-owner --no-acl -f "$SQL_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    SQL_SIZE=$(du -h "$SQL_FILE" | cut -f1)
    echo "      PostgreSQL backup complete: $SQL_FILE ($SQL_SIZE)"
else
    echo "      ERROR: PostgreSQL backup failed!"
fi

# 2. ChromaDB Backup
echo ""
echo "[2/2] Backing up ChromaDB vector database..."

if [ -d "$CHROMA_DIR" ]; then
    cp -r "$CHROMA_DIR" "${BACKUP_PATH}/chroma_db"
    CHROMA_SIZE=$(du -sh "${BACKUP_PATH}/chroma_db" | cut -f1)
    echo "      ChromaDB backup complete: ${BACKUP_PATH}/chroma_db ($CHROMA_SIZE)"
else
    echo "      WARNING: ChromaDB directory not found"
fi

# 3. Create metadata
echo ""
echo "Saving metadata..."
PRODUCT_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM grest_products" 2>/dev/null | tr -d ' ')

cat > "${BACKUP_PATH}/backup_metadata.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "source": "GRESTA UAT",
  "product_count": ${PRODUCT_COUNT:-0}
}
EOF

echo ""
echo "============================================================"
echo "Backup Complete!"
echo "============================================================"
echo "Location: $BACKUP_PATH"
echo "Products: ${PRODUCT_COUNT:-unknown}"
echo ""
echo "To restore on production:"
echo "  1. Copy backup folder to production server"
echo "  2. Run: bash db_restore.sh $BACKUP_PATH"
echo ""
