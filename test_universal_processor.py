#!/usr/bin/env python3
"""
Test script for the Universal Query Builder and LLM Processor
Tests various query types to ensure flexibility
"""

import asyncio
import json
from src.services.universal_llm_processor import universal_llm_processor
from src.database.mongodb import mongodb_client

# Test queries to verify the system handles various types
TEST_QUERIES = [
    # Price-related queries
    "What's the price range of our products?",
    "Show me products under $50",
    "What's the average product price?",
    "Which products are most expensive?",

    # Product count/inventory queries
    "How many products do we have?",
    "How many products are in stock?",
    "Show me low stock items",
    "What's our inventory value?",

    # Sales queries
    "What are our total sales?",
    "Show me top 5 selling products",
    "What's the revenue for last week?",
    "Which products generated most revenue?",

    # Complex queries requiring multiple domains
    "Show me best selling products with their current stock levels",
    "What's the average price of our top 10 selling products?",
    "How many customers bought products over $100?",

    # Customer queries
    "How many customers do we have?",
    "Who are our VIP customers?",
    "Show me customers who haven't ordered recently",
]

async def test_universal_processor():
    """Test the universal processor with various queries"""

    print("=" * 80)
    print("UNIVERSAL QUERY PROCESSOR TEST")
    print("=" * 80)

    # Connect to database
    if not mongodb_client.is_connected:
        await mongodb_client.connect()
        print("✓ Connected to MongoDB")

    # Test context
    context = {
        "shop_id": "10",
        "user_id": "test_user"
    }

    # Run test queries
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(TEST_QUERIES)}")
        print(f"Query: {query}")
        print("-" * 60)

        try:
            # Process query
            result = await universal_llm_processor.process_query(query, context)

            if result["success"]:
                print(f"✓ Success")
                print(f"Response: {result['response']}")
                print(f"Domains used: {result['metadata']['tools_called']}")
                print(f"Confidence: {result['metadata']['confidence_score']}")
                print(f"Execution time: {result['metadata']['execution_time_ms']}ms")

                # Show debug info if available
                if result.get("debug") and result["debug"].get("data_statistics"):
                    print("\nData fetched:")
                    for domain, stats in result["debug"]["data_statistics"].items():
                        print(f"  - {domain}: {json.dumps(stats, indent=4)}")
            else:
                print(f"✗ Failed")
                print(f"Error: {result.get('error')}")

        except Exception as e:
            print(f"✗ Exception: {e}")

        # Small delay between queries
        await asyncio.sleep(1)

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

async def compare_processors():
    """Compare old vs new processor on the same query"""

    print("\n" + "=" * 80)
    print("PROCESSOR COMPARISON TEST")
    print("=" * 80)

    test_query = "What's the price range of our products?"
    context = {"shop_id": "10", "user_id": "test_user"}

    # Test with old processor (specific tools)
    print("\n1. OLD PROCESSOR (Specific Tools):")
    print("-" * 40)

    from src.services.llm_query_processor import llm_query_processor

    try:
        result_old = await llm_query_processor.process_query(test_query, context)
        if result_old["success"]:
            print(f"Response: {result_old['response']}")
            print(f"Tools used: {result_old['metadata']['tools_called']}")
            print(f"Time: {result_old['metadata']['execution_time_ms']}ms")
    except Exception as e:
        print(f"Error: {e}")

    # Test with new processor (universal)
    print("\n2. NEW PROCESSOR (Universal):")
    print("-" * 40)

    try:
        result_new = await universal_llm_processor.process_query(test_query, context)
        if result_new["success"]:
            print(f"Response: {result_new['response']}")
            print(f"Domains used: {result_new['metadata']['tools_called']}")
            print(f"Time: {result_new['metadata']['execution_time_ms']}ms")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 80)

async def main():
    """Main test function"""

    # Run universal processor tests
    await test_universal_processor()

    # Compare processors
    await compare_processors()

    # Cleanup
    if mongodb_client.is_connected:
        await mongodb_client.disconnect()
        print("\n✓ Disconnected from MongoDB")

if __name__ == "__main__":
    asyncio.run(main())