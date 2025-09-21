#!/usr/bin/env python3
"""
Direct test of the fallback logic for active products
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import UniversalLLMProcessor
from src.services.universal_query_builder import universal_query_builder
from src.database.mongodb import mongodb_client


async def test_fallback_directly():
    """
    Test the fallback logic directly
    """
    print("=" * 60)
    print("DIRECT FALLBACK TEST")
    print("=" * 60)

    # Connect to MongoDB
    if not mongodb_client.is_connected:
        await mongodb_client.connect()
        print("✓ Connected to MongoDB")

    # Initialize processor
    processor = UniversalLLMProcessor()

    # Fetch products data
    print("\n1. Fetching products data...")
    products_data = await universal_query_builder.fetch_domain_data(
        domain="products",
        shop_id="10",
        date_range=None
    )

    if products_data.get("success"):
        all_data = {"products": products_data["data"]}
        print(f"✓ Fetched {products_data['data']['statistics']['total_products']} products")

        # Prepare the data (this adds product_status_distribution)
        print("\n2. Preparing data for LLM...")
        prepared_data = processor._prepare_full_data_for_llm(all_data)

        # Check product_status_distribution
        if "products" in prepared_data and "product_status_distribution" in prepared_data["products"]:
            dist = prepared_data["products"]["product_status_distribution"]
            print(f"✓ Product status distribution: {dist}")
            print(f"   Active products: {dist.get('active', 0)}")
        else:
            print("✗ No product_status_distribution found")

        # Test the fallback function directly
        print("\n3. Testing fallback logic...")
        query = "How many active products do I have?"

        result = processor._create_enhanced_fallback(query, all_data, prepared_data)

        print(f"\n📝 Query: {query}")
        print(f"✅ Answer: {result['answer']}")
        print(f"   Intent: {result['intent']}")
        print(f"   Confidence: {result['confidence']}")

        # Test other variations
        print("\n4. Testing query variations...")
        variations = [
            "How many products are active?",
            "What's the number of active products?",
            "Show me active products count"
        ]

        for q in variations:
            result = processor._create_enhanced_fallback(q, all_data, prepared_data)
            print(f"\nQuery: {q}")
            print(f"  → {result['answer']}")

    # Cleanup
    if mongodb_client.is_connected:
        await mongodb_client.disconnect()
        print("\n✓ Disconnected from MongoDB")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_fallback_directly())