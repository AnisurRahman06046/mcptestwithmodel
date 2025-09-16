"""
Hybrid Intent Classification System

A production-grade intent classification system that combines:
- SetFit models for fast classification (30ms)
- LLM fallback for adaptive learning (new intents)
- Automatic model improvement through continuous learning

Designed to run alongside existing systems without breaking changes.

Usage:
    from src.services.hybrid_intent_classification import HybridIntentClassificationService

    # Initialize with existing query processor (non-breaking)
    hybrid_service = HybridIntentClassificationService(query_processor)

    # Classify intent (drop-in replacement)
    intent = await hybrid_service.classify_intent("show products")

    # Enable hybrid mode when ready
    await hybrid_service.enable_hybrid_classification()
"""

from .hybrid_classifier import HybridIntentClassificationService, HybridIntentClassifier
from .models import HybridConfig, ClassificationResult, ClassificationMethod, LearningMetrics

__all__ = [
    "HybridIntentClassificationService",
    "HybridIntentClassifier",
    "HybridConfig",
    "ClassificationResult",
    "ClassificationMethod",
    "LearningMetrics"
]

__version__ = "1.0.0"
__description__ = "Hybrid intent classification with automatic learning"