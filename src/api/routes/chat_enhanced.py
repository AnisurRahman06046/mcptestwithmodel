"""
Enhanced Chat API with Query Classification and Disambiguation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.services.enhanced_query_processor import enhanced_query_processor
from src.services.conversation_service import conversation_service
from src.database.mongodb import mongodb_client
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    query: str
    shop_id: int = 10  # Default shop ID for testing
    conversation_id: Optional[str] = None
    # For disambiguation responses
    selected_intent: Optional[str] = None
    original_query: Optional[str] = None


class DisambiguationOption(BaseModel):
    intent: str
    description: str


class ChatResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    conversation_id: str
    # Disambiguation fields
    needs_clarification: Optional[bool] = False
    question: Optional[str] = None
    options: Optional[List[DisambiguationOption]] = None
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/chat/enhanced", response_model=ChatResponse)
async def enhanced_chat_endpoint(request: ChatRequest):
    """
    Enhanced chat endpoint with classification and disambiguation support

    Usage:
    1. Normal query:
    POST /api/v1/chat/enhanced
    {
        "query": "How many active products do I have?",
        "shop_id": 10
    }

    2. Disambiguation response:
    POST /api/v1/chat/enhanced
    {
        "selected_intent": "active_products",
        "original_query": "Show me active inventory",
        "conversation_id": "xxx-xxx-xxx",
        "shop_id": 10
    }
    """

    logger.info(f"[ENHANCED CHAT] Processing query: {request.query or request.original_query} for shop_id: {request.shop_id}")

    # Ensure MongoDB is connected
    if not mongodb_client.is_connected:
        await mongodb_client.connect()

    # Create context
    context = {
        "user_id": "test_user",
        "shop_id": str(request.shop_id),
        "timezone": "UTC",
        "currency": "USD"
    }

    # Handle conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        # Create new conversation
        conversation = await conversation_service.create_conversation(
            "test_user",
            str(request.shop_id),
            request.query or request.original_query
        )
        conversation_id = conversation["conversation_id"] if isinstance(conversation, dict) else conversation.conversation_id

    try:
        # Check if this is a disambiguation response
        if request.selected_intent and request.original_query:
            logger.info(f"[ENHANCED CHAT] Processing disambiguation: intent={request.selected_intent}")

            # Add user's selection to conversation
            await conversation_service.add_message(
                conversation_id,
                "user",
                f"Selected: {request.selected_intent}",
                tokens_used=0
            )

            # Process with selected intent
            result = await enhanced_query_processor.handle_disambiguation_response(
                original_query=request.original_query,
                selected_intent=request.selected_intent,
                context=context
            )

        else:
            # Add user message to conversation
            await conversation_service.add_message(
                conversation_id,
                "user",
                request.query,
                tokens_used=0
            )

            # Process normal query
            result = await enhanced_query_processor.process_query(
                query=request.query,
                context=context
            )

        # Handle disambiguation response
        if result.get("needs_clarification"):
            logger.info(f"[ENHANCED CHAT] Disambiguation needed for query")

            # Save disambiguation request to conversation
            await conversation_service.add_message(
                conversation_id,
                "assistant",
                result.get("question", "Please clarify your query"),
                tokens_used=0,
                execution_time_ms=0,
                model_used="classifier"
            )

            return ChatResponse(
                success=True,
                conversation_id=conversation_id,
                needs_clarification=True,
                question=result.get("question"),
                options=[
                    DisambiguationOption(
                        intent=opt["intent"],
                        description=opt["description"]
                    )
                    for opt in result.get("options", [])
                ],
                metadata={
                    "original_query": request.query,
                    "confidence": result.get("metadata", {}).get("confidence"),
                    "trigger_words": result.get("metadata", {}).get("trigger_words")
                }
            )

        # Handle normal response
        if result.get("success"):
            response_text = result.get("response", "")

            # Extract metadata
            metadata = result.get("metadata", {})

            # Add assistant response to conversation
            await conversation_service.add_message(
                conversation_id,
                "assistant",
                response_text,
                tokens_used=metadata.get("token_usage", {}).get("total_tokens", 0) if "token_usage" in metadata else 0,
                execution_time_ms=metadata.get("execution_time_ms", 0),
                model_used=metadata.get("method", "enhanced")
            )

            return ChatResponse(
                success=True,
                response=response_text,
                conversation_id=conversation_id,
                metadata={
                    "method": metadata.get("method"),
                    "intent": metadata.get("intent"),
                    "confidence": metadata.get("confidence"),
                    "classification_method": metadata.get("classification_method"),
                    "execution_time_ms": metadata.get("execution_time_ms"),
                    "cached": metadata.get("cached", False),
                    "shop_id": request.shop_id
                }
            )
        else:
            # Handle failure
            error_msg = result.get("error", "Processing failed")
            error_response = result.get("response", "I encountered an error processing your request.")

            # Save error to conversation
            await conversation_service.add_message(
                conversation_id,
                "assistant",
                error_response,
                tokens_used=0,
                execution_time_ms=0,
                model_used="error"
            )

            return ChatResponse(
                success=False,
                response=error_response,
                conversation_id=conversation_id,
                error=error_msg,
                metadata={
                    "shop_id": request.shop_id
                }
            )

    except Exception as e:
        logger.error(f"[ENHANCED CHAT] Error: {e}", exc_info=True)

        # Save error to conversation
        await conversation_service.add_message(
            conversation_id,
            "assistant",
            "An unexpected error occurred.",
            tokens_used=0,
            execution_time_ms=0,
            model_used="error"
        )

        return ChatResponse(
            success=False,
            response="An unexpected error occurred. Please try again.",
            conversation_id=conversation_id,
            error=str(e),
            metadata={
                "shop_id": request.shop_id
            }
        )


@router.get("/chat/metrics")
async def get_chat_metrics():
    """
    Get metrics for the enhanced chat system

    Returns classification metrics, processing metrics, etc.
    """
    metrics = enhanced_query_processor.get_metrics()

    return {
        "success": True,
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/chat/clear-cache")
async def clear_chat_cache():
    """
    Clear all caches in the enhanced chat system

    Useful for testing and debugging
    """
    enhanced_query_processor.classifier.clear_cache()
    enhanced_query_processor.deterministic.clear_cache()

    return {
        "success": True,
        "message": "All caches cleared",
        "timestamp": datetime.utcnow().isoformat()
    }