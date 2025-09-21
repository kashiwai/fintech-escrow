#!/usr/bin/env python3
"""Initialize database for Render deployment with proper error handling"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set RENDER environment variable for config
os.environ['RENDER'] = 'true'

from src.app.db import init_db

if __name__ == "__main__":
    db_path = os.environ.get('DB_PATH', '/app/data/fintech.db')
    db_dir = os.path.dirname(db_path)

    print(f"Checking database directory: {db_dir}")
    if os.path.exists(db_dir):
        print(f"✓ Directory exists: {db_dir}")
        print(f"✓ Directory writable: {os.access(db_dir, os.W_OK)}")
    else:
        print(f"✗ Directory does not exist: {db_dir}")
        print("Using fallback directory...")

    print("Initializing database...")
    try:
        init_db()
        print(f"✅ Database initialized successfully")

        # Verify DB file was created
        from src.app.config import DB_PATH as actual_db_path
        if os.path.exists(actual_db_path):
            print(f"✅ Database file created at: {actual_db_path}")
            print(f"   File size: {os.path.getsize(actual_db_path)} bytes")
        else:
            print(f"⚠️ Database file not found at: {actual_db_path}")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)