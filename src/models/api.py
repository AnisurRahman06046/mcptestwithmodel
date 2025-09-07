from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class QueryContext(BaseModel):
    user_id: Optional[str] = None
    shop_id: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "USD"


class QueryOptions(BaseModel):
    include_structured_data: bool = True
    max_results: int = 50
    preferred_model: Optional[str] = None


class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query to process")
    context: Optional[QueryContext] = None
    options: Optional[QueryOptions] = None


class StructuredData(BaseModel):
    product: Optional[str] = None
    category: Optional[str] = None
    period: Optional[Dict[str, str]] = None
    metrics: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QueryMetadata(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    model_used: str
    execution_time_ms: int
    tools_called: List[str]
    confidence_score: float = 0.0
    query_intent: Optional[str] = None
    extracted_entities: Optional[List[str]] = None
    token_usage: Optional[TokenUsage] = None


class QueryResponse(BaseModel):
    success: bool = True
    response: str
    structured_data: Optional[StructuredData] = None
    metadata: QueryMetadata
    error: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None


class ModelStatus(BaseModel):
    name: str
    status: str  # "loaded", "loading", "available", "error"
    memory_usage: Optional[str] = None
    load_time: Optional[str] = None
    last_used: Optional[datetime] = None
    error_message: Optional[str] = None


class SystemResources(BaseModel):
    total_memory: str
    available_memory: str
    gpu_memory: Optional[str] = None
    gpu_utilization: Optional[str] = None


class ModelsStatusResponse(BaseModel):
    models: List[ModelStatus]
    active_model: Optional[str] = None
    system_resources: SystemResources


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter]
    examples: List[str] = []


class ToolsListResponse(BaseModel):
    tools: List[ToolDefinition]


class HealthCheck(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime: Optional[float] = None
    database_connected: bool = True
    model_loaded: bool = False
    version: str = "1.0.0"