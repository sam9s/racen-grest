#!/bin/bash
# GRESTA Database Restore Script
# Restores PostgreSQL and ChromaDB from backup

CHROMA_DIR="chroma_db"

if [ -z "$1" ]; then
    echo "Usage: bash db_restore.sh <backup_path>"
    echo "Example: bash db_restore.sh backups/gresta_backup_20251224_071536"
    exit 1
fi

BACKUP_PATH="$1"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "ERROR: Backup path not found: $BACKUP_PATH"
    exit 1
fi

echo ""
echo "============================================================"
echo "GRESTA Database Restore"
echo "============================================================"
echo "Restoring from: $BACKUP_PATH"

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not found!"
    exit 1
fi

# 1. PostgreSQL Restore
echo ""
echo "[1/2] Restoring PostgreSQL database..."
SQL_FILE="${BACKUP_PATH}/postgres_backup.sql"

if [ -f "$SQL_FILE" ]; then
    psql "$DATABASE_URL" -f "$SQL_FILE" 2>/dev/null
    echo "      PostgreSQL restore complete"
else
    echo "      ERROR: SQL file not found: $SQL_FILE"
fi

# 2. ChromaDB Restore
echo ""
echo "[2/2] Restoring ChromaDB vector database..."
CHROMA_BACKUP="${BACKUP_PATH}/chroma_db"

if [ -d "$CHROMA_BACKUP" ]; then
    rm -rf "$CHROMA_DIR"
    cp -r "$CHROMA_BACKUP" "$CHROMA_DIR"
    echo "      ChromaDB restore complete"
else
    echo "      WARNING: ChromaDB backup not found"
fi

echo ""
echo "============================================================"
echo "Restore Complete!"
echo "============================================================"
echo "Restart your application to use the restored data."
echo ""
