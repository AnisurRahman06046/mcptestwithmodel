"""
Factory for creating prompt enhancement components.
Implements dependency injection and configuration.
"""

import logging
from typing import Optional, Dict, Any

from .interfaces import (
    IEnhancementFactory,
    IQueryAnalyzer,
    IPromptEnhancer,
    IEnhancementValidator,
    IEnhancementCache,
    IMetricsCollector,
    IEnhancementOrchestrator,
    IModelManager
)

from .analyzers.query_analyzer import IntelligentQueryAnalyzer, FastIntentPredictor
from .enhancers.ai_enhancer import AIPromptEnhancer
from .cache.redis_cache import InMemoryEnhancementCache
from .orchestrator import EnhancementOrchestrator, SimpleMetricsCollector

logger = logging.getLogger(__name__)


class ModelManagerAdapter(IModelManager):
    """
    Adapter to integrate existing model manager with enhancement system.
    """

    def __init__(self, model_manager):
        """
        Initialize adapter.

        Args:
            model_manager: Existing model manager instance
        """
        self.model_manager = model_manager

    async def inference(self, prompt: str, max_tokens: int = 50, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Run model inference using dedicated enhancement model.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature

        Returns:
            Dict[str, Any]: Inference result
        """
        try:
            # Use dedicated enhancement model (load once, use for all enhancements)
            optimal_model = self._get_dedicated_enhancement_model()

            # Load enhancement model only if not already loaded
            if self.model_manager.active_model != optimal_model:
                logger.info(f"Loading dedicated enhancement model: {optimal_model}")
                success = self.model_manager.load_model(optimal_model)
                if not success:
                    raise RuntimeError(f"Failed to load enhancement model: {optimal_model}")

            # Use existing model manager
            result = self.model_manager.inference(prompt, max_tokens, temperature)

            # Ensure consistent return format
            if isinstance(result, dict):
                return result
            else:
                return {
                    "text": str(result),
                    "token_usage": {"total_tokens": max_tokens},
                    "processing_time": 0
                }

        except Exception as e:
            logger.error(f"Model inference failed: {e}")
            raise

    def _get_dedicated_enhancement_model(self) -> str:
        """
        Get the single, dedicated model for all enhancements.

        Returns:
            str: Dedicated enhancement model name
        """
        # Priority order: balanced performance for all enhancement tasks
        preferred_models = [
            "qwen2.5-1.5b",  # Best balance of speed (3-4s) and accuracy (90%+)
            "qwen2.5-0.5b",  # Ultra-fast (1-2s) but slightly lower accuracy (85%+)
            "qwen2.5-3b",    # High accuracy (95%+) but slower (7-8s)
            "phi-3-mini"     # Fallback if Qwen models unavailable
        ]

        # Return first available model
        for model_name in preferred_models:
            model_stats = self.model_manager.model_stats.get(model_name, {})
            if model_stats.get("file_exists", False):
                return model_name

        # Ultimate fallback
        return "qwen2.5-1.5b"

    # Removed complex routing logic - using single dedicated model approach

    def is_available(self) -> bool:
        """Check if model is available"""
        try:
            # Auto-load a model if none is active
            if not self.model_manager.active_model:
                # Try to load the fastest available model for enhancement
                available_models = ['qwen2.5-1.5b', 'qwen2.5-3b', 'phi-3-mini']
                for model_name in available_models:
                    if self.model_manager.load_model(model_name):
                        logger.info(f"Auto-loaded {model_name} for enhancement")
                        break

            return hasattr(self.model_manager, 'active_model') and self.model_manager.active_model is not None
        except Exception as e:
            logger.error(f"Model availability check failed: {e}")
            return False


class EnhancementFactory(IEnhancementFactory):
    """
    Factory for creating enhancement system components.
    Handles dependency injection and configuration.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize factory with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._model_manager = None
        self._analyzer = None
        self._enhancer = None
        self._cache = None
        self._metrics_collector = None

    def configure_model_manager(self, model_manager) -> 'EnhancementFactory':
        """
        Configure model manager for the factory.

        Args:
            model_manager: Model manager instance

        Returns:
            EnhancementFactory: Self for method chaining
        """
        self._model_manager = ModelManagerAdapter(model_manager)
        return self

    def create_analyzer(self) -> IQueryAnalyzer:
        """Create query analyzer instance"""
        if self._analyzer is None:
            # Create intent predictor
            intent_predictor = FastIntentPredictor()

            # Create analyzer
            self._analyzer = IntelligentQueryAnalyzer(intent_predictor)

        return self._analyzer

    def create_enhancer(self, enhancer_type: str = "ai_dynamic") -> IPromptEnhancer:
        """Create prompt enhancer instance"""
        if self._enhancer is None:
            if enhancer_type != "ai_dynamic":
                raise ValueError(f"Unsupported enhancer type: {enhancer_type}")

            if not self._model_manager:
                raise ValueError("Model manager must be configured before creating enhancer")

            # Create analyzer if not exists
            analyzer = self.create_analyzer()

            # Create AI enhancer
            self._enhancer = AIPromptEnhancer(self._model_manager, analyzer)

        return self._enhancer

    def create_validator(self) -> IEnhancementValidator:
        """Create enhancement validator instance"""
        # Simple validator for now
        class SimpleValidator(IEnhancementValidator):
            async def validate(self, original: str, enhanced: str, context=None) -> float:
                if enhanced == original:
                    return 0.0
                length_ratio = len(enhanced) / len(original) if original else 1
                return 0.8 if 1.2 <= length_ratio <= 3.0 else 0.5

        return SimpleValidator()

    def create_cache(self) -> IEnhancementCache:
        """Create enhancement cache instance"""
        if self._cache is None:
            cache_config = self.config.get("cache", {})
            max_size = cache_config.get("max_size", 1000)
            ttl = cache_config.get("ttl", 3600)

            self._cache = InMemoryEnhancementCache(max_size=max_size, default_ttl=ttl)
            logger.info("Using in-memory cache for enhancements")

        return self._cache

    def create_metrics_collector(self) -> IMetricsCollector:
        """Create metrics collector instance"""
        if self._metrics_collector is None:
            self._metrics_collector = SimpleMetricsCollector()

        return self._metrics_collector

    def create_orchestrator(self) -> IEnhancementOrchestrator:
        """Create enhancement orchestrator instance"""
        # Create all dependencies
        enhancer = self.create_enhancer()
        analyzer = self.create_analyzer()
        cache = self.create_cache()
        metrics_collector = self.create_metrics_collector()

        # Create orchestrator
        return EnhancementOrchestrator(
            enhancer=enhancer,
            analyzer=analyzer,
            cache=cache,
            metrics_collector=metrics_collector
        )


class EnhancementService:
    """
    High-level service for prompt enhancement.
    Provides simple interface for integration.
    """

    def __init__(self, model_manager, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhancement service.

        Args:
            model_manager: Model manager instance
            config: Optional configuration
        """
        self.config = config or {}

        # Create factory and configure
        factory = EnhancementFactory(config)
        factory.configure_model_manager(model_manager)

        # Create main orchestrator
        self.orchestrator = factory.create_orchestrator()

        logger.info("Enhancement service initialized successfully")

    async def enhance_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        force_enhancement: bool = False
    ) -> Dict[str, Any]:
        """
        Enhance a user query.

        Args:
            query: User query to enhance
            context: Optional context information
            force_enhancement: Force enhancement even if not needed

        Returns:
            Dict[str, Any]: Enhancement result
        """
        from .models import EnhancementRequest, EnhancementContext

        # Create context object
        enhancement_context = None
        if context:
            enhancement_context = EnhancementContext(
                user_id=context.get("user_id"),
                shop_id=context.get("shop_id"),
                business_domain=context.get("business_domain", "ecommerce")
            )

        # Create request
        request = EnhancementRequest(
            query=query,
            context=enhancement_context,
            force_enhancement=force_enhancement
        )

        # Perform enhancement
        result = await self.orchestrator.enhance_query(request)

        # Return as dictionary for API response
        return result.to_dict()

    async def get_enhancement_preview(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get enhancement preview without caching.

        Args:
            query: Query to enhance
            context: Optional context

        Returns:
            Dict[str, Any]: Enhancement preview
        """
        from .models import EnhancementContext

        # Create context object
        enhancement_context = None
        if context:
            enhancement_context = EnhancementContext(
                user_id=context.get("user_id"),
                shop_id=context.get("shop_id"),
                business_domain=context.get("business_domain", "ecommerce")
            )

        # Get preview
        result = await self.orchestrator.get_enhancement_preview(query, enhancement_context)

        return result.to_dict()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of enhancement system"""
        return await self.orchestrator.health_check()

    async def get_metrics(self) -> Dict[str, Any]:
        """Get enhancement metrics"""
        metrics = await self.orchestrator.metrics_collector.get_metrics()
        return {
            "total_requests": metrics.total_requests,
            "successful_enhancements": metrics.successful_enhancements,
            "cache_hits": metrics.cache_hits,
            "success_rate": metrics.success_rate,
            "cache_hit_rate": metrics.cache_hit_rate,
            "average_processing_time": metrics.average_processing_time,
            "average_confidence": metrics.average_confidence
        }