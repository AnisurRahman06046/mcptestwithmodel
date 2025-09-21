"""
Chat API endpoint for testing - No authentication required
Simple endpoint that works exactly like query API but without auth
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from src.services.universal_llm_processor import universal_llm_processor
from src.services.conversation_service import conversation_service
from src.config.settings import settings
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    query: str
    shop_id: int = 10  # Default shop ID for testing
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    conversation_id: str
    metadata: Optional[dict] = None
    error: Optional[str] = None


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Simple chat endpoint that works exactly like query API but without authentication

    Usage:
    POST /api/v1/chat
    {
        "query": "How much revenue in July?",
        "shop_id": 10
    }
    """

    logger.info(f"[CHAT API] Processing query: {request.query} for shop_id: {request.shop_id}")

    # Create context (same as query API but without auth)
    context = {
        "user_id": "test_user",  # Fixed test user
        "shop_id": str(request.shop_id),
        "timezone": "UTC",  # Default timezone
        "currency": "USD"   # Default currency
    }

    # Handle conversation (optional)
    conversation_id = request.conversation_id
    if not conversation_id:
        # Create new conversation
        conversation = await conversation_service.create_conversation(
            "test_user",
            str(request.shop_id),
            request.query
        )
        conversation_id = conversation["conversation_id"] if isinstance(conversation, dict) else conversation.conversation_id

    # Add user message
    await conversation_service.add_message(
        conversation_id,
        "user",
        request.query,
        tokens_used=0
    )

    try:
        # Process the query using appropriate processor (same logic as query API)
        query_lower = request.query.lower().strip()
        simple_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]

        if query_lower in simple_greetings:
            # Simple greeting - return quick response
            logger.info("[CHAT API] Using pattern-based processor for greeting")
            result = {
                "success": True,
                "response": "Hello! I'm here to help you with your store data. You can ask me about products, sales, inventory, customers, or any other business metrics.",
                "metadata": {
                    "model_used": "pattern-based",
                    "execution_time_ms": 10,
                    "tools_called": [],
                    "confidence_score": 1.0,
                    "query_intent": "greeting"
                }
            }
        else:
            # Use universal LLM processor
            logger.info("[CHAT API] Using UNIVERSAL LLM query processor")
            result = await universal_llm_processor.process_query(
                query=request.query,
                context=context
            )

        # Check if result is None
        if result is None:
            logger.error("[CHAT API] Processor returned None")
            return ChatResponse(
                success=False,
                response="I encountered an error processing your request. Please try again.",
                conversation_id=conversation_id,
                error="Processor returned None"
            )

        if result.get("success"):
            # Safely extract metadata
            metadata = result.get("metadata", {})
            token_usage = metadata.get("token_usage", {}) if metadata else {}

            # Add assistant response to conversation
            await conversation_service.add_message(
                conversation_id,
                "assistant",
                result.get("response", ""),
                tokens_used=token_usage.get("total_tokens", 0) if isinstance(token_usage, dict) else 0,
                execution_time_ms=metadata.get("execution_time_ms", 0) if metadata else 0,
                model_used=metadata.get("model_used", "unknown") if metadata else "unknown"
            )

            return ChatResponse(
                success=True,
                response=result.get("response", ""),
                conversation_id=conversation_id,
                metadata={
                    "model_used": metadata.get("model_used") if metadata else None,
                    "execution_time_ms": metadata.get("execution_time_ms") if metadata else None,
                    "tools_called": metadata.get("tools_called", []) if metadata else [],
                    "shop_id": request.shop_id
                }
            )
        else:
            # Handle failure case
            error_response = result.get("response", "I encountered an error processing your request.")

            # Still save the error response to conversation
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
                error=result.get("error", "Unknown error")
            )

    except Exception as e:
        logger.error(f"[CHAT API] Error: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            response="An error occurred while processing your request.",
            conversation_id=conversation_id,
            error=str(e)
        )


@router.get("/chat/shops")
async def get_available_shops():
    """
    Get list of all available shops for the dropdown
    """
    try:
        from src.database.mongodb import mongodb_client

        if not mongodb_client.is_connected:
            await mongodb_client.connect()

        db = mongodb_client.database

        # Get shops directly from shop collection
        cursor = db.shop.find({}, {"_id": 0, "id": 1, "name": 1, "status": 1}).limit(100)
        shops = await cursor.to_list(length=100)

        # Format shop list
        shop_list = []
        for shop in shops:
            shop_id = shop.get("id") or shop.get("shop_id")
            shop_name = shop.get("name") or f"Shop {shop_id}"

            if shop_id is not None:
                shop_list.append({
                    "id": shop_id,
                    "name": shop_name,
                    "status": shop.get("status", "active")
                })

        # Sort by shop ID
        shop_list.sort(key=lambda x: x["id"])

        return {
            "success": True,
            "shops": shop_list,
            "total": len(shop_list)
        }

    except Exception as e:
        logger.error(f"Error fetching shops: {e}")
        return {
            "success": False,
            "error": str(e),
            "shops": [
                {"id": 10, "name": "Shop 10 (Default)"},
                {"id": 1, "name": "Shop 1"},
                {"id": 2, "name": "Shop 2"}
            ]
        }


@router.get("/chat/ui", response_class=HTMLResponse)
async def serve_chat_ui():
    """
    Serve the chat UI HTML page
    Access at: http://localhost:8000/api/v1/chat/ui
    """
    import os

    # Path to the HTML file
    html_file_path = os.path.join(os.path.dirname(__file__), "../../../chat-ui.html")

    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Update the API URLs to use relative paths for same-origin requests
        html_content = html_content.replace(
            "const API_URL = 'http://localhost:8000/api/v1/chat/enhanced';",
            "const API_URL = '/api/v1/chat/enhanced';"
        )
        html_content = html_content.replace(
            "const SHOPS_API_URL = 'http://localhost:8000/api/v1/chat/shops';",
            "const SHOPS_API_URL = '/api/v1/chat/shops';"
        )

        return HTMLResponse(content=html_content)

    except FileNotFoundError:
        logger.error(f"Chat UI HTML file not found at {html_file_path}")
        return HTMLResponse(
            content="<h1>Error: Chat UI file not found</h1><p>Please ensure chat-ui.html exists in the project root.</p>",
            status_code=404
        )
    except Exception as e:
        logger.error(f"Error serving chat UI: {e}")
        return HTMLResponse(
            content=f"<h1>Error loading chat UI</h1><p>{str(e)}</p>",
            status_code=500
        )