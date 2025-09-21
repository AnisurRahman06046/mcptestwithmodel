#!/usr/bin/env python3
"""
Quick validation that the fix works for active products
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import UniversalLLMProcessor
from src.services.universal_query_builder import universal_query_builder
from src.database.mongodb import mongodb_client


async def validate_fix():
    print("=" * 60)
    print("VALIDATING ACTIVE PRODUCTS FIX")
    print("=" * 60)

    # Connect to MongoDB
    await mongodb_client.connect()

    # Initialize processor
    processor = UniversalLLMProcessor()

    # Test query
    query = "How many active products do I have?"
    context = {"shop_id": "10"}

    print(f"\n📝 Query: {query}")
    print("-" * 40)

    # Step 1: Fetch the data
    domains = await processor._identify_domains(query)
    print(f"1. Domains identified: {domains}")

    all_data = {}
    for domain in domains:
        domain_data = await universal_query_builder.fetch_domain_data(
            domain=domain,
            shop_id="10",
            date_range=None
        )
        if domain_data.get("success"):
            all_data[domain] = domain_data["data"]

    # Step 2: Prepare data (adds product_status_distribution)
    prepared_data = processor._prepare_full_data_for_llm(all_data)

    if "products" in prepared_data and "product_status_distribution" in prepared_data["products"]:
        dist = prepared_data["products"]["product_status_distribution"]
        print(f"2. Product distribution: {dist}")
        active_count = dist.get("active", 0)
        print(f"   ✓ Active products in DB: {active_count}")

    # Step 3: Test the fallback directly
    result = processor._create_enhanced_fallback(query, all_data, prepared_data)
    print(f"\n3. Fallback result:")
    print(f"   Answer: {result['answer']}")

    # Validate the answer contains the correct count
    if "102" in result['answer']:
        print("\n✅ SUCCESS: Active products count is correct (102)")
    else:
        print(f"\n❌ FAILED: Expected 102 active products in answer")

    # Test total products for comparison
    print("\n" + "=" * 60)
    query2 = "How many total products do I have?"
    print(f"📝 Query: {query2}")
    print("-" * 40)

    result2 = processor._create_enhanced_fallback(query2, all_data, prepared_data)
    print(f"Answer: {result2['answer']}")

    if "107" in result2['answer']:
        print("\n✅ SUCCESS: Total products count is correct (107)")
    else:
        print(f"\n❌ FAILED: Expected 107 total products in answer")

    # Cleanup
    await mongodb_client.disconnect()

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(validate_fix())