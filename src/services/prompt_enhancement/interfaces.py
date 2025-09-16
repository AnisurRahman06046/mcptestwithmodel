"""
Core interfaces for prompt enhancement system.
Defines contracts for all enhancement components.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio

from .models import (
    EnhancementRequest,
    EnhancementResult,
    QueryAnalysis,
    EnhancementContext,
    EnhancementMetrics
)


class IQueryAnalyzer(ABC):
    """Interface for analyzing user queries"""

    @abstractmethod
    async def analyze(self, query: str, context: Optional[EnhancementContext] = None) -> QueryAnalysis:
        """
        Analyze query complexity and characteristics.

        Args:
            query: User query to analyze
            context: Optional context information

        Returns:
            QueryAnalysis: Analysis result with complexity and recommendations
        """
        pass


class IPromptEnhancer(ABC):
    """Interface for prompt enhancement implementations"""

    @abstractmethod
    async def enhance(self, request: EnhancementRequest) -> EnhancementResult:
        """
        Enhance a user query.

        Args:
            request: Enhancement request with query and context

        Returns:
            EnhancementResult: Enhanced query with metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if enhancer is available for use.

        Returns:
            bool: True if enhancer can be used
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get enhancer name for identification.

        Returns:
            str: Enhancer name
        """
        pass


class IEnhancementValidator(ABC):
    """Interface for validating enhancement results"""

    @abstractmethod
    async def validate(self, original: str, enhanced: str, context: Optional[EnhancementContext] = None) -> float:
        """
        Validate enhancement quality.

        Args:
            original: Original query
            enhanced: Enhanced query
            context: Optional context information

        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        pass


class IEnhancementCache(ABC):
    """Interface for caching enhancement results"""

    @abstractmethod
    async def get(self, query: str, context_hash: Optional[str] = None) -> Optional[EnhancementResult]:
        """
        Retrieve cached enhancement result.

        Args:
            query: Original query
            context_hash: Optional context identifier

        Returns:
            Optional[EnhancementResult]: Cached result if available
        """
        pass

    @abstractmethod
    async def set(self, query: str, result: EnhancementResult, context_hash: Optional[str] = None, ttl: Optional[int] = None):
        """
        Store enhancement result in cache.

        Args:
            query: Original query
            result: Enhancement result to cache
            context_hash: Optional context identifier
            ttl: Time to live in seconds
        """
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None):
        """
        Clear cache entries.

        Args:
            pattern: Optional pattern to match for selective clearing
        """
        pass


class IMetricsCollector(ABC):
    """Interface for collecting enhancement metrics"""

    @abstractmethod
    async def record_enhancement(self, result: EnhancementResult):
        """
        Record enhancement result for metrics.

        Args:
            result: Enhancement result to record
        """
        pass

    @abstractmethod
    async def get_metrics(self) -> EnhancementMetrics:
        """
        Get current metrics.

        Returns:
            EnhancementMetrics: Current metrics snapshot
        """
        pass

    @abstractmethod
    async def reset_metrics(self):
        """Reset all metrics to zero"""
        pass


class IEnhancementOrchestrator(ABC):
    """Interface for orchestrating the enhancement process"""

    @abstractmethod
    async def enhance_query(self, request: EnhancementRequest) -> EnhancementResult:
        """
        Main enhancement orchestration method.

        Args:
            request: Enhancement request

        Returns:
            EnhancementResult: Final enhancement result
        """
        pass

    @abstractmethod
    async def get_enhancement_preview(self, query: str, context: Optional[EnhancementContext] = None) -> EnhancementResult:
        """
        Get enhancement preview without caching.

        Args:
            query: Query to enhance
            context: Optional context

        Returns:
            EnhancementResult: Enhancement preview
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of enhancement system.

        Returns:
            Dict[str, Any]: Health status of all components
        """
        pass


class IModelManager(ABC):
    """Interface for model management (abstraction over existing model manager)"""

    @abstractmethod
    async def inference(self, prompt: str, max_tokens: int = 50, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Run model inference.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature

        Returns:
            Dict[str, Any]: Inference result with text and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if model is available.

        Returns:
            bool: True if model can be used
        """
        pass


class IIntentPredictor(ABC):
    """Interface for fast intent prediction"""

    @abstractmethod
    async def predict_intent(self, query: str, context: Optional[EnhancementContext] = None) -> Optional[str]:
        """
        Predict likely intent of query.

        Args:
            query: User query
            context: Optional context

        Returns:
            Optional[str]: Predicted intent or None
        """
        pass

    @abstractmethod
    def get_supported_intents(self) -> list[str]:
        """
        Get list of supported intents.

        Returns:
            list[str]: List of intent names
        """
        pass


# Factory interfaces for dependency injection

class IEnhancementFactory(ABC):
    """Factory for creating enhancement components"""

    @abstractmethod
    def create_analyzer(self) -> IQueryAnalyzer:
        """Create query analyzer instance"""
        pass

    @abstractmethod
    def create_enhancer(self, enhancer_type: str = "ai_dynamic") -> IPromptEnhancer:
        """Create prompt enhancer instance"""
        pass

    @abstractmethod
    def create_validator(self) -> IEnhancementValidator:
        """Create enhancement validator instance"""
        pass

    @abstractmethod
    def create_cache(self) -> IEnhancementCache:
        """Create enhancement cache instance"""
        pass

    @abstractmethod
    def create_metrics_collector(self) -> IMetricsCollector:
        """Create metrics collector instance"""
        pass

    @abstractmethod
    def create_orchestrator(self) -> IEnhancementOrchestrator:
        """Create enhancement orchestrator instance"""
        pass