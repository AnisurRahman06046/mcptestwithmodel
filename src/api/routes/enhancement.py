"""
API routes for prompt enhancement functionality.
Provides endpoints for query enhancement preview and processing.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from src.services.prompt_enhancement import EnhancementService
from src.services.real_model_manager import real_model_manager

logger = logging.getLogger(__name__)

# Initialize enhancement service (singleton pattern)
_enhancement_service: Optional[EnhancementService] = None


def get_enhancement_service() -> EnhancementService:
    """
    Get or create enhancement service instance.

    Returns:
        EnhancementService: Configured enhancement service
    """
    global _enhancement_service

    if _enhancement_service is None:
        # Configuration for enhancement service
        config = {
            "cache": {
                "type": "memory",  # Use in-memory cache only
                "max_size": 1000,
                "ttl": 3600  # 1 hour cache TTL
            }
        }

        try:
            _enhancement_service = EnhancementService(
                model_manager=real_model_manager,
                config=config
            )
            logger.info("Enhancement service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhancement service: {e}")
            raise HTTPException(status_code=500, detail="Enhancement service unavailable")

    return _enhancement_service


# Request/Response models
class EnhanceRequest(BaseModel):
    """Request model for prompt enhancement"""
    query: str = Field(..., min_length=1, max_length=500, description="Query to enhance")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context information")
    force_enhancement: bool = Field(False, description="Force enhancement even if not needed")

    class Config:
        schema_extra = {
            "example": {
                "query": "show products",
                "context": {
                    "user_id": "user123",
                    "shop_id": "shop456"
                },
                "force_enhancement": False
            }
        }


class EnhanceResponse(BaseModel):
    """Response model for prompt enhancement"""
    success: bool = Field(..., description="Whether enhancement was successful")
    original_query: str = Field(..., description="Original user query")
    enhanced_query: str = Field(..., description="Enhanced version of the query")
    was_enhanced: bool = Field(..., description="Whether the query was actually changed")
    method: str = Field(..., description="Enhancement method used")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in enhancement quality")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "original_query": "show products",
                "enhanced_query": "show me available products in inventory catalog",
                "was_enhanced": True,
                "method": "ai_dynamic",
                "confidence": 0.92,
                "processing_time_ms": 245.5,
                "metadata": {
                    "enhancement_level": "comprehensive",
                    "model_tokens_used": 45
                }
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Health check timestamp")
    components: Dict[str, Any] = Field(..., description="Component health details")


class MetricsResponse(BaseModel):
    """Response model for enhancement metrics"""
    total_requests: int = Field(..., description="Total enhancement requests")
    successful_enhancements: int = Field(..., description="Successful enhancements")
    cache_hits: int = Field(..., description="Cache hits")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Enhancement success rate")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    average_processing_time: float = Field(..., description="Average processing time in ms")
    average_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence score")


# Create router
router = APIRouter(prefix="/api/enhancement", tags=["Enhancement"])


@router.post("/preview", response_model=EnhanceResponse)
async def get_enhancement_preview(
    request: EnhanceRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Get enhancement preview for a query without caching.

    This endpoint shows what the enhanced query would look like
    without actually processing it or storing the result.
    """
    try:
        # Get enhancement service
        enhancement_service = get_enhancement_service()

        # Simple context (no complex auth for preview)
        context = request.context or {}

        # Get enhancement preview
        result = await enhancement_service.get_enhancement_preview(
            query=request.query,
            context=context
        )

        return EnhanceResponse(
            success=True,
            **result
        )

    except Exception as e:
        logger.error(f"Enhancement preview failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Enhancement preview failed: {str(e)}"
        )


# Removed - Only using preview endpoint


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of enhancement system components.

    Returns health status of all enhancement system components
    including AI models, cache, and metrics collection.
    """
    try:
        enhancement_service = get_enhancement_service()
        health_data = await enhancement_service.health_check()

        return HealthResponse(**health_data)

    except Exception as e:
        logger.error(f"Enhancement health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics():
    """Get enhancement system performance metrics"""
    try:
        enhancement_service = get_enhancement_service()
        metrics_data = await enhancement_service.get_metrics()
        return metrics_data
    except Exception as e:
        logger.error(f"Failed to get enhancement metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


# Removed - Not needed for simple in-memory cache