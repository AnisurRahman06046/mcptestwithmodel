"""
Core data models for prompt enhancement system.
Provides type safety and clear contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import time


class EnhancementMethod(Enum):
    """Enhancement methods available"""
    AI_DYNAMIC = "ai_dynamic"
    FALLBACK = "fallback"
    CACHED = "cached"


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"        # 1-2 words
    MODERATE = "moderate"    # 3-5 words, basic structure
    STRUCTURED = "structured" # Has time/business terms
    COMPLEX = "complex"      # Detailed, well-formed


class EnhancementLevel(Enum):
    """Enhancement intensity levels"""
    MINIMAL = "minimal"         # Light enhancement
    STANDARD = "standard"       # Balanced enhancement
    COMPREHENSIVE = "comprehensive"  # Heavy enhancement


@dataclass(frozen=True)
class QueryAnalysis:
    """Analysis result of user query"""
    complexity: QueryComplexity
    word_count: int
    has_time_references: bool
    has_business_terms: bool
    estimated_intent: Optional[str] = None
    confidence: float = 0.0

    @property
    def recommended_enhancement_level(self) -> EnhancementLevel:
        """Recommend enhancement level based on analysis"""
        if self.complexity == QueryComplexity.SIMPLE:
            return EnhancementLevel.COMPREHENSIVE
        elif self.complexity == QueryComplexity.MODERATE:
            return EnhancementLevel.STANDARD
        else:
            return EnhancementLevel.MINIMAL


@dataclass
class EnhancementContext:
    """Context information for enhancement"""
    user_id: Optional[str] = None
    shop_id: Optional[str] = None
    conversation_history: Optional[List[str]] = None
    business_domain: str = "ecommerce"
    preferred_enhancement_level: Optional[EnhancementLevel] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "user_id": self.user_id,
            "shop_id": self.shop_id,
            "business_domain": self.business_domain,
            "has_history": bool(self.conversation_history),
            "preferred_level": self.preferred_enhancement_level.value if self.preferred_enhancement_level else None
        }


@dataclass
class EnhancementResult:
    """Result of prompt enhancement operation"""
    original_query: str
    enhanced_query: str
    method: EnhancementMethod
    confidence: float
    processing_time_ms: float
    analysis: Optional[QueryAnalysis] = None
    context: Optional[EnhancementContext] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def was_enhanced(self) -> bool:
        """Check if query was actually enhanced"""
        return self.enhanced_query != self.original_query

    @property
    def enhancement_ratio(self) -> float:
        """Calculate enhancement ratio (enhanced length / original length)"""
        if not self.original_query:
            return 0.0
        return len(self.enhanced_query) / len(self.original_query)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "original_query": self.original_query,
            "enhanced_query": self.enhanced_query,
            "method": self.method.value,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "was_enhanced": self.was_enhanced,
            "enhancement_ratio": self.enhancement_ratio,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class EnhancementRequest:
    """Request for prompt enhancement"""
    query: str
    context: Optional[EnhancementContext] = None
    preferred_method: Optional[EnhancementMethod] = None
    force_enhancement: bool = False  # Force enhancement even if query seems good

    def __post_init__(self):
        """Validate request data"""
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")

        self.query = self.query.strip()


@dataclass
class EnhancementMetrics:
    """Metrics for monitoring enhancement performance"""
    total_requests: int = 0
    successful_enhancements: int = 0
    cache_hits: int = 0
    ai_enhancements: int = 0
    fallbacks: int = 0
    average_processing_time: float = 0.0
    average_confidence: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_enhancements / self.total_requests

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    def update(self, result: EnhancementResult):
        """Update metrics with new result"""
        self.total_requests += 1

        if result.was_enhanced:
            self.successful_enhancements += 1

        if result.method == EnhancementMethod.CACHED:
            self.cache_hits += 1
        elif result.method == EnhancementMethod.AI_DYNAMIC:
            self.ai_enhancements += 1
        else:
            self.fallbacks += 1

        # Update running averages
        self.average_processing_time = (
            (self.average_processing_time * (self.total_requests - 1) + result.processing_time_ms)
            / self.total_requests
        )

        self.average_confidence = (
            (self.average_confidence * (self.total_requests - 1) + result.confidence)
            / self.total_requests
        )