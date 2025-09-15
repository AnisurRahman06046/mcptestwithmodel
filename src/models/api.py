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
    # context: Optional[QueryContext] = None  # Will be extracted from token
    options: Optional[QueryOptions] = None
    # Optional conversation_id to continue existing conversation
    conversation_id: Optional[str] = None


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
    tokens_per_second: Optional[float] = None


class UserTokenInfo(BaseModel):
    """User token information for query responses"""

    used_this_query: int
    total_used_this_month: int
    allocated_tokens: int
    remaining_tokens: int
    usage_percentage: float
    queries_remaining_estimate: Optional[int] = None


class SubscriptionInfo(BaseModel):
    """Subscription information for query responses"""

    plan: str
    status: str
    days_remaining: int


class QueryResponse(BaseModel):
    success: bool = True
    response: str
    structured_data: Optional[StructuredData] = None
    metadata: QueryMetadata
    error: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None
    user_token_info: Optional[UserTokenInfo] = None
    subscription_info: Optional[SubscriptionInfo] = None
    # New conversation fields (optional for backward compatibility)
    conversation_id: Optional[str] = None
    message_index: Optional[int] = None


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


class SubscriptionRequest(BaseModel):
    """Request model for creating/updating subscription"""

    plan_name: str = Field(..., min_length=1, description="Plan identifier")
    plan_display_name: str = Field(..., min_length=1, description="Human readable plan name")
    allocated_tokens: int = Field(..., ge=0, description="Monthly token allocation")
    monthly_fee: float = Field(..., ge=0, description="Monthly subscription fee")
    currency: str = Field(default="USD", max_length=3, description="Currency code")
    billing_cycle: str = Field(default="monthly", description="Billing cycle")
    action: str = Field(default="create", description="Action type: create, update, upgrade, downgrade")

    class Config:
        schema_extra = {
            "example": {
                "plan_name": "pro",
                "plan_display_name": "Pro Plan",
                "allocated_tokens": 20000,
                "monthly_fee": 29.99,
                "currency": "USD",
                "billing_cycle": "monthly",
                "action": "create"
            }
        }


class SubscriptionResponse(BaseModel):
    """Response model for subscription operations"""

    success: bool = True
    subscription_id: str
    user_id: str
    shop_id: str
    plan_name: str
    plan_display_name: str
    allocated_tokens: int
    monthly_fee: float
    currency: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: datetime
    current_usage: int = 0
    remaining_tokens: int
    usage_percentage: float
    action_performed: str
    previous_plan: Optional[str] = None
    effective_date: datetime
    message: str = "Subscription updated successfully"

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "subscription_id": "sub_abc123",
                "user_id": "user123",
                "plan_name": "pro",
                "allocated_tokens": 20000,
                "monthly_fee": 29.99,
                "current_usage": 5670,
                "remaining_tokens": 14330,
                "usage_percentage": 28.35,
                "action_performed": "create",
                "message": "Successfully created Pro Plan subscription"
            }
        }


class SubscriptionStatusResponse(BaseModel):
    """Response model for subscription status"""

    success: bool = True
    user_id: str
    shop_id: str
    subscription_id: str
    plan_name: str
    plan_display_name: str
    status: str
    allocated_tokens: int
    monthly_fee: float
    currency: str
    current_usage: int
    remaining_tokens: int
    usage_percentage: float
    current_period_start: datetime
    current_period_end: datetime
    days_remaining_in_period: int
    next_billing_date: datetime
    next_billing_amount: float
    avg_daily_usage: float
    projected_monthly_usage: float
    usage_trend: str
    alerts: List[Dict] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    usage_history: Dict[str, Any] = Field(default_factory=dict)
    plan_history: List[Dict] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "user_id": "user123",
                "subscription_id": "sub_abc123",
                "plan_name": "pro",
                "allocated_tokens": 20000,
                "current_usage": 12750,
                "remaining_tokens": 7250,
                "usage_percentage": 63.75,
                "days_remaining_in_period": 12,
                "avg_daily_usage": 425,
                "usage_trend": "stable",
                "status": "active"
            }
        }


# Conversation API Models
class ConversationListResponse(BaseModel):
    """Response for listing user conversations"""

    success: bool = True
    conversations: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "conversations": [
                    {
                        "conversation_id": "conv-uuid-123",
                        "title": "Sales Analysis Discussion",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T11:45:00Z",
                        "message_count": 8,
                        "total_tokens_used": 1850,
                        "last_message_preview": "Based on your data...",
                        "status": "active"
                    }
                ],
                "total_count": 1
            }
        }


class ConversationDetailResponse(BaseModel):
    """Response for getting full conversation history"""

    success: bool = True
    conversation: Dict[str, Any] = Field(default_factory=dict)
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "conversation": {
                    "conversation_id": "conv-uuid-123",
                    "title": "Sales Analysis Discussion",
                    "created_at": "2024-01-15T10:30:00Z",
                    "message_count": 4,
                    "status": "active"
                },
                "messages": [
                    {
                        "message_id": "msg-uuid-1",
                        "role": "user",
                        "content": "Show me sales data",
                        "message_index": 0,
                        "timestamp": "2024-01-15T10:30:00Z",
                        "tokens_used": 0
                    }
                ]
            }
        }


class ConversationTitleUpdateRequest(BaseModel):
    """Request for updating conversation title"""

    title: str = Field(..., min_length=1, max_length=200)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Q1 2024 Sales Analysis"
            }
        }