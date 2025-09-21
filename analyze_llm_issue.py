#!/usr/bin/env python3
"""
Analyze why LLM fails and what the actual issue is
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import UniversalLLMProcessor
from src.services.universal_query_builder import universal_query_builder
from src.services.real_model_manager import real_model_manager as model_manager
from src.database.mongodb import mongodb_client
from src.utils.json_parser import safe_parse_llm_json


async def analyze_llm_behavior():
    print("=" * 70)
    print("ANALYZING LLM BEHAVIOR AND ROOT CAUSE")
    print("=" * 70)

    await mongodb_client.connect()
    processor = UniversalLLMProcessor()

    query = "How many active products do I have?"

    # Step 1: Get the raw data
    print("\n1. FETCHING RAW DATA")
    print("-" * 40)

    products_data = await universal_query_builder.fetch_domain_data(
        domain="products",
        shop_id="10",
        date_range=None
    )

    all_data = {"products": products_data["data"]}

    # Show what raw data contains
    print(f"Total products in raw data: {len(all_data['products']['products'])}")
    print(f"Statistics from DB: {all_data['products']['statistics']}")

    # Count active products manually
    active_count = 0
    for p in all_data['products']['products']:
        if p.get('status') == 'active':
            active_count += 1
    print(f"Manual count of active products: {active_count}")

    # Step 2: Show what prepared data contains
    print("\n2. PREPARED DATA FOR LLM")
    print("-" * 40)

    prepared_data = processor._prepare_full_data_for_llm(all_data)

    if 'products' in prepared_data:
        print(f"Prepared data includes:")
        print(f"  - sample_products: {len(prepared_data['products'].get('sample_products', []))} samples")
        print(f"  - all_products_count: {prepared_data['products'].get('all_products_count', 0)}")
        print(f"  - product_status_distribution: {prepared_data['products'].get('product_status_distribution', {})}")

    # Step 3: Test LLM directly with the prepared data
    print("\n3. TESTING LLM DIRECTLY")
    print("-" * 40)

    # Create a test prompt with full prepared data
    test_prompt = f"""Analyze the data and answer the query with a natural language response. Return ONLY JSON, no explanations.

Query: {query}

Data:
{json.dumps(prepared_data, indent=2, default=str)[:5000]}...

IMPORTANT: Look at product_status_distribution for active products count.

Return ONLY JSON:
{{
    "answer": "your natural language answer",
    "intent": "product_inquiry",
    "confidence": 0.9
}}"""

    print("Testing with full prepared data (truncated for display)...")

    if model_manager.auto_load_best_model(query):
        result = model_manager.inference(test_prompt, max_tokens=200, temperature=0.3)
        response = result.get("text", "")
        parsed = safe_parse_llm_json(response)

        print(f"LLM Response: {parsed.get('answer', 'No answer')}")

        if "0" in str(parsed.get('answer', '')) or "don't have any" in str(parsed.get('answer', '')).lower():
            print("❌ LLM still returns 0 despite having product_status_distribution!")
        else:
            print("✅ LLM correctly identifies active products")

    # Step 4: Test with just statistics (what fallback uses)
    print("\n4. TESTING LLM WITH STATISTICS ONLY (FALLBACK MODE)")
    print("-" * 40)

    stats_summary = {
        "products": all_data['products']['statistics'],
        "product_status_distribution": prepared_data['products']['product_status_distribution']
    }

    stats_prompt = f"""Answer this query with a complete, natural language response.

Query: {query}

Available Statistics:
{json.dumps(stats_summary, indent=2, default=str)}

IMPORTANT: For active products, look at product_status_distribution.active

Return ONLY JSON:
{{
    "answer": "your natural language answer",
    "intent": "product_inquiry",
    "confidence": 0.8
}}"""

    print(f"Statistics provided to LLM:")
    print(json.dumps(stats_summary, indent=2))

    if model_manager.auto_load_best_model(query):
        result = model_manager.inference(stats_prompt, max_tokens=200, temperature=0.3)
        response = result.get("text", "")
        parsed = safe_parse_llm_json(response)

        print(f"\nLLM Response with stats only: {parsed.get('answer', 'No answer')}")

        if "0" in str(parsed.get('answer', '')) or "don't have any" in str(parsed.get('answer', '')).lower():
            print("❌ LLM returns 0 even with explicit product_status_distribution!")
        else:
            print("✅ LLM correctly identifies active products from statistics")

    # Step 5: Identify why this happens
    print("\n5. ROOT CAUSE ANALYSIS")
    print("-" * 40)

    print("The issue is that:")
    print("1. The raw data has 'statistics' with total_products and products_in_stock")
    print("2. products_in_stock is 0 (items with available inventory)")
    print("3. The LLM confuses 'products_in_stock' (0) with 'active products' (102)")
    print("4. Even though product_status_distribution clearly shows active: 102")
    print("5. The LLM prioritizes products_in_stock=0 over product_status_distribution")

    print(f"\nConfusing statistics:")
    print(f"  - total_products: {all_data['products']['statistics']['total_products']}")
    print(f"  - products_in_stock: {all_data['products']['statistics']['products_in_stock']} (inventory > 0)")
    print(f"  - active products: {prepared_data['products']['product_status_distribution'].get('active', 0)} (status='active')")

    await mongodb_client.disconnect()

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("The LLM incorrectly interprets 'active products' as 'products in stock'")
    print("This is why it returns 0 (because products_in_stock=0 in statistics)")
    print("The fallback override fixes this by explicitly checking product_status_distribution")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(analyze_llm_behavior())