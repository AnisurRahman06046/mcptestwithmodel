#!/usr/bin/env python3
"""
Integration test for the Query Classification System
Tests the actual implementation with mock database
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import just what we need, avoiding the __init__ that has other dependencies
import importlib.util

# Load query_classifier module directly
spec1 = importlib.util.spec_from_file_location(
    "query_classifier",
    Path(__file__).parent / "src/services/query_classifier.py"
)
query_classifier_module = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(query_classifier_module)
QueryClassifier = query_classifier_module.QueryClassifier
ClassificationResult = query_classifier_module.ClassificationResult

# Load deterministic_processor module directly
spec2 = importlib.util.spec_from_file_location(
    "deterministic_processor",
    Path(__file__).parent / "src/services/deterministic_processor.py"
)
deterministic_processor_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(deterministic_processor_module)
DeterministicProcessor = deterministic_processor_module.DeterministicProcessor


# Mock MongoDB client for testing
class MockMongoDBClient:
    """Mock MongoDB client for testing"""

    def __init__(self):
        self.is_connected = True
        self.database = MockDatabase()


class MockDatabase:
    """Mock database with test data"""

    def __init__(self):
        # Mock product collection
        self.product_data = (
            [{"shop_id": 10, "status": "active"} for _ in range(102)]
            + [{"shop_id": 10, "status": "inactive"}]
            + [{"shop_id": 10, "status": "draft"} for _ in range(4)]
        )

        # Mock warehouse collection
        self.warehouse_data = [
            {"shop_id": 10, "product_id": i, "available_quantity": 0}
            for i in range(107)
        ]

    def __getitem__(self, collection):
        if collection == "product":
            return MockCollection(self.product_data)
        elif collection == "warehouse":
            return MockCollection(self.warehouse_data)
        return MockCollection([])


class MockCollection:
    """Mock MongoDB collection"""

    def __init__(self, data):
        self.data = data

    async def count_documents(self, filter_query):
        """Mock count_documents"""
        count = 0
        for doc in self.data:
            if self._matches_filter(doc, filter_query):
                count += 1
        return count

    def _matches_filter(self, doc, filter_query):
        """Check if document matches filter"""
        for key, value in filter_query.items():
            if key not in doc:
                return False

            if isinstance(value, dict):
                # Handle operators like $gt, $eq, etc.
                doc_value = doc[key]
                for op, op_value in value.items():
                    if op == "$gt" and not (doc_value > op_value):
                        return False
                    elif op == "$eq" and not (doc_value == op_value):
                        return False
                    elif op == "$lte" and not (doc_value <= op_value):
                        return False
            else:
                if doc[key] != value:
                    return False
        return True


async def test_integration():
    """Run integration tests"""
    print("=" * 80)
    print("QUERY CLASSIFICATION SYSTEM - INTEGRATION TEST")
    print("=" * 80)

    # Initialize components
    classifier = QueryClassifier()
    mock_client = MockMongoDBClient()
    processor = DeterministicProcessor(mongodb_client=mock_client)

    # Test cases
    test_cases = [
        {
            "query": "How many active products do I have?",
            "expected_intent": "active_products",
            "expected_response": "You have 102 active products.",
            "should_be_deterministic": True
        },
        {
            "query": "Show me products in stock",
            "expected_intent": "products_in_stock",
            "expected_response": "You don't have any products in stock.",
            "should_be_deterministic": True
        },
        {
            "query": "What's the total number of products?",
            "expected_intent": "total_products",
            "expected_response": "You have 107 total products.",
            "should_be_deterministic": True
        },
        {
            "query": "Show me active products in stock",
            "expected_intent": "ambiguous",
            "expected_response": None,
            "should_disambiguate": True
        },
        {
            "query": "Sales report for last month",
            "expected_intent": "sales_analysis",
            "expected_response": None,
            "should_be_deterministic": False
        }
    ]

    context = {"shop_id": "10", "user_id": "test"}

    print("\n📝 Running Integration Tests")
    print("-" * 40)

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\n🔍 Query: '{test['query']}'")

        # Step 1: Classify query
        result = classifier.classify(test["query"], context)
        print(f"   Classification: {result.intent} (confidence: {result.confidence:.2f})")

        # Check classification
        if test.get("should_disambiguate"):
            if result.needs_clarification:
                print(f"   ✅ Correctly triggered disambiguation")
                print(f"      Options: {[opt['intent'] for opt in result.disambiguation_options]}")
                passed += 1
            else:
                print(f"   ❌ Should have triggered disambiguation")
                failed += 1
            continue

        if result.intent != test["expected_intent"]:
            print(f"   ❌ Expected intent: {test['expected_intent']}, got: {result.intent}")
            failed += 1
            continue

        # Step 2: Process deterministically if applicable
        if result.use_deterministic:
            if not test["should_be_deterministic"]:
                print(f"   ❌ Should not be deterministic")
                failed += 1
                continue

            # Process with deterministic processor
            response = await processor.process(result.intent, context)

            if response["success"]:
                actual_response = response["response"]
                print(f"   Response: '{actual_response}'")

                if actual_response == test["expected_response"]:
                    print(f"   ✅ Correct response")
                    passed += 1
                else:
                    print(f"   ❌ Expected: '{test['expected_response']}'")
                    failed += 1
            else:
                print(f"   ❌ Processing failed: {response['error']}")
                failed += 1
        else:
            if test["should_be_deterministic"]:
                print(f"   ❌ Should be deterministic")
                failed += 1
            else:
                print(f"   ✅ Correctly identified as non-deterministic")
                passed += 1

    # Test disambiguation flow
    print("\n\n🔀 Testing Disambiguation Flow")
    print("-" * 40)

    ambiguous_query = "Show me active inventory"
    result = classifier.classify(ambiguous_query, context)

    if result.needs_clarification:
        print(f"Query: '{ambiguous_query}'")
        print(f"System: {result.metadata['question']}")
        print("\nOptions:")
        for i, option in enumerate(result.disambiguation_options, 1):
            print(f"  {i}. {option['description']}")

        # Simulate user selection
        selected_intent = "active_products"
        print(f"\nUser selects: {selected_intent}")

        # Process with selected intent
        response = await processor.process(selected_intent, context)
        print(f"Final response: {response['response']}")
        passed += 1
    else:
        print("❌ Disambiguation not triggered")
        failed += 1

    # Show metrics
    print("\n\n📊 Performance Metrics")
    print("-" * 40)

    classifier_metrics = classifier.get_metrics()
    processor_metrics = processor.get_metrics()

    print("Classifier Metrics:")
    for key, value in classifier_metrics.items():
        if "rate" in key:
            print(f"  {key}: {value:.2%}")
        else:
            print(f"  {key}: {value}")

    print("\nProcessor Metrics:")
    for key, value in processor_metrics.items():
        if "rate" in key:
            print(f"  {key}: {value:.2%}")
        else:
            print(f"  {key}: {value}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")

    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed. Review before deployment.")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_integration())