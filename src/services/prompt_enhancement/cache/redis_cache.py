"""
Cache implementations for prompt enhancement results.
"""

import json
import hashlib
import logging
import time
from typing import Optional, Dict, Any

from ..interfaces import IEnhancementCache
from ..models import EnhancementResult, EnhancementMethod

logger = logging.getLogger(__name__)


# Redis cache removed - using only in-memory cache


class InMemoryEnhancementCache(IEnhancementCache):
    """
    In-memory cache implementation for development/testing.
    Not recommended for production use.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_cache_key(self, query: str, context_hash: Optional[str] = None) -> str:
        """Generate cache key"""
        normalized_query = query.lower().strip()
        if context_hash:
            return f"{normalized_query}:{context_hash}"
        return normalized_query

    async def get(self, query: str, context_hash: Optional[str] = None) -> Optional[EnhancementResult]:
        """Retrieve cached result"""
        cache_key = self._generate_cache_key(query, context_hash)

        if cache_key in self._cache:
            data = self._cache[cache_key]

            # Check expiration
            import time
            if time.time() > data["expires_at"]:
                del self._cache[cache_key]
                return None

            # Return cached result
            cached_result = data["result"]
            cached_result.method = EnhancementMethod.CACHED
            cached_result.processing_time_ms = 0.1

            return cached_result

        return None

    async def set(
        self,
        query: str,
        result: EnhancementResult,
        context_hash: Optional[str] = None,
        ttl: Optional[int] = None
    ):
        """Store result in cache"""
        if not result.was_enhanced:
            return

        cache_key = self._generate_cache_key(query, context_hash)

        # Evict oldest entries if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        import time
        ttl_seconds = ttl or self.default_ttl
        expires_at = time.time() + ttl_seconds

        self._cache[cache_key] = {
            "result": result,
            "expires_at": expires_at
        }

    async def clear(self, pattern: Optional[str] = None):
        """Clear cache entries"""
        if pattern:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
        else:
            self._cache.clear()