#!/usr/bin/env python3
"""
GRESTA Database Initialization Script

This script creates all required database tables for the GRESTA chatbot.
Run this when setting up a new environment or recovering from backup.

Usage:
    python init_database.py
"""

import os
import sys
from datetime import datetime

def get_database_url():
    """Get database URL from environment."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set!")
        print("Please set it to your PostgreSQL connection string.")
        print("Example: postgresql://user:password@host:5432/database")
        sys.exit(1)
    return db_url

def init_database():
    """Initialize all database tables."""
    try:
        from sqlalchemy import create_engine, text
        
        db_url = get_database_url()
        engine = create_engine(db_url)
        
        print("=" * 60)
        print("GRESTA Database Initialization")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Database: {db_url.split('@')[-1] if '@' in db_url else 'configured'}")
        print()
        
        with engine.connect() as conn:
            # Create users table
            print("[1/6] Creating users table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    image TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("      Users table ready.")
            
            # Create conversations table
            print("[2/6] Creating conversations table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    channel VARCHAR(50) DEFAULT 'web',
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session 
                ON conversations(session_id)
            """))
            # Add user_id column if missing (for existing tables)
            try:
                conn.execute(text("""
                    ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_user 
                    ON conversations(user_id)
                """))
            except Exception:
                pass  # Column or index may already exist
            conn.commit()
            print("      Conversations table ready.")
            
            # Create messages table
            print("[3/6] Creating messages table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES conversations(id),
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            """))
            conn.commit()
            print("      Messages table ready.")
            
            # Create feedback table
            print("[4/6] Creating feedback table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    message_id INTEGER REFERENCES messages(id),
                    session_id VARCHAR(255),
                    rating VARCHAR(20),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("      Feedback table ready.")
            
            # Create grest_products table
            print("[5/6] Creating grest_products table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS grest_products (
                    id SERIAL PRIMARY KEY,
                    shopify_id BIGINT UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    price DECIMAL(10, 2),
                    compare_at_price DECIMAL(10, 2),
                    discount_percent INTEGER,
                    condition VARCHAR(50),
                    storage VARCHAR(50),
                    color VARCHAR(50),
                    description TEXT,
                    specifications JSONB,
                    product_url TEXT,
                    image_url TEXT,
                    in_stock BOOLEAN DEFAULT TRUE,
                    warranty_months INTEGER DEFAULT 6,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_products_category 
                ON grest_products(category)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_products_price 
                ON grest_products(price)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_products_name 
                ON grest_products(name)
            """))
            conn.commit()
            print("      grest_products table ready.")
            
            # Create flagged_conversations table for safety logging
            print("[6/6] Creating flagged_conversations table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS flagged_conversations (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255),
                    user_message TEXT,
                    flag_reason VARCHAR(100),
                    severity VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("      Flagged conversations table ready.")
            
            # Verify tables
            print()
            print("Verifying tables...")
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            required_tables = ['users', 'conversations', 'messages', 'feedback', 
                             'grest_products', 'flagged_conversations']
            
            all_present = True
            for table in required_tables:
                if table in tables:
                    print(f"  [OK] {table}")
                else:
                    print(f"  [MISSING] {table}")
                    all_present = False
            
            print()
            if all_present:
                print("=" * 60)
                print("SUCCESS: All database tables created successfully!")
                print("=" * 60)
                print()
                print("Next steps:")
                print("1. Run 'python scrape_grest_products.py' to populate products")
                print("2. Start the application with 'python webhook_server.py'")
            else:
                print("WARNING: Some tables are missing. Check errors above.")
                
    except ImportError:
        print("ERROR: SQLAlchemy not installed.")
        print("Run: pip install sqlalchemy psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        sys.exit(1)

def check_product_count():
    """Check if products are populated."""
    try:
        from sqlalchemy import create_engine, text
        
        db_url = get_database_url()
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM grest_products"))
            count = result.scalar()
            
            if count > 0:
                print(f"\nProduct database: {count} products found")
            else:
                print("\nProduct database: Empty - run 'python scrape_grest_products.py'")
                
    except Exception as e:
        print(f"Could not check product count: {e}")

if __name__ == "__main__":
    init_database()
    check_product_count()
