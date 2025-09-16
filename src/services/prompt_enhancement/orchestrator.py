"""
Main orchestrator for prompt enhancement system.
Coordinates all components and provides the main enhancement interface.
"""

import time
import logging
from typing import Optional, Dict, Any, List

from .interfaces import (
    IEnhancementOrchestrator,
    IPromptEnhancer,
    IQueryAnalyzer,
    IEnhancementCache,
    IMetricsCollector
)
from .models import (
    EnhancementRequest,
    EnhancementResult,
    EnhancementContext,
    EnhancementMethod,
    EnhancementMetrics
)

logger = logging.getLogger(__name__)


class EnhancementOrchestrator(IEnhancementOrchestrator):
    """
    Main orchestrator for the prompt enhancement system.
    Coordinates caching, analysis, enhancement, and metrics collection.
    """

    def __init__(
        self,
        enhancer: IPromptEnhancer,
        analyzer: IQueryAnalyzer,
        cache: Optional[IEnhancementCache] = None,
        metrics_collector: Optional[IMetricsCollector] = None
    ):
        """
        Initialize orchestrator.

        Args:
            enhancer: Primary prompt enhancer
            analyzer: Query analyzer
            cache: Optional cache for results
            metrics_collector: Optional metrics collector
        """
        self.enhancer = enhancer
        self.analyzer = analyzer
        self.cache = cache
        self.metrics_collector = metrics_collector

        # Performance thresholds
        self.min_confidence_threshold = 0.3  # Lower threshold
        self.max_processing_time_ms = 10000  # 10 seconds max for AI enhancement

    async def enhance_query(self, request: EnhancementRequest) -> EnhancementResult:
        """
        Main enhancement orchestration with full pipeline.

        Args:
            request: Enhancement request

        Returns:
            EnhancementResult: Final enhancement result
        """
        start_time = time.time()

        try:
            # Step 1: Check cache first
            if self.cache:
                context_hash = self._generate_context_hash(request.context)
                cached_result = await self.cache.get(request.query, context_hash)

                if cached_result:
                    logger.debug(f"Cache hit for query: {request.query[:50]}...")

                    # Record metrics
                    if self.metrics_collector:
                        await self.metrics_collector.record_enhancement(cached_result)

                    return cached_result

            # Step 2: Perform enhancement
            result = await self._perform_enhancement(request)

            # Step 3: Cache successful results
            if self.cache and result.was_enhanced and result.confidence >= self.min_confidence_threshold:
                context_hash = self._generate_context_hash(request.context)
                await self.cache.set(request.query, result, context_hash)

            # Step 4: Record metrics
            if self.metrics_collector:
                await self.metrics_collector.record_enhancement(result)

            return result

        except Exception as e:
            logger.error(f"Enhancement orchestration failed: {e}")

            # Create fallback result
            processing_time = (time.time() - start_time) * 1000
            fallback_result = EnhancementResult(
                original_query=request.query,
                enhanced_query=request.query,
                method=EnhancementMethod.FALLBACK,
                confidence=0.0,
                processing_time_ms=processing_time,
                context=request.context,
                metadata={"error": str(e)}
            )

            # Record failed attempt
            if self.metrics_collector:
                await self.metrics_collector.record_enhancement(fallback_result)

            return fallback_result

    async def get_enhancement_preview(
        self,
        query: str,
        context: Optional[EnhancementContext] = None
    ) -> EnhancementResult:
        """
        Get enhancement preview without caching.

        Args:
            query: Query to enhance
            context: Optional context

        Returns:
            EnhancementResult: Enhancement preview
        """
        request = EnhancementRequest(query=query, context=context)

        # Perform enhancement without caching
        return await self._perform_enhancement(request)

    async def _perform_enhancement(self, request: EnhancementRequest) -> EnhancementResult:
        """
        Perform the actual enhancement process.

        Args:
            request: Enhancement request

        Returns:
            EnhancementResult: Enhancement result
        """
        # Check if enhancement is needed
        if not self._should_enhance(request):
            return EnhancementResult(
                original_query=request.query,
                enhanced_query=request.query,
                method=EnhancementMethod.FALLBACK,
                confidence=1.0,  # High confidence in no change needed
                processing_time_ms=0.1,
                context=request.context,
                metadata={"reason": "enhancement_not_needed"}
            )

        # Check enhancer availability
        if not self.enhancer.is_available():
            logger.warning("Primary enhancer not available, returning original query")
            return EnhancementResult(
                original_query=request.query,
                enhanced_query=request.query,
                method=EnhancementMethod.FALLBACK,
                confidence=0.0,
                processing_time_ms=0.1,
                context=request.context,
                metadata={"reason": "enhancer_unavailable"}
            )

        # Perform enhancement
        result = await self.enhancer.enhance(request)

        # Validate result
        result = await self._validate_result(result, request)

        return result

    def _should_enhance(self, request: EnhancementRequest) -> bool:
        """
        Determine if query should be enhanced.

        Args:
            request: Enhancement request

        Returns:
            bool: True if enhancement should be performed
        """
        # Always enhance if forced
        if request.force_enhancement:
            return True

        query = request.query.strip()

        # Don't enhance empty queries
        if not query:
            return False

        # Don't enhance very long, detailed queries (likely already good)
        if len(query.split()) > 15:
            return False

        # Don't enhance queries that are already very detailed and well-formed
        well_formed_indicators = [
            "provide detailed",
            "show me comprehensive",
            "analyze the detailed",
            "give me a detailed report",
            "display comprehensive analytics",
            "provide complete analysis"
        ]

        query_lower = query.lower()
        if any(indicator in query_lower for indicator in well_formed_indicators):
            return False

        # Always enhance short queries (they need more context)
        if len(query.split()) <= 3:
            return True

        return True

    async def _validate_result(
        self,
        result: EnhancementResult,
        request: EnhancementRequest
    ) -> EnhancementResult:
        """
        Validate enhancement result and apply quality checks.

        Args:
            result: Enhancement result
            request: Original request

        Returns:
            EnhancementResult: Validated result
        """
        # Check processing time
        if result.processing_time_ms > self.max_processing_time_ms:
            logger.warning(f"Enhancement took too long: {result.processing_time_ms}ms")
            result.metadata["performance_warning"] = "slow_processing"

        # Check enhancement quality
        if result.was_enhanced:
            # Check for reasonable length increase (very generous for short queries)
            length_ratio = len(result.enhanced_query) / len(result.original_query)
            max_ratio = 15.0 if len(result.original_query.split()) <= 2 else 8.0  # Allow more expansion for very short queries

            if length_ratio > max_ratio:  # Too much expansion
                logger.warning(f"Enhancement too verbose, ratio: {length_ratio}")
                result.metadata["length_ratio"] = length_ratio
                result.metadata["warning"] = "verbose_but_accepted"
                # Don't reject, just warn

            # Check confidence threshold
            if result.confidence < self.min_confidence_threshold:
                logger.warning(f"Enhancement confidence too low: {result.confidence}")
                result.metadata["confidence_warning"] = "below_threshold"

        return result

    def _generate_context_hash(self, context: Optional[EnhancementContext]) -> Optional[str]:
        """
        Generate hash for context.

        Args:
            context: Enhancement context

        Returns:
            Optional[str]: Context hash
        """
        if not context:
            return None

        import hashlib
        import json

        context_dict = context.to_dict()
        context_str = json.dumps(context_dict, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of enhancement system.

        Returns:
            Dict[str, Any]: Health status of all components
        """
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {}
        }

        # Check enhancer
        try:
            enhancer_available = self.enhancer.is_available()
            health_status["components"]["enhancer"] = {
                "status": "healthy" if enhancer_available else "unavailable",
                "name": self.enhancer.get_name(),
                "available": enhancer_available
            }

            if not enhancer_available:
                health_status["status"] = "degraded"

        except Exception as e:
            health_status["components"]["enhancer"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"

        # Check cache
        if self.cache:
            try:
                # Try a simple cache operation
                test_result = await self.cache.get("health_check_test")
                health_status["components"]["cache"] = {
                    "status": "healthy",
                    "type": type(self.cache).__name__
                }
            except Exception as e:
                health_status["components"]["cache"] = {
                    "status": "error",
                    "error": str(e)
                }
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
        else:
            health_status["components"]["cache"] = {
                "status": "disabled"
            }

        # Check metrics collector
        if self.metrics_collector:
            try:
                metrics = await self.metrics_collector.get_metrics()
                health_status["components"]["metrics"] = {
                    "status": "healthy",
                    "total_requests": metrics.total_requests
                }
            except Exception as e:
                health_status["components"]["metrics"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["components"]["metrics"] = {
                "status": "disabled"
            }

        return health_status


class SimpleMetricsCollector(IMetricsCollector):
    """
    Simple in-memory metrics collector.
    """

    def __init__(self):
        """Initialize metrics collector"""
        self.metrics = EnhancementMetrics()

    async def record_enhancement(self, result: EnhancementResult):
        """Record enhancement result"""
        self.metrics.update(result)

    async def get_metrics(self) -> EnhancementMetrics:
        """Get current metrics"""
        return self.metrics

    async def reset_metrics(self):
        """Reset metrics"""
        self.metrics = EnhancementMetrics()