#!/bin/bash
# Complete Database Backup Script for JoveHeal
# Backs up: PostgreSQL + ChromaDB (vector_db) + Knowledge Base metadata

echo "=========================================="
echo "  JoveHeal Complete Backup"
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
BACKUP_DIR="backups/joveheal_backup_${TIMESTAMP}"
mkdir -p "$BACKUP_DIR"

echo ""
echo "Timestamp: ${TIMESTAMP}"
echo ""

# 1. PostgreSQL Database
echo "[1/3] Backing up PostgreSQL database..."
pg_dump "$DATABASE_URL" --no-owner --no-acl --clean --if-exists > "$BACKUP_DIR/postgresql.sql"
if [ $? -eq 0 ]; then
    PG_SIZE=$(du -h "$BACKUP_DIR/postgresql.sql" | cut -f1)
    echo "      PostgreSQL: ${PG_SIZE}"
else
    echo "      ERROR: PostgreSQL backup failed!"
fi

# 2. ChromaDB Vector Database (contains all ingested content)
echo "[2/3] Backing up ChromaDB vector database..."
if [ -d "vector_db" ]; then
    cp -r vector_db "$BACKUP_DIR/"
    CHROMA_SIZE=$(du -sh "$BACKUP_DIR/vector_db" | cut -f1)
    echo "      ChromaDB: ${CHROMA_SIZE}"
else
    echo "      WARNING: vector_db folder not found"
fi

# 3. Knowledge Base Metadata
echo "[3/3] Backing up knowledge base metadata..."
if [ -d "knowledge_base" ]; then
    cp -r knowledge_base "$BACKUP_DIR/"
    KB_SIZE=$(du -sh "$BACKUP_DIR/knowledge_base" | cut -f1)
    echo "      Knowledge Base: ${KB_SIZE}"
else
    echo "      WARNING: knowledge_base folder not found"
fi

# Compress everything into one file
echo ""
echo "Compressing backup..."
FINAL_FILE="backups/joveheal_complete_${TIMESTAMP}.tar.gz"
tar -czf "$FINAL_FILE" -C backups "joveheal_backup_${TIMESTAMP}"
rm -rf "$BACKUP_DIR"

FINAL_SIZE=$(du -h "$FINAL_FILE" | cut -f1)

echo ""
echo "=========================================="
echo "  BACKUP SUCCESSFUL!"
echo "=========================================="
echo ""
echo "  File: ${FINAL_FILE}"
echo "  Total Size: ${FINAL_SIZE}"
echo ""
echo "  Contents:"
echo "  - PostgreSQL (users, conversations, feedback)"
echo "  - ChromaDB (Jovee pages + SOMERA transcripts)"
echo "  - Knowledge base metadata"
echo ""
echo "=========================================="
echo "  HOW TO DOWNLOAD:"
echo "=========================================="
echo ""
echo "  1. Open 'backups' folder in Replit file browser"
echo "  2. Right-click the .tar.gz file"
echo "  3. Click 'Download'"
echo ""
echo "=========================================="

# List recent backups
echo ""
echo "Recent backups:"
ls -lh backups/*.tar.gz 2>/dev/null | tail -5
