import asyncio
import sys
import json
sys.path.append('/home/munim/anis/projects/test')

from src.database.mongodb import mongodb_client

async def check_data():
    try:
        # Connect to MongoDB
        if not mongodb_client.is_connected:
            await mongodb_client.connect()
        
        db = mongodb_client.database
        
        # Check shop collection
        print("=== Shop Collection ===")
        shops = await db['shop'].find({}).limit(5).to_list(length=5)
        if shops:
            print(f"Found {len(shops)} shops")
            for shop in shops[:2]:
                print(f"Shop ID: {shop.get('id')}, Name: {shop.get('name', 'N/A')}")
        
        # Check order collection structure
        print("\n=== Order Collection ===")
        orders = await db['order'].find({}).limit(2).to_list(length=2)
        if orders:
            print(f"Sample order fields: {list(orders[0].keys())[:15]}")
            print(f"Shop ID in order: {orders[0].get('shop_id', 'NOT FOUND')}")
            print(f"Order date field: created_at={orders[0].get('created_at', 'N/A')}")
            print(f"Total amount field: total={orders[0].get('total', 'N/A')}, grand_total={orders[0].get('grand_total', 'N/A')}")
        
        # Check product collection
        print("\n=== Product Collection ===")
        products = await db['product'].find({}).limit(2).to_list(length=2)
        if products:
            print(f"Sample product fields: {list(products[0].keys())[:15]}")
            print(f"Product name: {products[0].get('name', 'N/A')}")
            
        # Check customer collection
        print("\n=== Customer Collection ===")
        customers = await db['customer'].find({}).limit(2).to_list(length=2)
        if customers:
            print(f"Sample customer fields: {list(customers[0].keys())[:15]}")
            
        # Check user collection
        print("\n=== User Collection ===")
        users = await db['user'].find({}).limit(2).to_list(length=2)
        if users:
            print(f"Sample user fields: {list(users[0].keys())[:15]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await mongodb_client.disconnect()

asyncio.run(check_data())
