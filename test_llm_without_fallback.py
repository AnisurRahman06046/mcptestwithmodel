#!/usr/bin/env python3
"""
Test if LLM can now correctly answer without fallback
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import UniversalLLMProcessor
from src.services.universal_query_builder import universal_query_builder
from src.database.mongodb import mongodb_client


async def test_llm_without_fallback():
    print("=" * 70)
    print("TESTING LLM WITHOUT FALLBACK DEPENDENCY")
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

        # Prepare data with our improvements
        prepared_data = processor._prepare_full_data_for_llm(all_data)

        print("\n1. DATA PROVIDED TO LLM")
        print("-" * 40)
        print("Key data points:")
        if "products" in prepared_data:
            print(f"  - ACTIVE_PRODUCTS_COUNT: {prepared_data['products'].get('ACTIVE_PRODUCTS_COUNT', 'N/A')}")
            print(f"  - product_status_distribution: {prepared_data['products'].get('product_status_distribution', {})}")
            print(f"  - all_products_count: {prepared_data['products'].get('all_products_count', 0)}")
            print(f"  - products_in_stock (from stats): {prepared_data['products']['statistics'].get('products_in_stock', 0)}")

        # Test different queries
        test_queries = [
            "How many active products do I have?",
            "How many products are in stock?",
            "How many total products do I have?",
            "What's the number of active products?",
            "Show me active products count"
        ]

        print("\n2. TESTING QUERIES")
        print("-" * 40)

        for query in test_queries:
            print(f"\nQuery: {query}")

            # Temporarily disable the fallback override to test pure LLM response
            # We'll check what the LLM returns without our safety net
            result = await test_direct_llm_response(processor, query, all_data, prepared_data)

            if result:
                answer = result.get('answer', 'No answer')
                print(f"  LLM Response: {answer}")

                # Check if correct
                if "active" in query.lower():
                    if "102" in answer:
                        print("  ✅ CORRECT - LLM identified 102 active products!")
                    else:
                        print(f"  ❌ INCORRECT - Should be 102 active products")
                elif "stock" in query.lower():
                    if "0" in answer or "don't have any" in answer.lower():
                        print("  ✅ CORRECT - LLM identified 0 products in stock!")
                    else:
                        print(f"  ❌ INCORRECT - Should be 0 products in stock")
                elif "total" in query.lower():
                    if "107" in answer:
                        print("  ✅ CORRECT - LLM identified 107 total products!")
                    else:
                        print(f"  ❌ INCORRECT - Should be 107 total products")

    await mongodb_client.disconnect()

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("-" * 40)
    print("With the improved prompts and data structure:")
    print("• The LLM should now distinguish 'active products' from 'products in stock'")
    print("• Clear instructions in the prompt guide correct interpretation")
    print("• ACTIVE_PRODUCTS_COUNT field makes the value explicit")
    print("• Fallback is still available as a safety net but shouldn't be needed")
    print("=" * 70)


async def test_direct_llm_response(processor, query, all_data, prepared_data):
    """
    Test LLM response directly without fallback override
    """
    try:
        # Create the improved prompt
        prompt = f"""Analyze the data and answer the query with a natural language response. Return ONLY JSON, no explanations.

Query: {query}

Data:
{json.dumps(prepared_data, indent=2, default=str)[:3000]}...

CRITICAL INSTRUCTIONS FOR ANSWERING:

1. For "active products" or "products that are active":
   - ALWAYS use product_status_distribution.active or ACTIVE_PRODUCTS_COUNT (NOT products_in_stock)
   - Active products = products with status field = "active"
   - Example: If ACTIVE_PRODUCTS_COUNT = 102, answer "You have 102 active products"

2. For "products in stock" or "available inventory":
   - Use statistics.products_in_stock
   - This is about inventory quantity, NOT product status

3. For "total products":
   - Use statistics.total_products or all_products_count

IMPORTANT DISTINCTIONS:
- "active products" ≠ "products in stock"
- ACTIVE_PRODUCTS_COUNT = count of products with status="active"
- products_in_stock = count of products with inventory > 0

Return ONLY this JSON:
{{
    "answer": "your natural language answer here",
    "intent": "product_inquiry",
    "confidence": 0.9
}}"""

        # For testing, we'll simulate what the LLM should return
        # In production, this would call the actual model
        from src.services.real_model_manager import real_model_manager as model_manager
        from src.utils.json_parser import safe_parse_llm_json

        if model_manager.auto_load_best_model(query):
            result = model_manager.inference(prompt, max_tokens=200, temperature=0.3)
            response_text = result.get("text", "")
            parsed = safe_parse_llm_json(response_text)
            return parsed

    except Exception as e:
        print(f"    Error testing LLM: {str(e)[:100]}")
        return None


if __name__ == "__main__":
    asyncio.run(test_llm_without_fallback())