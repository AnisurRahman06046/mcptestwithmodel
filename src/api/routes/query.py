from fastapi import APIRouter, HTTPException, Header
from src.models.api import (
    QueryRequest, QueryResponse, QueryMetadata, StructuredData, TokenUsage,
    UserTokenInfo, SubscriptionInfo
)
from src.services.query_processor import query_processor
from src.services.auth_service import auth_service
from src.services.token_service import token_service
from src.services.subscription_service import subscription_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """Process natural language queries with subscription and token management"""

    logger.info(f"Processing authenticated query: {request.query}")

    # Step 1: Authenticate and get user context
    context = await auth_service.authenticate_request(authorization)
    logger.info(f"Authenticated user: {context.user_id}, shop: {context.shop_id}")

    # Step 2: Check subscription and token limits
    estimated_tokens = token_service.estimate_query_tokens(
        request.query,
        request.options.dict() if request.options else None
    )

    can_proceed, token_info = await token_service.check_token_availability(
        context.user_id,
        context.shop_id,
        estimated_tokens
    )

    if not can_proceed:
        # Return token limit error with custom response structure
        from fastapi.responses import JSONResponse

        if token_info.get("error") == "NO_SUBSCRIPTION":
            return JSONResponse(
                status_code=402,
                content={
                    "error": "NO_SUBSCRIPTION",
                    "message": token_info.get("message"),
                    "subscribe_url": "/api/v1/subscription"
                }
            )
        elif token_info.get("error") == "TOKEN_LIMIT_EXCEEDED":
            return JSONResponse(
                status_code=429,
                content={
                    "error": "TOKEN_LIMIT_EXCEEDED",
                    "message": token_info.get("message"),
                    "current_usage": token_info.get("current_usage"),
                    "allocated_tokens": token_info.get("allocated_tokens"),
                    "remaining_tokens": token_info.get("remaining_tokens")
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "TOKEN_CHECK_FAILED",
                    "message": token_info.get("message", "Unable to verify token availability")
                }
            )

    try:

        # Step 3: Process the query using the query processor with context
        result = await query_processor.process_query(
            query=request.query,
            context=context.dict()
        )
        
        # Step 4: Process successful query response and update token usage
        if result["success"]:
            # Handle token usage if present
            token_usage = None
            actual_tokens_used = 0

            if result["metadata"].get("token_usage"):
                token_usage_data = result["metadata"]["token_usage"]
                actual_tokens_used = token_usage_data.get("total_tokens", estimated_tokens)

                token_usage = TokenUsage(
                    prompt_tokens=token_usage_data.get("prompt_tokens", 0),
                    completion_tokens=token_usage_data.get("completion_tokens", 0),
                    total_tokens=actual_tokens_used
                )
            else:
                # Fallback to estimated tokens if no actual usage reported
                actual_tokens_used = estimated_tokens

            # Step 5: Update token usage in database
            usage_update_result = await token_service.update_token_usage(
                context.user_id,
                context.shop_id,
                actual_tokens_used,
                {"query": request.query[:100]}  # First 100 chars for reference
            )

            if not usage_update_result.get("success"):
                logger.warning(f"Failed to update token usage for user {context.user_id}: {usage_update_result.get('error')}")

            # Step 6: Get updated user token and subscription info
            user_token_info = await token_service.get_user_token_info(
                context.user_id,
                context.shop_id,
                actual_tokens_used
            )

            subscription_info = await token_service.get_subscription_info(
                context.user_id,
                context.shop_id
            )

            metadata = QueryMetadata(
                model_used=result["metadata"].get("model_used", "phi-3-mini"),
                execution_time_ms=result["metadata"]["execution_time_ms"],
                tools_called=result["metadata"]["tools_called"],
                confidence_score=result["metadata"]["confidence_score"],
                query_intent=result["metadata"].get("query_intent"),
                extracted_entities=result["metadata"].get("extracted_entities", []),
                token_usage=token_usage
            )

            # Convert structured data
            structured_data = None
            if result.get("structured_data"):
                structured_data = StructuredData(**result["structured_data"])

            logger.info(f"Query processed successfully for user {context.user_id}, tokens used: {actual_tokens_used}")

            return QueryResponse(
                success=True,
                response=result["response"],
                structured_data=structured_data,
                metadata=metadata,
                debug=result.get("debug"),
                user_token_info=user_token_info,
                subscription_info=subscription_info
            )
        else:
            return QueryResponse(
                success=False,
                response=result["response"],
                metadata=QueryMetadata(
                    model_used="error",
                    execution_time_ms=result["metadata"]["execution_time_ms"],
                    tools_called=[],
                    confidence_score=0.0
                ),
                error=result.get("error")
            )
        
    except HTTPException:
        # Let HTTP exceptions bubble up to FastAPI's exception handler
        raise
    except Exception as e:
        logger.error(f"API error processing query: {e}", exc_info=True)
        return QueryResponse(
            success=False,
            response="I encountered an error while processing your request. Please try again.",
            metadata=QueryMetadata(
                model_used="error",
                execution_time_ms=0,
                tools_called=[],
                confidence_score=0.0
            ),
            error=str(e)
        )