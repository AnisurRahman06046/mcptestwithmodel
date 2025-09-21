#!/usr/bin/env python3
"""
Test script specifically for greeting handling
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.universal_llm_processor import UniversalLLMProcessor

async def test_greeting():
    processor = UniversalLLMProcessor()

    test_queries = [
        "Hi",
        "Hello",
        "Hey there",
        "Good morning",
        "How many products do you have?",
        "What's the total sales today?"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('-'*60)

        try:
            # Test domain identification
            domains = await processor._identify_domains(query)
            print(f"Domains identified: {domains}")

            # Test full processing
            context = {"shop_id": "10"}
            result = await processor.process_query(query, context)

            if result.get("success"):
                print(f"Response: {result.get('response', 'No response')[:200]}")
                if result.get("metadata"):
                    print(f"Intent: {result['metadata'].get('query_intent')}")
                    print(f"Tools called: {result['metadata'].get('tools_called')}")
            else:
                print(f"Error: {result.get('error')}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_greeting())