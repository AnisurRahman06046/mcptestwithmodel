#!/usr/bin/env python3
"""
Simple MySQL connection test script.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    import aiomysql
except ImportError:
    print("❌ Error: aiomysql not installed")
    print("Install it with: pip install aiomysql")
    sys.exit(1)


async def test_mysql_connection():
    """Test MySQL connection with credentials from .env"""
    
    # Get MySQL connection details from environment
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER', '')
    password = os.getenv('MYSQL_PASSWORD', '')
    database = os.getenv('MYSQL_DATABASE', '')
    
    # Validate required fields
    if not all([host, user, password, database]):
        print("❌ Error: Missing required MySQL connection details!")
        print("Please set these environment variables:")
        print("  MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
        return False
    
    print(f"🔌 Testing MySQL connection...")
    print(f"   Host: {host}:{port}")
    print(f"   User: {user}")
    print(f"   Database: {database}")
    
    try:
        # Test connection
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            db=database,
            charset='utf8mb4'
        )
        
        print("✅ Connection successful!")
        
        # Test query
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            
            print(f"📊 Found {len(tables)} tables:")
            for i, (table_name,) in enumerate(tables[:10], 1):
                print(f"   {i}. {table_name}")
            
            if len(tables) > 10:
                print(f"   ... and {len(tables) - 10} more tables")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    print("🔍 MySQL Connection Test")
    print("=" * 40)
    
    success = asyncio.run(test_mysql_connection())
    
    if success:
        print("\n✅ Your MySQL credentials are working!")
        print("The sync system should be able to connect.")
    else:
        print("\n❌ Please check your MySQL credentials in .env file")