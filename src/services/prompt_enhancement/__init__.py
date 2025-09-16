"""
Prompt Enhancement System

A modular, AI-driven system for enhancing user queries in e-commerce applications.
Provides intelligent query transformation to improve intent classification and response quality.

Main Components:
- EnhancementService: High-level service interface
- EnhancementOrchestrator: Main coordination logic
- AIPromptEnhancer: AI-driven enhancement engine
- IntelligentQueryAnalyzer: Query complexity analysis
- RedisEnhancementCache: Performance caching layer

Usage:
    from src.services.prompt_enhancement import EnhancementService

    # Initialize with your model manager
    enhancement_service = EnhancementService(model_manager)

    # Enhance a query
    result = await enhancement_service.enhance_query("show products")
    print(result["enhanced_query"])  # "show me available products in inventory catalog"
"""

from .factory import EnhancementService, EnhancementFactory
from .orchestrator import EnhancementOrchestrator
from .models import (
    EnhancementRequest,
    EnhancementResult,
    EnhancementContext,
    EnhancementMethod,
    QueryComplexity,
    EnhancementLevel,
    EnhancementMetrics
)

# Main exports
__all__ = [
    # Main service interface
    "EnhancementService",

    # Core components
    "EnhancementFactory",
    "EnhancementOrchestrator",

    # Data models
    "EnhancementRequest",
    "EnhancementResult",
    "EnhancementContext",
    "EnhancementMetrics",

    # Enums
    "EnhancementMethod",
    "QueryComplexity",
    "EnhancementLevel"
]

# Version information
__version__ = "1.0.0"
__author__ = "E-commerce AI Team"
__description__ = "AI-powered prompt enhancement system for e-commerce applications"