#!/usr/bin/env python3
"""
Test script to verify the active products fix
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_llm_processor import universal_llm_processor


async def test_queries():
    """
    Test various queries to ensure they work correctly
    """
    print("=" * 60)
    print("TESTING QUERY FIXES")
    print("=" * 60)

    context = {"shop_id": "10", "user_id": "test"}

    test_cases = [
        {
            "query": "How many active products do I have?",
            "expected_contains": ["102", "active products"]
        },
        {
            "query": "How many total products do I have?",
            "expected_contains": ["107", "products"]
        },
        {
            "query": "What is the total sales of last month?",
            "expected_contains": ["$0", "sales"]
        },
        {
            "query": "What is the total sales of May?",
            "expected_contains": ["$0", "May"]
        },
        {
            "query": "How many products are active?",
            "expected_contains": ["102", "active"]
        },
        {
            "query": "Show me active products count",
            "expected_contains": ["102", "active"]
        }
    ]

    for test in test_cases:
        print(f"\n📝 Query: {test['query']}")
        print("-" * 40)

        try:
            result = await universal_llm_processor.process_query(test['query'], context)

            if result["success"]:
                response = result['response']
                print(f"✅ Response: {response}")

                # Check if expected content is in response
                matches = []
                for expected in test['expected_contains']:
                    if expected.lower() in response.lower():
                        matches.append(expected)

                if len(matches) == len(test['expected_contains']):
                    print(f"✓ All expected content found: {matches}")
                else:
                    print(f"⚠️  Only found {matches} out of {test['expected_contains']}")

            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_queries())