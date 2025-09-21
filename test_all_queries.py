#!/usr/bin/env python3
"""
Comprehensive test of all query types
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import universal_llm_processor
from src.database.mongodb import mongodb_client


async def test_all_queries():
    """
    Test all query types to ensure nothing is broken
    """
    print("=" * 70)
    print("COMPREHENSIVE QUERY VALIDATION TEST")
    print("=" * 70)

    context = {"shop_id": "10", "user_id": "test"}

    # Define test cases with expected values
    test_cases = [
        {
            "category": "Product Queries",
            "queries": [
                ("How many active products do I have?", "102", "active"),
                ("How many total products do I have?", "107", "products"),
                ("How many products are active?", "102", "active"),
                ("What's the total number of products?", "107", "products")
            ]
        },
        {
            "category": "Sales Queries",
            "queries": [
                ("What is the total sales of last month?", "$0", None),
                ("What is the total sales of May?", "$0", "May"),
                ("What are our sales for September?", "$0", "September"),
                ("Show me sales for this month", "$0", None)
            ]
        },
        {
            "category": "Order Queries",
            "queries": [
                ("How many orders do we have today?", "0", "today"),
                ("Show me yesterday's orders", "0", "yesterday"),
                ("What's the order count for this week?", "0", "week")
            ]
        }
    ]

    total_passed = 0
    total_failed = 0
    failed_queries = []

    for category in test_cases:
        print(f"\n📋 {category['category']}")
        print("-" * 70)

        for query, expected_value, expected_keyword in category["queries"]:
            try:
                # Process the query
                result = await universal_llm_processor.process_query(query, context)

                if result["success"]:
                    response = result['response']

                    # Check if expected value is in response
                    passed = expected_value.lower() in response.lower()

                    # Also check for expected keyword if provided
                    if expected_keyword and passed:
                        passed = expected_keyword.lower() in response.lower()

                    if passed:
                        print(f"  ✅ {query}")
                        print(f"     → {response}")
                        total_passed += 1
                    else:
                        print(f"  ❌ {query}")
                        print(f"     Expected: {expected_value}")
                        print(f"     Got: {response}")
                        total_failed += 1
                        failed_queries.append((query, expected_value, response))
                else:
                    print(f"  ❌ {query}")
                    print(f"     Error: Query failed")
                    total_failed += 1
                    failed_queries.append((query, expected_value, "Query failed"))

            except Exception as e:
                print(f"  ❌ {query}")
                print(f"     Exception: {str(e)[:100]}")
                total_failed += 1
                failed_queries.append((query, expected_value, str(e)[:100]))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"📊 Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")

    if failed_queries:
        print("\n❌ Failed Queries Details:")
        for query, expected, got in failed_queries:
            print(f"\n  Query: {query}")
            print(f"  Expected: {expected}")
            print(f"  Got: {got}")

    print("\n" + "=" * 70)
    print(f"TEST COMPLETED at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    # Run with timeout to prevent hanging
    try:
        asyncio.run(asyncio.wait_for(test_all_queries(), timeout=60))
    except asyncio.TimeoutError:
        print("\n⚠️  Test timed out after 60 seconds")
        sys.exit(1)