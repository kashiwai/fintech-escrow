#!/usr/bin/env python3
"""Initialize database for Render deployment"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app.db import init_db

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print(f"Database initialized at: {os.environ.get('DB_PATH', './fintech.db')}")