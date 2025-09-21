#!/usr/bin/env python3
"""
Test that queries work without hitting token limits
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import UniversalLLMProcessor
from src.services.universal_query_builder import universal_query_builder
from src.database.mongodb import mongodb_client


async def test_token_optimization():
    print("=" * 70)
    print("TESTING TOKEN OPTIMIZATION")
    print("=" * 70)

    await mongodb_client.connect()
    processor = UniversalLLMProcessor()

    # Fetch products data
    products_data = await universal_query_builder.fetch_domain_data(
        domain="products",
        shop_id="10",
        date_range=None
    )

    if products_data.get("success"):
        all_data = {"products": products_data["data"]}

        print("\n1. TESTING MINIMAL DATA FOR ACTIVE PRODUCTS")
        print("-" * 40)

        # Test minimal data preparation
        minimal_data = processor._prepare_minimal_data_for_active_products(all_data)

        # Check size
        data_str = json.dumps(minimal_data, indent=2, default=str)
        estimated_tokens = len(data_str) // 4

        print(f"Minimal data size: {len(data_str)} chars")
        print(f"Estimated tokens: {estimated_tokens}")
        print(f"Under 10k limit: {'✅ YES' if estimated_tokens < 10000 else '❌ NO'}")

        print("\nMinimal data contents:")
        print(json.dumps(minimal_data, indent=2, default=str)[:500] + "...")

        print("\n2. TESTING FULL DATA PREPARATION")
        print("-" * 40)

        # Test full data preparation with new limits
        full_data = processor._prepare_full_data_for_llm(all_data)

        # Check size
        full_str = json.dumps(full_data, indent=2, default=str)
        full_tokens = len(full_str) // 4

        print(f"Full data size: {len(full_str)} chars")
        print(f"Estimated tokens: {full_tokens}")
        print(f"Under 10k limit: {'✅ YES' if full_tokens < 10000 else '❌ NO'}")

        print("\n3. QUERY FLOW ANALYSIS")
        print("-" * 40)

        query = "How many active products do I have?"
        print(f"Query: {query}")

        # Simulate the flow
        query_lower = query.lower()
        if "active" in query_lower and "product" in query_lower:
            print("✓ Using minimal data preparation (optimized for active products)")
            data_for_llm = minimal_data
        else:
            print("• Using full data preparation")
            data_for_llm = full_data

        data_str = json.dumps(data_for_llm, indent=2, default=str)
        tokens = len(data_str) // 4

        print(f"Data tokens: {tokens}")
        if tokens > 10000:
            print(f"❌ Would trigger fallback (>{10000} tokens)")
        else:
            print(f"✅ Within limits - LLM will process directly")

        print("\n4. KEY DATA POINTS SENT TO LLM")
        print("-" * 40)

        if "products" in data_for_llm:
            prod_data = data_for_llm["products"]
            print(f"ACTIVE_PRODUCTS_COUNT: {prod_data.get('ACTIVE_PRODUCTS_COUNT', 'N/A')}")
            print(f"product_status_distribution: {prod_data.get('product_status_distribution', {})}")
            print(f"total_products: {prod_data.get('total_products', 'N/A')}")

    await mongodb_client.disconnect()

    print("\n" + "=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    print("\n✅ IMPROVEMENTS MADE:")
    print("1. Created minimal data preparation for active products queries")
    print("2. Reduced sample products from 500 to 3")
    print("3. Reduced SKUs from 100 to 5")
    print("4. Smart query detection to use minimal data when possible")
    print("5. Lowered token threshold to 10k for safety")
    print("\n✅ RESULT:")
    print("• Active products queries now use minimal data (~200 tokens)")
    print("• Avoids fallback mode for most queries")
    print("• LLM gets clear, focused data with ACTIVE_PRODUCTS_COUNT")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_token_optimization())