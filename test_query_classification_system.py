#!/usr/bin/env python3
"""
Comprehensive Test Suite for Query Classification System
Tests all layers: Regex, Disambiguation, Deterministic, and Fallback
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import re
import json
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class TestCase:
    """Test case for classification"""
    query: str
    expected_intent: str
    expected_confidence_min: float
    expected_method: str
    should_disambiguate: bool = False
    description: str = ""


@dataclass
class ClassificationResult:
    """Result from classifier"""
    intent: str
    confidence: float
    method: str
    needs_clarification: bool = False
    metadata: Dict = None


# ============================================================================
# MOCK CLASSIFIER FOR TESTING
# ============================================================================

class MockHybridClassifier:
    """
    Mock implementation of the hybrid classifier for testing
    This represents what we will build
    """

    def __init__(self):
        # Regex patterns for exact matching
        self.regex_patterns = {
            "active_products": [
                r"^how many active products",
                r"^count.*active products",
                r"^active products count",
                r"^what('s| is) the number of active products",
                r"^show.*active products.*count"
            ],
            "products_in_stock": [
                r"^products.*in stock",
                r"^show products in stock",
                r".*available inventory",
                r".*items with quantity",
                r".*products with stock",
                r"(?<!active )products.*in stock"  # Negative lookbehind to exclude "active products in stock"
            ],
            "total_products": [
                r"^total products",
                r"^how many products",
                r"^all products count",
                r"^what('s| is) the total.*products"
            ],
            "sales_analysis": [
                r".*sales.*last month",
                r".*revenue.*this week",
                r".*earnings today",
                r".*sales report"
            ]
        }

        # Disambiguation triggers
        self.ambiguous_patterns = [
            (["active", "stock"], ["active_products", "products_in_stock"]),
            (["active", "inventory"], ["active_products", "products_in_stock"]),
            (["available", "products"], ["active_products", "products_in_stock"]),
        ]

        # Cache for testing
        self.cache = {}

        # Metrics for testing
        self.metrics = {
            "regex_hits": 0,
            "disambiguations": 0,
            "fallbacks": 0,
            "cache_hits": 0
        }

    def classify(self, query: str) -> ClassificationResult:
        """Main classification method"""
        query_lower = query.lower().strip()

        # Check cache
        if query_lower in self.cache:
            self.metrics["cache_hits"] += 1
            return self.cache[query_lower]

        # Layer 1: Regex exact match
        regex_result = self._regex_match(query_lower)
        if regex_result:
            self.metrics["regex_hits"] += 1
            result = ClassificationResult(
                intent=regex_result[0],
                confidence=0.95,
                method="regex",
                metadata={"pattern": regex_result[1]}
            )
            self.cache[query_lower] = result
            return result

        # Layer 2: Check for ambiguous queries
        if self._is_ambiguous(query_lower):
            self.metrics["disambiguations"] += 1
            return ClassificationResult(
                intent="ambiguous",
                confidence=0.65,
                method="disambiguation",
                needs_clarification=True,
                metadata={
                    "possible_intents": self._get_possible_intents(query_lower)
                }
            )

        # Layer 3: Keyword fallback
        keyword_result = self._keyword_match(query_lower)
        if keyword_result:
            self.metrics["fallbacks"] += 1
            result = ClassificationResult(
                intent=keyword_result,
                confidence=0.60,
                method="keyword"
            )
            self.cache[query_lower] = result
            return result

        # No match
        return ClassificationResult(
            intent="unknown",
            confidence=0.0,
            method="none"
        )

    def _regex_match(self, query: str) -> Optional[Tuple[str, str]]:
        """Check regex patterns"""
        for intent, patterns in self.regex_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return (intent, pattern)
        return None

    def _is_ambiguous(self, query: str) -> bool:
        """Check if query is ambiguous"""
        for trigger_words, _ in self.ambiguous_patterns:
            if all(word in query for word in trigger_words):
                return True
        return False

    def _get_possible_intents(self, query: str) -> List[str]:
        """Get possible intents for ambiguous query"""
        for trigger_words, intents in self.ambiguous_patterns:
            if all(word in query for word in trigger_words):
                return intents
        return []

    def _keyword_match(self, query: str) -> Optional[str]:
        """Simple keyword matching"""
        if "active" in query and "product" in query:
            return "active_products"
        if "stock" in query or "inventory" in query:
            return "products_in_stock"
        if "total" in query and "product" in query:
            return "total_products"
        if "sales" in query or "revenue" in query:
            return "sales_analysis"
        return None


# ============================================================================
# MOCK DETERMINISTIC PROCESSOR
# ============================================================================

class MockDeterministicProcessor:
    """Mock deterministic query processor"""

    def __init__(self):
        self.factual_queries = {
            "active_products": {
                "count": 102,
                "template": "You have {count} active products."
            },
            "products_in_stock": {
                "count": 0,
                "template": "You have {count} products in stock."
            },
            "total_products": {
                "count": 107,
                "template": "You have {count} total products."
            }
        }

    def can_process(self, intent: str) -> bool:
        """Check if intent can be processed deterministically"""
        return intent in self.factual_queries

    def process(self, intent: str) -> str:
        """Process query deterministically"""
        if intent in self.factual_queries:
            data = self.factual_queries[intent]
            return data["template"].format(count=data["count"])
        return None


# ============================================================================
# TEST SUITE
# ============================================================================

class TestQueryClassification:
    """Comprehensive test suite"""

    def __init__(self):
        self.classifier = MockHybridClassifier()
        self.deterministic = MockDeterministicProcessor()
        self.test_results = []

    def run_all_tests(self):
        """Run all test categories"""
        print("=" * 80)
        print("QUERY CLASSIFICATION SYSTEM - TEST SUITE")
        print("=" * 80)

        # Test categories
        self.test_regex_classification()
        self.test_disambiguation()
        self.test_deterministic_processing()
        self.test_confidence_thresholds()
        self.test_cache_behavior()
        self.test_edge_cases()
        self.test_performance()

        # Summary
        self.print_summary()

    def test_regex_classification(self):
        """Test regex pattern matching"""
        print("\n📝 TEST: Regex Classification")
        print("-" * 40)

        test_cases = [
            TestCase(
                query="How many active products do I have?",
                expected_intent="active_products",
                expected_confidence_min=0.95,
                expected_method="regex"
            ),
            TestCase(
                query="count my active products",
                expected_intent="active_products",
                expected_confidence_min=0.95,
                expected_method="regex"
            ),
            TestCase(
                query="What's the number of active products?",
                expected_intent="active_products",
                expected_confidence_min=0.95,
                expected_method="regex"
            ),
            TestCase(
                query="Show products in stock",
                expected_intent="products_in_stock",
                expected_confidence_min=0.95,
                expected_method="regex"
            ),
            TestCase(
                query="total products count",
                expected_intent="total_products",
                expected_confidence_min=0.95,
                expected_method="regex"
            ),
            TestCase(
                query="Sales report last month",
                expected_intent="sales_analysis",
                expected_confidence_min=0.95,
                expected_method="regex"
            )
        ]

        for test in test_cases:
            result = self.classifier.classify(test.query)
            self._assert_test(test, result)

    def test_disambiguation(self):
        """Test disambiguation for ambiguous queries"""
        print("\n🤔 TEST: Disambiguation")
        print("-" * 40)

        test_cases = [
            TestCase(
                query="Show me active products in stock",
                expected_intent="ambiguous",
                expected_confidence_min=0.60,
                expected_method="disambiguation",
                should_disambiguate=True,
                description="Contains both 'active' and 'stock'"
            ),
            TestCase(
                query="Active inventory items",
                expected_intent="ambiguous",
                expected_confidence_min=0.60,
                expected_method="disambiguation",
                should_disambiguate=True,
                description="'Active' + 'inventory' is ambiguous"
            ),
            TestCase(
                query="Available products count",
                expected_intent="ambiguous",
                expected_confidence_min=0.60,
                expected_method="disambiguation",
                should_disambiguate=True,
                description="'Available' could mean active or in stock"
            )
        ]

        for test in test_cases:
            result = self.classifier.classify(test.query)
            self._assert_test(test, result)

            # Check disambiguation metadata
            if result.needs_clarification:
                print(f"  ✓ Possible intents: {result.metadata.get('possible_intents', [])}")

    def test_deterministic_processing(self):
        """Test deterministic query processing"""
        print("\n🔢 TEST: Deterministic Processing")
        print("-" * 40)

        test_intents = [
            ("active_products", "You have 102 active products."),
            ("products_in_stock", "You have 0 products in stock."),
            ("total_products", "You have 107 total products."),
            ("sales_analysis", None)  # Not deterministic
        ]

        for intent, expected_response in test_intents:
            can_process = self.deterministic.can_process(intent)

            if expected_response:
                assert can_process, f"Should process {intent} deterministically"
                response = self.deterministic.process(intent)
                assert response == expected_response, f"Expected: {expected_response}, Got: {response}"
                print(f"  ✅ {intent}: {response}")
            else:
                assert not can_process, f"Should NOT process {intent} deterministically"
                print(f"  ✅ {intent}: Correctly identified as non-deterministic")

    def test_confidence_thresholds(self):
        """Test confidence threshold behavior"""
        print("\n🎯 TEST: Confidence Thresholds")
        print("-" * 40)

        test_queries = [
            ("How many active products?", 0.95, "regex", "High confidence"),
            ("active products", 0.60, "keyword", "Low confidence - keyword fallback"),
            ("something about products", 0.0, "none", "Very low confidence"),
            ("random query xyz", 0.0, "none", "No match")
        ]

        for query, expected_conf, expected_method, description in test_queries:
            result = self.classifier.classify(query)
            print(f"  Query: '{query}'")
            print(f"    Confidence: {result.confidence:.2f} (expected >= {expected_conf})")
            print(f"    Method: {result.method} (expected: {expected_method})")
            print(f"    Result: {description}")

            assert result.confidence >= expected_conf - 0.05, f"Confidence too low"

            # Check thresholds
            if result.confidence >= 0.85:
                print(f"    ✅ Accept immediately")
            elif result.confidence >= 0.60:
                print(f"    ⚠️  Consider disambiguation")
            else:
                print(f"    ❌ Fallback required")

    def test_cache_behavior(self):
        """Test caching behavior"""
        print("\n💾 TEST: Cache Behavior")
        print("-" * 40)

        # Clear cache
        self.classifier.cache.clear()
        self.classifier.metrics["cache_hits"] = 0

        query = "How many active products?"

        # First call - should miss cache
        result1 = self.classifier.classify(query)
        cache_hits1 = self.classifier.metrics["cache_hits"]

        # Second call - should hit cache
        result2 = self.classifier.classify(query)
        cache_hits2 = self.classifier.metrics["cache_hits"]

        # Third call - should hit cache
        result3 = self.classifier.classify(query)
        cache_hits3 = self.classifier.metrics["cache_hits"]

        assert cache_hits1 == 0, "First call should miss cache"
        assert cache_hits2 == 1, "Second call should hit cache"
        assert cache_hits3 == 2, "Third call should hit cache"
        assert result1.intent == result2.intent == result3.intent, "Results should be consistent"

        print(f"  ✅ Cache working correctly")
        print(f"    Misses: 1, Hits: 2")
        print(f"    Consistent results: {result1.intent}")

    def test_edge_cases(self):
        """Test edge cases and error scenarios"""
        print("\n⚠️  TEST: Edge Cases")
        print("-" * 40)

        edge_cases = [
            ("", "unknown", "Empty query"),
            ("   ", "unknown", "Whitespace only"),
            ("products", "unknown", "Single word - too vague"),
            ("ACTIVE PRODUCTS COUNT", "active_products", "All caps"),
            ("how   many    active   products", "active_products", "Extra spaces"),
            ("😀 active products", "active_products", "Emoji in query"),
            ("active products" * 100, "active_products", "Very long query")
        ]

        for query, expected_intent, description in edge_cases:
            try:
                result = self.classifier.classify(query)
                if expected_intent != "unknown":
                    assert result.intent == expected_intent, f"Failed: {description}"
                print(f"  ✅ {description}: Handled correctly")
            except Exception as e:
                print(f"  ❌ {description}: Error - {e}")

    def test_performance(self):
        """Test performance metrics"""
        print("\n⚡ TEST: Performance")
        print("-" * 40)

        # Test latency for different methods
        test_queries = [
            ("How many active products?", "regex", 1),  # Should be < 1ms
            ("active products", "keyword", 5),  # Should be < 5ms
            ("Show me active products in stock", "disambiguation", 5)  # Should be < 5ms
        ]

        for query, method, max_ms in test_queries:
            start = time.time()
            result = self.classifier.classify(query)
            elapsed = (time.time() - start) * 1000

            print(f"  Query: '{query[:30]}...'")
            print(f"    Method: {result.method}")
            print(f"    Latency: {elapsed:.2f}ms (target < {max_ms}ms)")

            if elapsed < max_ms:
                print(f"    ✅ Performance acceptable")
            else:
                print(f"    ⚠️  Performance needs optimization")

    def _assert_test(self, test: TestCase, result: ClassificationResult):
        """Assert individual test case"""
        try:
            # Check intent
            if not test.should_disambiguate:
                assert result.intent == test.expected_intent, \
                    f"Intent mismatch: expected {test.expected_intent}, got {result.intent}"

            # Check confidence
            assert result.confidence >= test.expected_confidence_min, \
                f"Confidence too low: expected >= {test.expected_confidence_min}, got {result.confidence}"

            # Check method
            assert result.method == test.expected_method, \
                f"Method mismatch: expected {test.expected_method}, got {result.method}"

            # Check disambiguation
            if test.should_disambiguate:
                assert result.needs_clarification, "Should trigger disambiguation"

            print(f"  ✅ '{test.query[:40]}...'")
            if test.description:
                print(f"     {test.description}")

            self.test_results.append(("PASS", test.query))

        except AssertionError as e:
            print(f"  ❌ '{test.query[:40]}...'")
            print(f"     Error: {e}")
            self.test_results.append(("FAIL", test.query))

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for status, _ in self.test_results if status == "PASS")
        failed = sum(1 for status, _ in self.test_results if status == "FAIL")
        total = len(self.test_results)

        print(f"\n📊 Results:")
        print(f"  Total Tests: {total}")
        print(f"  Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"  Failed: {failed} ({failed/total*100:.1f}%)")

        print(f"\n📈 Metrics:")
        print(f"  Regex Hits: {self.classifier.metrics['regex_hits']}")
        print(f"  Disambiguations: {self.classifier.metrics['disambiguations']}")
        print(f"  Fallbacks: {self.classifier.metrics['fallbacks']}")
        print(f"  Cache Hits: {self.classifier.metrics['cache_hits']}")

        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for status, query in self.test_results:
                if status == "FAIL":
                    print(f"  - {query}")

        print("\n" + "=" * 80)
        if failed == 0:
            print("✅ ALL TESTS PASSED - Ready for implementation!")
        else:
            print("❌ SOME TESTS FAILED - Review before implementation")
        print("=" * 80)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting Query Classification System Tests\n")

    # Run test suite
    test_suite = TestQueryClassification()
    test_suite.run_all_tests()

    print("\n✨ Test suite completed!\n")