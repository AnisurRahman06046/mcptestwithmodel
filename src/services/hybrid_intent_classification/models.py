"""
Data models for hybrid intent classification system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import time


class ClassificationMethod(Enum):
    """Classification methods available"""
    SETFIT_FAST = "setfit_fast"
    LLM_ADAPTIVE = "llm_adaptive"
    CACHED = "cached"
    FALLBACK = "fallback"


class ConfidenceLevel(Enum):
    """Confidence levels for classification results"""
    HIGH = "high"        # >0.8 - Use result directly
    MEDIUM = "medium"    # 0.5-0.8 - Use with caution
    LOW = "low"          # <0.5 - Use LLM fallback


@dataclass(frozen=True)
class ClassificationResult:
    """Result of intent classification"""
    intent: str
    confidence: float
    method: ClassificationMethod
    processing_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category"""
        if self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "method": self.method.value,
            "processing_time_ms": self.processing_time_ms,
            "confidence_level": self.confidence_level.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class TrainingExample:
    """Training example for learning system"""
    query: str
    intent: str
    confidence: float
    source: ClassificationMethod
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "query": self.query,
            "intent": self.intent,
            "confidence": self.confidence,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


@dataclass
class LearningMetrics:
    """Metrics for learning system performance"""
    total_classifications: int = 0
    setfit_usage: int = 0
    llm_usage: int = 0
    cache_hits: int = 0
    new_intents_discovered: int = 0
    retraining_sessions: int = 0
    average_setfit_time: float = 0.0
    average_llm_time: float = 0.0
    setfit_accuracy_estimate: float = 0.0

    @property
    def fast_path_percentage(self) -> float:
        """Percentage of queries using fast path"""
        if self.total_classifications == 0:
            return 0.0
        return (self.setfit_usage + self.cache_hits) / self.total_classifications * 100

    @property
    def learning_path_percentage(self) -> float:
        """Percentage of queries using learning path"""
        if self.total_classifications == 0:
            return 0.0
        return self.llm_usage / self.total_classifications * 100

    def update_classification(self, result: ClassificationResult):
        """Update metrics with classification result"""
        self.total_classifications += 1

        if result.method == ClassificationMethod.SETFIT_FAST:
            self.setfit_usage += 1
            # Update running average
            self.average_setfit_time = (
                (self.average_setfit_time * (self.setfit_usage - 1) + result.processing_time_ms)
                / self.setfit_usage
            )
        elif result.method == ClassificationMethod.LLM_ADAPTIVE:
            self.llm_usage += 1
            self.average_llm_time = (
                (self.average_llm_time * (self.llm_usage - 1) + result.processing_time_ms)
                / self.llm_usage
            )
        elif result.method == ClassificationMethod.CACHED:
            self.cache_hits += 1


@dataclass
class HybridConfig:
    """Configuration for hybrid intent classification system"""
    enabled: bool = False  # Feature flag - start disabled
    setfit_confidence_threshold: float = 0.8
    training_buffer_size: int = 50
    auto_retrain_enabled: bool = True
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    setfit_model_path: str = "./models/hybrid_intent_setfit"

    # Performance thresholds
    max_setfit_time_ms: float = 100.0
    max_llm_time_ms: float = 5000.0

    # Learning parameters
    min_examples_for_new_intent: int = 3
    retraining_schedule_hours: int = 24

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "setfit_confidence_threshold": self.setfit_confidence_threshold,
            "training_buffer_size": self.training_buffer_size,
            "auto_retrain_enabled": self.auto_retrain_enabled,
            "fast_path_percentage": "90%+ target",
            "learning_enabled": True
        }