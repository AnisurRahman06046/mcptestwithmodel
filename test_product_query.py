import asyncio
import sys
sys.path.append('/home/munim/anis/projects/test')

from src.services.tool_registry import mongodb_tool_registry
from src.database.mongodb import mongodb_client

async def test_product_tool():
    try:
        # Connect to MongoDB
        if not mongodb_client.is_connected:
            await mongodb_client.connect()
        
        # Test the get_product_data tool
        result = await mongodb_tool_registry.execute_tool(
            "get_product_data",
            {"shop_id": "10"}
        )
        
        print("Tool execution result:")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Total products: {result['result']['total_products']}")
            print(f"Highest price: {result['result']['highest_price']}")
            print(f"Lowest price: {result['result']['lowest_price']}")
            print(f"Average price: {result['result']['average_price']}")
        else:
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await mongodb_client.disconnect()

asyncio.run(test_product_tool())
