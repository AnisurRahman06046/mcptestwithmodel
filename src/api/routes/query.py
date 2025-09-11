from fastapi import APIRouter, HTTPException, Header
from src.models.api import QueryRequest, QueryResponse, QueryMetadata, StructuredData, TokenUsage
from src.services.query_processor import query_processor
from src.services.auth_service import auth_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest, 
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """Process natural language queries and return structured responses"""
    
    try:
        logger.info(f"Processing authenticated query: {request.query}")
        
        # Step 1: Authenticate and get user context
        context = await auth_service.authenticate_request(authorization)
        logger.info(f"Authenticated user: {context.user_id}, shop: {context.shop_id}")
        
        # Step 2: Process the query using the query processor with context
        result = await query_processor.process_query(
            query=request.query,
            context=context.dict()
        )
        
        # Convert the result to the API response format
        if result["success"]:
            # Handle token usage if present
            token_usage = None
            if result["metadata"].get("token_usage"):
                token_usage_data = result["metadata"]["token_usage"]
                token_usage = TokenUsage(
                    prompt_tokens=token_usage_data["prompt_tokens"],
                    completion_tokens=token_usage_data["completion_tokens"],
                    total_tokens=token_usage_data["total_tokens"]
                )
            
            metadata = QueryMetadata(
                model_used=result["metadata"].get("model_used", "phi-3-mini"),
                execution_time_ms=result["metadata"]["execution_time_ms"],
                tools_called=result["metadata"]["tools_called"],
                confidence_score=result["metadata"]["confidence_score"],
                query_intent=result["metadata"].get("intent"),
                extracted_entities=list(result["metadata"].get("entities", {}).keys()),
                token_usage=token_usage
            )
            
            # Convert structured data
            structured_data = None
            if result.get("structured_data"):
                structured_data = StructuredData(**result["structured_data"])
            
            return QueryResponse(
                success=True,
                response=result["response"],
                structured_data=structured_data,
                metadata=metadata,
                debug=result.get("debug")
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