"""
Deterministic Query Processor
Handles factual queries with direct database lookups
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DeterministicProcessor:
    """
    Process factual queries deterministically using direct database queries
    This ensures 100% accuracy for counts and factual data
    """

    def __init__(self, mongodb_client=None):
        """
        Initialize with database connection

        Args:
            mongodb_client: MongoDB client instance
        """
        self.mongodb_client = mongodb_client

        # Define deterministic query templates
        self.query_templates = {
            "active_products": {
                "collection": "product",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id),
                    "status": "active"
                },
                "response_template": "You have {count} active products.",
                "empty_response": "You don't have any active products."
            },
            "products_in_stock": {
                "collection": "warehouse",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id),
                    "available_quantity": {"$gt": 0}
                },
                "response_template": "You have {count} products in stock.",
                "empty_response": "You don't have any products in stock."
            },
            "total_products": {
                "collection": "product",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id)
                },
                "response_template": "You have {count} total products.",
                "empty_response": "You don't have any products in your store."
            },
            "inactive_products": {
                "collection": "product",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id),
                    "status": "inactive"
                },
                "response_template": "You have {count} inactive products.",
                "empty_response": "You don't have any inactive products."
            },
            "draft_products": {
                "collection": "product",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id),
                    "status": "draft"
                },
                "response_template": "You have {count} draft products.",
                "empty_response": "You don't have any draft products."
            },
            "low_stock_products": {
                "collection": "warehouse",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id),
                    "available_quantity": {"$gt": 0, "$lte": 10}
                },
                "response_template": "You have {count} products with low stock (≤10 units).",
                "empty_response": "No products are currently low on stock."
            },
            "out_of_stock_products": {
                "collection": "warehouse",
                "filter": lambda shop_id: {
                    "shop_id": int(shop_id),
                    "available_quantity": {"$eq": 0}
                },
                "response_template": "You have {count} products out of stock.",
                "empty_response": "All products have stock available."
            }
        }

        # Track metrics
        self.metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "cache_hits": 0
        }

        # Simple cache for recent counts (TTL: 60 seconds)
        self.count_cache = {}
        self.cache_ttl = 60

    def can_process(self, intent: str) -> bool:
        """
        Check if intent can be processed deterministically

        Args:
            intent: The classified intent

        Returns:
            True if intent can be processed deterministically
        """
        return intent in self.query_templates

    async def process(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process query deterministically

        Args:
            intent: The classified intent
            context: Query context (must include shop_id)

        Returns:
            Response dictionary with answer and metadata
        """
        self.metrics["total_processed"] += 1

        try:
            # Validate context
            shop_id = context.get("shop_id")
            if not shop_id:
                raise ValueError("shop_id is required for deterministic processing")

            # Check if intent is supported
            if not self.can_process(intent):
                raise ValueError(f"Intent '{intent}' cannot be processed deterministically")

            # Get template
            template = self.query_templates[intent]

            # Check cache
            cache_key = f"{intent}:{shop_id}"
            cached_count = self._get_cached_count(cache_key)
            if cached_count is not None:
                self.metrics["cache_hits"] += 1
                count = cached_count
                logger.debug(f"Cache hit for {intent}: {count}")
            else:
                # Execute database query
                count = await self._execute_count_query(
                    collection=template["collection"],
                    filter_query=template["filter"](shop_id)
                )
                self._cache_count(cache_key, count)

            # Format response
            if count > 0:
                response = template["response_template"].format(count=count)
            else:
                response = template["empty_response"]

            self.metrics["successful"] += 1

            return {
                "success": True,
                "response": response,
                "data": {
                    "count": count,
                    "intent": intent,
                    "shop_id": shop_id
                },
                "metadata": {
                    "method": "deterministic",
                    "cached": cached_count is not None,
                    "query_time_ms": 0 if cached_count is not None else 50  # Approximate
                }
            }

        except Exception as e:
            self.metrics["failed"] += 1
            logger.error(f"Deterministic processing failed for {intent}: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": self._get_fallback_response(intent)
            }

    async def _execute_count_query(self, collection: str, filter_query: Dict) -> int:
        """
        Execute count query on database

        Args:
            collection: Collection name
            filter_query: MongoDB filter query

        Returns:
            Count of matching documents
        """
        if not self.mongodb_client or not self.mongodb_client.is_connected:
            raise ConnectionError("Database not connected")

        db = self.mongodb_client.database
        count = await db[collection].count_documents(filter_query)
        logger.debug(f"Count query on {collection}: {filter_query} -> {count}")
        return count

    def _get_cached_count(self, key: str) -> Optional[int]:
        """Get cached count if available and not expired"""
        if key in self.count_cache:
            entry = self.count_cache[key]
            if (datetime.now() - entry["timestamp"]).seconds < self.cache_ttl:
                return entry["count"]
            else:
                del self.count_cache[key]
        return None

    def _cache_count(self, key: str, count: int):
        """Cache count result"""
        self.count_cache[key] = {
            "count": count,
            "timestamp": datetime.now()
        }

    def _get_fallback_response(self, intent: str) -> str:
        """Get fallback response for failed queries"""
        fallback_responses = {
            "active_products": "I couldn't retrieve the active products count. Please try again.",
            "products_in_stock": "I couldn't check the inventory. Please try again.",
            "total_products": "I couldn't count the total products. Please try again.",
            "default": "I couldn't process your query. Please try again."
        }
        return fallback_responses.get(intent, fallback_responses["default"])

    async def get_product_statistics(self, shop_id: str) -> Dict[str, int]:
        """
        Get comprehensive product statistics

        Args:
            shop_id: Shop identifier

        Returns:
            Dictionary with various product counts
        """
        stats = {}

        # Define all statistics to gather
        stat_queries = [
            ("total_products", "product", {"shop_id": int(shop_id)}),
            ("active_products", "product", {"shop_id": int(shop_id), "status": "active"}),
            ("inactive_products", "product", {"shop_id": int(shop_id), "status": "inactive"}),
            ("draft_products", "product", {"shop_id": int(shop_id), "status": "draft"}),
            ("products_in_stock", "warehouse", {"shop_id": int(shop_id), "available_quantity": {"$gt": 0}}),
            ("out_of_stock", "warehouse", {"shop_id": int(shop_id), "available_quantity": {"$eq": 0}}),
            ("low_stock", "warehouse", {"shop_id": int(shop_id), "available_quantity": {"$gt": 0, "$lte": 10}})
        ]

        for stat_name, collection, filter_query in stat_queries:
            try:
                count = await self._execute_count_query(collection, filter_query)
                stats[stat_name] = count
            except Exception as e:
                logger.error(f"Failed to get {stat_name}: {e}")
                stats[stat_name] = -1  # Indicate error

        return stats

    def get_metrics(self) -> Dict:
        """Get processing metrics"""
        total = self.metrics["total_processed"] or 1
        return {
            **self.metrics,
            "success_rate": self.metrics["successful"] / total,
            "cache_hit_rate": self.metrics["cache_hits"] / total
        }

    def clear_cache(self):
        """Clear the count cache"""
        self.count_cache.clear()
        logger.info("Deterministic processor cache cleared")