"""
Production Query Classification System
Phase 1: Regex patterns, disambiguation, and deterministic processing
"""

import re
import logging
import time
from typing import Dict, Tuple, Optional, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result from query classification"""
    intent: str
    confidence: float
    method: str
    needs_clarification: bool = False
    disambiguation_options: List[Dict] = None
    data_preparation: str = "full"
    token_limit: int = 15000
    use_deterministic: bool = False
    metadata: Dict = None

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class QueryClassifier:
    """
    Hybrid query classifier with multiple layers:
    1. Cache
    2. Regex exact matching
    3. Disambiguation for ambiguous queries
    4. Keyword fallback
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize classifier with configuration

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

        # Initialize patterns
        self._init_regex_patterns()
        self._init_ambiguous_patterns()
        self._init_intent_configs()

        # Simple in-memory cache (replace with Redis in production)
        self.cache = {}
        self.cache_ttl = self.config.get("cache_ttl", 300)  # 5 minutes default

        # Metrics tracking
        self.metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "regex_hits": 0,
            "disambiguations": 0,
            "keyword_fallbacks": 0,
            "unknown_queries": 0
        }

        # Confidence thresholds
        self.thresholds = {
            "accept_immediately": 0.85,
            "disambiguation": 0.60,
            "fallback": 0.60
        }

    def _init_regex_patterns(self):
        """Initialize regex patterns for exact matching"""
        self.regex_patterns = {
            "active_products": [
                r"^how many active products",
                r"^count.*active products",
                r"^active products count",
                r"^what('s| is) the (number|count) of active products",
                r"^show.*active products.*count",
                r"^list.*active products",
                r"products.*with.*active.*status",
                r"products.*marked.*active"
            ],
            "products_in_stock": [
                r"^products.*in stock",
                r"^show.*in stock",
                r"^available inventory",
                r"^items with quantity",
                r"^products with stock",
                r"products.*available.*warehouse",
                r"what.*have.*stock",
                r"(?<!active )products.*in stock"  # Exclude "active products in stock"
            ],
            "total_products": [
                r"^total products",
                r"^how many products(?!.*active)(?!.*stock)",
                r"^all products count",
                r"^what('s| is) the total.*products",
                r"^complete.*catalog.*size",
                r"^entire.*inventory.*count"
            ],
            "sales_analysis": [
                r"sales.*last month",
                r"revenue.*this week",
                r"earnings.*today",
                r"sales report",
                r"total sales",
                r"how much.*earn",
                r"sales.*performance"
            ],
            "order_tracking": [
                r"orders.*today",
                r"pending orders",
                r"recent orders",
                r"new orders",
                r"order.*status",
                r"unfulfilled.*orders"
            ]
        }

    def _init_ambiguous_patterns(self):
        """Initialize patterns that trigger disambiguation"""
        self.ambiguous_patterns = [
            # (trigger words, possible intents, clarification question)
            (
                ["active", "stock"],
                ["active_products", "products_in_stock"],
                "Are you asking about products with active status or products with available inventory?"
            ),
            (
                ["active", "inventory"],
                ["active_products", "products_in_stock"],
                "Do you mean products marked as active or products in your inventory?"
            ),
            (
                ["available", "products"],
                ["active_products", "products_in_stock"],
                "Are you looking for active products or products with stock available?"
            ),
            (
                ["live", "items"],
                ["active_products", "total_products"],
                "Do you want active/live products or all products?"
            )
        ]

    def _init_intent_configs(self):
        """Initialize intent configurations"""
        self.intent_configs = {
            "active_products": {
                "description": "Products with status='active'",
                "data_preparation": "minimal",
                "token_limit": 2000,
                "use_deterministic": True,
                "deterministic_query": {"status": "active"},
                "response_template": "You have {count} active products."
            },
            "products_in_stock": {
                "description": "Products with inventory > 0",
                "data_preparation": "moderate",
                "token_limit": 10000,
                "use_deterministic": True,
                "deterministic_query": {"inventory": {"$gt": 0}},
                "response_template": "You have {count} products in stock."
            },
            "total_products": {
                "description": "All products count",
                "data_preparation": "minimal",
                "token_limit": 5000,
                "use_deterministic": True,
                "deterministic_query": {},
                "response_template": "You have {count} total products."
            },
            "sales_analysis": {
                "description": "Sales and revenue analysis",
                "data_preparation": "full",
                "token_limit": 25000,
                "use_deterministic": False
            },
            "order_tracking": {
                "description": "Order management queries",
                "data_preparation": "full",
                "token_limit": 20000,
                "use_deterministic": False
            }
        }

    def classify(self, query: str, context: Optional[Dict] = None) -> ClassificationResult:
        """
        Classify query through multiple layers

        Args:
            query: User query
            context: Optional context (shop_id, user_id, etc.)

        Returns:
            ClassificationResult with intent and confidence
        """
        start_time = time.time()
        self.metrics["total_queries"] += 1

        # Normalize query
        query_normalized = query.lower().strip()

        # Layer 1: Check cache
        cache_key = f"{query_normalized}:{context.get('shop_id') if context else 'default'}"
        cached = self._check_cache(cache_key)
        if cached:
            self.metrics["cache_hits"] += 1
            logger.debug(f"Cache hit for query: {query[:50]}")
            return cached

        # Layer 2: Regex exact matching
        regex_result = self._classify_by_regex(query_normalized)
        if regex_result:
            self.metrics["regex_hits"] += 1
            intent, pattern = regex_result
            result = self._create_result(
                intent=intent,
                confidence=0.95,
                method="regex",
                metadata={"pattern": pattern, "latency_ms": (time.time() - start_time) * 1000}
            )
            self._cache_result(cache_key, result)
            logger.info(f"Regex match: '{query[:50]}' -> {intent}")
            return result

        # Layer 3: Check for ambiguous patterns
        ambiguous_result = self._check_ambiguous(query_normalized)
        if ambiguous_result:
            self.metrics["disambiguations"] += 1
            logger.info(f"Disambiguation needed for: '{query[:50]}'")
            return ambiguous_result

        # Layer 4: Keyword fallback
        keyword_result = self._classify_by_keywords(query_normalized)
        if keyword_result:
            self.metrics["keyword_fallbacks"] += 1
            result = self._create_result(
                intent=keyword_result,
                confidence=0.60,
                method="keyword",
                metadata={"latency_ms": (time.time() - start_time) * 1000}
            )
            self._cache_result(cache_key, result)
            logger.info(f"Keyword match: '{query[:50]}' -> {keyword_result}")
            return result

        # No match found
        self.metrics["unknown_queries"] += 1
        logger.warning(f"Unknown query: '{query[:50]}'")
        return ClassificationResult(
            intent="unknown",
            confidence=0.0,
            method="none",
            metadata={"query": query, "latency_ms": (time.time() - start_time) * 1000}
        )

    def _check_cache(self, key: str) -> Optional[ClassificationResult]:
        """Check if result is in cache"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.cache_ttl:
                return entry["result"]
            else:
                del self.cache[key]  # Remove expired entry
        return None

    def _cache_result(self, key: str, result: ClassificationResult):
        """Cache classification result"""
        self.cache[key] = {
            "result": result,
            "timestamp": time.time()
        }

    def _classify_by_regex(self, query: str) -> Optional[Tuple[str, str]]:
        """Classify using regex patterns"""
        for intent, patterns in self.regex_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return (intent, pattern)
        return None

    def _check_ambiguous(self, query: str) -> Optional[ClassificationResult]:
        """Check if query is ambiguous and needs clarification"""
        for trigger_words, intents, question in self.ambiguous_patterns:
            if all(word in query for word in trigger_words):
                # Create disambiguation options
                options = []
                for intent in intents:
                    config = self.intent_configs.get(intent, {})
                    options.append({
                        "intent": intent,
                        "description": config.get("description", intent)
                    })

                return ClassificationResult(
                    intent="ambiguous",
                    confidence=0.65,
                    method="disambiguation",
                    needs_clarification=True,
                    disambiguation_options=options,
                    metadata={
                        "question": question,
                        "trigger_words": trigger_words
                    }
                )
        return None

    def _classify_by_keywords(self, query: str) -> Optional[str]:
        """Simple keyword-based classification"""
        # Define keyword mappings
        keyword_map = {
            "active_products": (["active", "products"], ["inactive", "stock"]),
            "products_in_stock": (["stock", "inventory", "available"], ["active"]),
            "total_products": (["total", "all", "products"], ["active", "stock"]),
            "sales_analysis": (["sales", "revenue", "earnings"], []),
            "order_tracking": (["order", "orders"], [])
        }

        best_match = None
        best_score = 0

        for intent, (required, excluded) in keyword_map.items():
            # Check if required words are present
            matches = sum(1 for word in required if word in query)
            # Check if excluded words are absent
            excludes = sum(1 for word in excluded if word in query)

            if matches > best_score and excludes == 0:
                best_score = matches
                best_match = intent

        if best_score >= 2:  # At least 2 keyword matches
            return best_match

        return None

    def _create_result(self, intent: str, confidence: float, method: str, **kwargs) -> ClassificationResult:
        """Create classification result with intent configuration"""
        config = self.intent_configs.get(intent, {})

        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            method=method,
            data_preparation=config.get("data_preparation", "full"),
            token_limit=config.get("token_limit", 15000),
            use_deterministic=config.get("use_deterministic", False),
            metadata=kwargs.get("metadata", {})
        )

    def get_deterministic_config(self, intent: str) -> Optional[Dict]:
        """Get deterministic processing configuration for an intent"""
        if intent in self.intent_configs:
            config = self.intent_configs[intent]
            if config.get("use_deterministic"):
                return {
                    "query": config.get("deterministic_query"),
                    "template": config.get("response_template")
                }
        return None

    def should_accept_immediately(self, confidence: float) -> bool:
        """Check if confidence is high enough to accept immediately"""
        return confidence >= self.thresholds["accept_immediately"]

    def should_disambiguate(self, confidence: float) -> bool:
        """Check if disambiguation is needed"""
        return self.thresholds["disambiguation"] <= confidence < self.thresholds["accept_immediately"]

    def get_metrics(self) -> Dict:
        """Get classification metrics"""
        total = self.metrics["total_queries"] or 1  # Avoid division by zero
        return {
            **self.metrics,
            "cache_hit_rate": self.metrics["cache_hits"] / total,
            "regex_hit_rate": self.metrics["regex_hits"] / total,
            "disambiguation_rate": self.metrics["disambiguations"] / total,
            "unknown_rate": self.metrics["unknown_queries"] / total
        }

    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        logger.info("Classification cache cleared")

    def add_pattern(self, intent: str, pattern: str):
        """Add a new regex pattern for an intent"""
        if intent not in self.regex_patterns:
            self.regex_patterns[intent] = []
        self.regex_patterns[intent].append(pattern)
        logger.info(f"Added pattern for {intent}: {pattern}")