from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.models.api import QueryRequest, QueryResponse, QueryMetadata, StructuredData
from src.database import get_db
from src.services.query_processor import query_processor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Process natural language queries and return structured responses"""
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Process the query using the query processor
        result = query_processor.process_query(
            query=request.query,
            context=request.context.dict() if request.context else None
        )
        
        # Convert the result to the API response format
        if result["success"]:
            metadata = QueryMetadata(
                model_used=result["metadata"].get("model_used", "llama3-7b"),
                execution_time_ms=result["metadata"]["execution_time_ms"],
                tools_called=result["metadata"]["tools_called"],
                confidence_score=result["metadata"]["confidence_score"],
                query_intent=result["metadata"].get("intent"),
                extracted_entities=list(result["metadata"].get("entities", {}).keys())
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