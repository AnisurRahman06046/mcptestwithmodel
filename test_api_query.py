#!/usr/bin/env python3
"""
Simple test script to test the Universal Query Processor via API
"""

import requests
import json
from datetime import datetime, timedelta

# API Configuration
API_URL = "http://localhost:8000/api/v1/query"
AUTH_TOKEN = "Bearer your-auth-token-here"  # Replace with actual token

# Test queries
TEST_QUERIES = [
    # Price queries
    "What's the price range of our products?",
    "Show me products under $50",
    "What's the average product price?",

    # Product queries
    "How many products do we have?",
    "Show me all product categories",

    # Sales queries
    "What are our total sales for last week?",
    "Show me top 5 selling products",

    # Inventory queries
    "Which products are low on stock?",
    "What's our total inventory value?",

    # Complex queries
    "What's the average price of our top 10 selling products?",
    "Show me best selling products with their current stock levels",
]

def test_query(query: str, token: str = AUTH_TOKEN):
    """Test a single query"""

    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "processor": "universal",  # Force universal processor
        "options": {
            "verbose": True
        }
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response": result.get("response"),
                "metadata": result.get("metadata"),
                "debug": result.get("debug")
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Main test function"""

    print("=" * 80)
    print("UNIVERSAL QUERY PROCESSOR API TEST")
    print("=" * 80)
    print(f"API URL: {API_URL}")
    print(f"Testing {len(TEST_QUERIES)} queries")
    print("=" * 80)

    # Get auth token if needed
    auth_token = input("\nEnter your auth token (or press Enter to skip): ").strip()
    if auth_token:
        auth_token = f"Bearer {auth_token}"
    else:
        auth_token = AUTH_TOKEN

    # Test each query
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(TEST_QUERIES)}")
        print(f"Query: {query}")
        print("-" * 60)

        result = test_query(query, auth_token)

        if result["success"]:
            print(f"✓ Success")
            print(f"Response: {result['response']}")

            if result.get("metadata"):
                meta = result["metadata"]
                print(f"\nMetadata:")
                print(f"  - Model: {meta.get('model_used')}")
                print(f"  - Domains: {meta.get('tools_called', [])}")
                print(f"  - Intent: {meta.get('query_intent')}")
                print(f"  - Confidence: {meta.get('confidence_score')}")
                print(f"  - Time: {meta.get('execution_time_ms')}ms")

            if result.get("debug") and result["debug"].get("domains_fetched"):
                print(f"\nDebug Info:")
                print(f"  - Domains fetched: {result['debug']['domains_fetched']}")
                if result["debug"].get("data_statistics"):
                    print(f"  - Data statistics:")
                    for domain, stats in result["debug"]["data_statistics"].items():
                        print(f"    {domain}: {json.dumps(stats, indent=6)}")
        else:
            print(f"✗ Failed")
            print(f"Error: {result['error']}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

def test_processor_comparison():
    """Compare universal vs specific tool processors"""

    print("\n" + "=" * 80)
    print("PROCESSOR COMPARISON TEST")
    print("=" * 80)

    test_query = "What's the price range of our products?"

    # Get auth token
    auth_token = input("\nEnter your auth token: ").strip()
    auth_token = f"Bearer {auth_token}"

    headers = {
        "Authorization": auth_token,
        "Content-Type": "application/json"
    }

    # Test with specific tools processor
    print("\n1. SPECIFIC TOOLS PROCESSOR:")
    print("-" * 40)

    payload = {
        "query": test_query,
        "processor": "specific"
    }

    response = requests.post(API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response')}")
        print(f"Tools used: {result.get('metadata', {}).get('tools_called', [])}")
        print(f"Time: {result.get('metadata', {}).get('execution_time_ms')}ms")
    else:
        print(f"Error: HTTP {response.status_code}")

    # Test with universal processor
    print("\n2. UNIVERSAL PROCESSOR:")
    print("-" * 40)

    payload = {
        "query": test_query,
        "processor": "universal"
    }

    response = requests.post(API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response')}")
        print(f"Domains used: {result.get('metadata', {}).get('tools_called', [])}")
        print(f"Time: {result.get('metadata', {}).get('execution_time_ms')}ms")
    else:
        print(f"Error: HTTP {response.status_code}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        test_processor_comparison()
    else:
        main()