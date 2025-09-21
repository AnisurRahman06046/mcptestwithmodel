#!/usr/bin/env python3
"""
Test script for the enhanced chat API with classification and disambiguation
"""

import requests
import json
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000/api/v1"
SHOP_ID = 10


def test_query(query: str, conversation_id: str = None) -> Dict[str, Any]:
    """Send a query to the enhanced chat endpoint"""

    url = f"{BASE_URL}/chat/enhanced"
    payload = {
        "query": query,
        "shop_id": SHOP_ID
    }

    if conversation_id:
        payload["conversation_id"] = conversation_id

    print(f"\n📝 Query: '{query}'")
    print("-" * 60)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get("needs_clarification"):
            print(f"🤔 Disambiguation needed!")
            print(f"   Question: {result['question']}")
            print(f"   Options:")
            for i, option in enumerate(result['options'], 1):
                print(f"     {i}. {option['description']} (intent: {option['intent']})")
            print(f"   Conversation ID: {result['conversation_id']}")
        else:
            print(f"✅ Response: {result['response']}")
            if result.get('metadata'):
                meta = result['metadata']
                print(f"   Method: {meta.get('method')}")
                print(f"   Intent: {meta.get('intent')}")
                print(f"   Confidence: {meta.get('confidence')}")
                print(f"   Time: {meta.get('execution_time_ms')}ms")
                print(f"   Cached: {meta.get('cached', False)}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def handle_disambiguation(original_query: str, selected_intent: str, conversation_id: str) -> Dict[str, Any]:
    """Handle disambiguation by selecting an intent"""

    url = f"{BASE_URL}/chat/enhanced"
    payload = {
        "selected_intent": selected_intent,
        "original_query": original_query,
        "conversation_id": conversation_id,
        "shop_id": SHOP_ID,
        "query": ""  # Required field but not used for disambiguation
    }

    print(f"\n✋ Selecting: {selected_intent}")
    print("-" * 60)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        print(f"✅ Response: {result['response']}")
        if result.get('metadata'):
            meta = result['metadata']
            print(f"   Method: {meta.get('method')}")
            print(f"   Time: {meta.get('execution_time_ms')}ms")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def get_metrics():
    """Get system metrics"""

    url = f"{BASE_URL}/chat/metrics"

    try:
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()

        if result['success']:
            metrics = result['metrics']
            print("\n📊 System Metrics")
            print("-" * 60)
            print(f"Total queries: {metrics['total_queries']}")
            print(f"Deterministic handled: {metrics['deterministic_handled']} ({metrics['deterministic_rate']:.1%})")
            print(f"LLM handled: {metrics['llm_handled']} ({metrics['llm_rate']:.1%})")
            print(f"Disambiguations: {metrics['disambiguations']} ({metrics['disambiguation_rate']:.1%})")
            print(f"Errors: {metrics['errors']} ({metrics['error_rate']:.1%})")

            # Classifier metrics
            if 'classifier_metrics' in metrics:
                cm = metrics['classifier_metrics']
                print(f"\nClassifier Performance:")
                print(f"  Cache hits: {cm.get('cache_hit_rate', 0):.1%}")
                print(f"  Regex hits: {cm.get('regex_hit_rate', 0):.1%}")
                print(f"  Disambiguation rate: {cm.get('disambiguation_rate', 0):.1%}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting metrics: {e}")
        return {"error": str(e)}


def clear_cache():
    """Clear all caches"""

    url = f"{BASE_URL}/chat/clear-cache"

    try:
        response = requests.post(url)
        response.raise_for_status()
        result = response.json()
        print(f"🧹 Cache cleared: {result['message']}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Error clearing cache: {e}")
        return {"error": str(e)}


def main():
    """Run comprehensive tests"""

    print("=" * 70)
    print("ENHANCED CHAT API TEST")
    print("=" * 70)
    print(f"Testing against: {BASE_URL}")
    print(f"Shop ID: {SHOP_ID}")

    # Clear cache first
    print("\n🧹 Clearing cache...")
    clear_cache()

    # Test cases
    test_cases = [
        # Deterministic queries
        "How many active products do I have?",
        "Show me products in stock",
        "What's the total number of products?",

        # Ambiguous queries (should trigger disambiguation)
        "Show me active inventory",
        "Active products in stock",

        # Complex queries (should use LLM)
        "What were my sales last month?",
        "Show me top selling products",

        # Edge cases
        "active products",  # Should still work with keyword fallback
        "Hello",  # Greeting
        "xyz123"  # Unknown query
    ]

    print("\n" + "=" * 70)
    print("RUNNING TEST QUERIES")
    print("=" * 70)

    for query in test_cases:
        result = test_query(query)

        # Handle disambiguation if needed
        if result.get("needs_clarification"):
            # Simulate user selecting first option
            if result.get("options"):
                selected = result["options"][0]["intent"]
                handle_disambiguation(
                    original_query=query,
                    selected_intent=selected,
                    conversation_id=result["conversation_id"]
                )

    # Show metrics
    print("\n" + "=" * 70)
    print("FINAL METRICS")
    print("=" * 70)
    get_metrics()

    # Test cache behavior
    print("\n" + "=" * 70)
    print("CACHE TEST")
    print("=" * 70)

    print("\n🔄 Testing same query twice (should hit cache second time)...")
    test_query("How many active products do I have?")
    test_query("How many active products do I have?")

    # Final metrics
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    get_metrics()


if __name__ == "__main__":
    main()