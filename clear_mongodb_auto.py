#!/usr/bin/env python3
"""
Auto-clear all synced collections from MongoDB (no confirmation)
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def clear_mongodb_collections():
    """Clear all collections from MongoDB automatically."""
    
    try:
        from src.database.mongodb import mongodb_client
        
        print("🔌 Connecting to MongoDB...")
        
        # Ensure MongoDB is connected
        if not mongodb_client.is_connected:
            await mongodb_client.connect()
        
        database = mongodb_client.database
        
        # Get all collection names
        collections = await database.list_collection_names()
        
        if not collections:
            print("📭 No collections found in database")
            return
        
        print(f"🗑️  Auto-deleting {len(collections)} collections...")
        
        deleted_count = 0
        for collection_name in collections:
            try:
                await database.drop_collection(collection_name)
                print(f"  ✅ Deleted: {collection_name}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ Failed to delete {collection_name}: {e}")
        
        print(f"\n🎉 Successfully deleted {deleted_count}/{len(collections)} collections")
        print("✅ MongoDB cleanup completed!")
        print("   Ready for fresh sync with your 8 core tables.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        if 'mongodb_client' in locals():
            await mongodb_client.disconnect()


if __name__ == "__main__":
    print("🗑️  MongoDB Auto-Cleaner")
    print("=" * 30)
    
    asyncio.run(clear_mongodb_collections())