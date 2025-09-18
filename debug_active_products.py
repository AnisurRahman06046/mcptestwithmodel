#!/usr/bin/env python3
"""
Debug script to test "How many active products?" query
"""

import asyncio
import json
from src.services.universal_llm_processor import universal_llm_processor
from src.services.universal_query_builder import universal_query_builder
from src.database.mongodb import mongodb_client
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_active_products():
    """Debug the active products query"""

    # Connect to MongoDB
    if not mongodb_client.is_connected:
        await mongodb_client.connect()
        print("✓ Connected to MongoDB")

    context = {"shop_id": "10", "user_id": "test"}
    query = "How many active products?"

    print("=" * 80)
    print(f"Query: {query}")
    print("=" * 80)

    # Step 1: Test domain identification
    print("\n1. DOMAIN IDENTIFICATION:")
    print("-" * 40)
    domains = await universal_llm_processor._identify_domains(query)
    print(f"Domains identified: {domains}")

    # Step 2: Fetch raw data
    print("\n2. RAW DATA FETCH:")
    print("-" * 40)
    raw_data = await universal_query_builder.fetch_domain_data(
        domain="products",
        shop_id="10",
        date_range=None
    )

    if raw_data.get("success"):
        data = raw_data["data"]
        print(f"✓ Data fetched successfully")
        print(f"Total products: {data.get('statistics', {}).get('total_products', 0)}")

        # Analyze product statuses
        if "products" in data:
            products = data["products"]
            print(f"Products in data: {len(products)}")

            # Count by status
            status_counts = {}
            for product in products:
                status = product.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            print("\nProduct Status Distribution:")
            for status, count in status_counts.items():
                print(f"  - {status}: {count}")

            # Show sample products
            print("\nSample Products (first 3):")
            for i, prod in enumerate(products[:3], 1):
                print(f"  {i}. ID: {prod.get('id')}, Name: {prod.get('name')}, Status: {prod.get('status')}")

    # Step 3: Test full processor
    print("\n3. FULL PROCESSOR TEST:")
    print("-" * 40)

    try:
        result = await universal_llm_processor.process_query(query, context)

        if result["success"]:
            print(f"✓ Success")
            print(f"Response: {result['response']}")
            print(f"Intent: {result['metadata']['query_intent']}")
            print(f"Confidence: {result['metadata']['confidence_score']}")

            if result.get("debug"):
                print("\nDebug Info:")
                print(json.dumps(result["debug"], indent=2))
        else:
            print(f"✗ Failed")
            print(f"Error: {result.get('error')}")
            print(f"Response: {result.get('response')}")

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()

    # Step 4: Test with different query variations
    print("\n4. QUERY VARIATIONS TEST:")
    print("-" * 40)

    variations = [
        "How many products are active?",
        "Show me active products count",
        "What's the number of active products?",
        "How many products in total?",
        "Total products count"
    ]

    for variant in variations:
        print(f"\nQuery: {variant}")
        try:
            result = await universal_llm_processor.process_query(variant, context)
            print(f"  → {result.get('response', 'No response')}")
        except Exception as e:
            print(f"  → Error: {e}")

    # Cleanup
    if mongodb_client.is_connected:
        await mongodb_client.disconnect()
        print("\n✓ Disconnected from MongoDB")

async def test_direct_data_fetch():
    """Test direct data fetching to understand the data structure"""

    if not mongodb_client.is_connected:
        await mongodb_client.connect()

    db = mongodb_client.database

    print("\n" + "=" * 80)
    print("DIRECT DATABASE QUERY TEST")
    print("=" * 80)

    # Query products directly
    products_cursor = db.product.find({"shop_id": 10}).limit(10)
    products = await products_cursor.to_list(length=10)

    print(f"\nFound {len(products)} products")
    print("\nProduct Structure Example:")

    if products:
        sample = products[0]
        print(json.dumps(sample, indent=2, default=str))

        # Check all unique statuses
        all_products_cursor = db.product.find({"shop_id": 10})
        all_products = await all_products_cursor.to_list(length=None)

        statuses = set()
        for p in all_products:
            statuses.add(str(p.get("status", "none")))

        print(f"\nUnique status values in database: {statuses}")
        print(f"Total products in database: {len(all_products)}")

        # Count active products
        active_count = 0
        for p in all_products:
            if str(p.get("status", "")).lower() in ["active", "1", "true"]:
                active_count += 1

        print(f"Active products (status=active/1/true): {active_count}")

async def main():
    """Main debug function"""
    await debug_active_products()
    await test_direct_data_fetch()

if __name__ == "__main__":
    asyncio.run(main())