#!/usr/bin/env python3
"""
Clear all synced collections from MongoDB
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
    """Clear all collections from MongoDB."""
    
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
        
        print(f"📋 Found {len(collections)} collections:")
        for i, collection_name in enumerate(collections, 1):
            print(f"  {i}. {collection_name}")
        
        # Ask for confirmation
        print(f"\n⚠️  This will DELETE ALL {len(collections)} collections!")
        print("   Are you sure? Type 'yes' to confirm:")
        
        confirmation = input().strip().lower()
        if confirmation != 'yes':
            print("❌ Operation cancelled")
            return
        
        print(f"\n🗑️  Deleting {len(collections)} collections...")
        
        deleted_count = 0
        for collection_name in collections:
            try:
                await database.drop_collection(collection_name)
                print(f"  ✅ Deleted: {collection_name}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ Failed to delete {collection_name}: {e}")
        
        print(f"\n🎉 Successfully deleted {deleted_count}/{len(collections)} collections")
        
        # Also reset sync metadata
        print("\n🔄 Resetting sync metadata...")
        try:
            # Create sync_metadata collection and clear it
            sync_collection = database["sync_metadata"]
            result = await sync_collection.delete_many({})
            print(f"  ✅ Cleared {result.deleted_count} sync records")
        except Exception as e:
            print(f"  ⚠️  Could not clear sync metadata: {e}")
        
        print("\n✅ MongoDB cleanup completed!")
        print("   You can now run a fresh sync.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect
        if 'mongodb_client' in locals():
            await mongodb_client.disconnect()


if __name__ == "__main__":
    print("🗑️  MongoDB Collection Cleaner")
    print("=" * 40)
    
    asyncio.run(clear_mongodb_collections())