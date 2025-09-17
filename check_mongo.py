import asyncio
import sys
sys.path.append('/home/munim/anis/projects/test')

from src.database.mongodb import mongodb_client
from src.config.settings import settings

async def check_collections():
    try:
        # Connect to MongoDB
        if not mongodb_client.is_connected:
            await mongodb_client.connect()
        
        db = mongodb_client.database
        
        # Get list of collections
        collections = await db.list_collection_names()
        print(f"Collections found: {len(collections)}")
        
        # Show first 10 collections
        print("\nFirst 10 collections:")
        for coll_name in collections[:10]:
            count = await db[coll_name].count_documents({})
            print(f"  {coll_name}: {count} documents")
        
        # Check specifically for tables we're trying to sync
        tables_to_check = ['user', 'shop', 'order', 'product', 'customer', 'abandoned_cart_items']
        print('\nChecking sync tables:')
        for table in tables_to_check:
            if table in collections:
                count = await db[table].count_documents({})
                # Get a sample document
                sample = await db[table].find_one()
                print(f"  {table}: {count} documents")
                if sample and '_sync_metadata' in sample:
                    print(f"    Last synced: {sample['_sync_metadata'].get('synced_at', 'N/A')}")
            else:
                print(f"  {table}: collection not found")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await mongodb_client.disconnect()

asyncio.run(check_collections())
