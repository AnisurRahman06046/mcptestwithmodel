#!/usr/bin/env python3
"""
Simple script to list all tables in your MySQL database.
Run this first to see what tables are available for sync.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.sync.mysql_connector import MySQLConnector, MySQLConnectionConfig


async def list_tables():
    """Connect to MySQL and list all available tables."""
    
    config = MySQLConnectionConfig(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', ''),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', '')
    )
    
    if not all([config.host, config.user, config.password, config.database]):
        print("Set these environment variables:")
        print("MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
        return
    
    connector = MySQLConnector(config)
    
    try:
        print(f"Connecting to {config.database}...")
        await connector.connect()
        
        # Discover all tables
        tables = await connector.discover_all_tables()
        
        print(f"\nFound {len(tables)} tables:")
        for name, info in tables.items():
            sync_ready = "✅" if (info.has_created_at or info.has_updated_at) else "⚠️"
            print(f"  {sync_ready} {name}")
        
        print(f"\nTo sync a specific table later, use:")
        print(f"SYNC_TABLES=table1,table2,table3")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await connector.disconnect()


if __name__ == "__main__":
    asyncio.run(list_tables())