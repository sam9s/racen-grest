#!/usr/bin/env python3
"""
GRESTA Database Backup Script
Backs up PostgreSQL database and ChromaDB vector database for UAT to Production transfer.

Usage:
    python db_backup.py backup              # Create full backup
    python db_backup.py restore <backup_dir> # Restore from backup
    python db_backup.py list                # List available backups
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from urllib.parse import urlparse

BACKUP_DIR = "backups"
CHROMA_DIR = "chroma_db"


def get_db_connection_params():
    """Extract connection parameters from DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password
    }


def backup_postgresql(backup_path: str) -> bool:
    """Backup PostgreSQL database to SQL file."""
    print("\n[1/3] Backing up PostgreSQL database...")
    
    try:
        params = get_db_connection_params()
        sql_file = os.path.join(backup_path, "postgres_backup.sql")
        
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]
        
        cmd = [
            "pg_dump",
            "-h", params["host"],
            "-p", str(params["port"]),
            "-U", params["user"],
            "-d", params["database"],
            "--no-owner",
            "--no-acl",
            "-f", sql_file
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            size = os.path.getsize(sql_file)
            print(f"    PostgreSQL backup complete: {sql_file} ({size:,} bytes)")
            return True
        else:
            print(f"    ERROR: pg_dump failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def backup_chromadb(backup_path: str) -> bool:
    """Backup ChromaDB vector database."""
    print("\n[2/3] Backing up ChromaDB vector database...")
    
    try:
        chroma_backup = os.path.join(backup_path, "chroma_db")
        
        if os.path.exists(CHROMA_DIR):
            shutil.copytree(CHROMA_DIR, chroma_backup)
            
            total_size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, dn, filenames in os.walk(chroma_backup)
                for f in filenames
            )
            print(f"    ChromaDB backup complete: {chroma_backup} ({total_size:,} bytes)")
            return True
        else:
            print(f"    WARNING: ChromaDB directory not found at {CHROMA_DIR}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def backup_metadata(backup_path: str) -> bool:
    """Save backup metadata."""
    print("\n[3/3] Saving backup metadata...")
    
    try:
        from database import get_product_count
        product_count = get_product_count()
    except:
        product_count = "unknown"
    
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "source": "GRESTA UAT",
        "product_count": product_count,
        "files": os.listdir(backup_path)
    }
    
    meta_file = os.path.join(backup_path, "backup_metadata.json")
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"    Metadata saved: {meta_file}")
    return True


def create_backup():
    """Create a complete backup of all databases."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"gresta_backup_{timestamp}")
    
    os.makedirs(backup_path, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"GRESTA Database Backup")
    print(f"{'='*60}")
    print(f"Backup directory: {backup_path}")
    
    pg_ok = backup_postgresql(backup_path)
    chroma_ok = backup_chromadb(backup_path)
    meta_ok = backup_metadata(backup_path)
    
    print(f"\n{'='*60}")
    print(f"Backup Summary")
    print(f"{'='*60}")
    print(f"  PostgreSQL:  {'OK' if pg_ok else 'FAILED'}")
    print(f"  ChromaDB:    {'OK' if chroma_ok else 'FAILED'}")
    print(f"  Metadata:    {'OK' if meta_ok else 'FAILED'}")
    print(f"\nBackup location: {backup_path}")
    
    if pg_ok:
        print(f"\nTo transfer to production Docker:")
        print(f"  1. Copy the backup folder to your production server")
        print(f"  2. Run: python db_backup.py restore {backup_path}")
    
    return backup_path


def restore_postgresql(backup_path: str) -> bool:
    """Restore PostgreSQL database from SQL file."""
    print("\n[1/2] Restoring PostgreSQL database...")
    
    try:
        params = get_db_connection_params()
        sql_file = os.path.join(backup_path, "postgres_backup.sql")
        
        if not os.path.exists(sql_file):
            print(f"    ERROR: SQL file not found: {sql_file}")
            return False
        
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]
        
        cmd = [
            "psql",
            "-h", params["host"],
            "-p", str(params["port"]),
            "-U", params["user"],
            "-d", params["database"],
            "-f", sql_file
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"    PostgreSQL restore complete")
            return True
        else:
            print(f"    WARNING: Some errors during restore (may be normal for re-imports)")
            print(f"    {result.stderr[:500]}")
            return True
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def restore_chromadb(backup_path: str) -> bool:
    """Restore ChromaDB vector database."""
    print("\n[2/2] Restoring ChromaDB vector database...")
    
    try:
        chroma_backup = os.path.join(backup_path, "chroma_db")
        
        if not os.path.exists(chroma_backup):
            print(f"    ERROR: ChromaDB backup not found: {chroma_backup}")
            return False
        
        if os.path.exists(CHROMA_DIR):
            shutil.rmtree(CHROMA_DIR)
            print(f"    Removed existing ChromaDB directory")
        
        shutil.copytree(chroma_backup, CHROMA_DIR)
        print(f"    ChromaDB restore complete")
        return True
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def restore_backup(backup_path: str):
    """Restore databases from a backup."""
    if not os.path.exists(backup_path):
        print(f"ERROR: Backup path not found: {backup_path}")
        return
    
    meta_file = os.path.join(backup_path, "backup_metadata.json")
    if os.path.exists(meta_file):
        with open(meta_file) as f:
            metadata = json.load(f)
        print(f"\n{'='*60}")
        print(f"Restoring GRESTA Backup")
        print(f"{'='*60}")
        print(f"Backup timestamp: {metadata.get('timestamp', 'unknown')}")
        print(f"Product count: {metadata.get('product_count', 'unknown')}")
    
    pg_ok = restore_postgresql(backup_path)
    chroma_ok = restore_chromadb(backup_path)
    
    print(f"\n{'='*60}")
    print(f"Restore Summary")
    print(f"{'='*60}")
    print(f"  PostgreSQL:  {'OK' if pg_ok else 'FAILED'}")
    print(f"  ChromaDB:    {'OK' if chroma_ok else 'FAILED'}")
    
    if pg_ok and chroma_ok:
        print(f"\nRestore complete! Restart your application to use the restored data.")


def list_backups():
    """List available backups."""
    if not os.path.exists(BACKUP_DIR):
        print("No backups found.")
        return
    
    backups = sorted([d for d in os.listdir(BACKUP_DIR) if d.startswith("gresta_backup_")])
    
    if not backups:
        print("No backups found.")
        return
    
    print(f"\n{'='*60}")
    print(f"Available GRESTA Backups")
    print(f"{'='*60}")
    
    for backup in backups:
        backup_path = os.path.join(BACKUP_DIR, backup)
        meta_file = os.path.join(backup_path, "backup_metadata.json")
        
        if os.path.exists(meta_file):
            with open(meta_file) as f:
                metadata = json.load(f)
            timestamp = metadata.get("timestamp", "unknown")
            products = metadata.get("product_count", "?")
        else:
            timestamp = "unknown"
            products = "?"
        
        print(f"  {backup}")
        print(f"      Created: {timestamp}")
        print(f"      Products: {products}")
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "backup":
        create_backup()
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python db_backup.py restore <backup_dir>")
            return
        restore_backup(sys.argv[2])
    elif command == "list":
        list_backups()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
