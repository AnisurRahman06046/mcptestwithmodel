from fastapi import APIRouter
from src.models.api import ToolsListResponse, ToolDefinition, ToolParameter

router = APIRouter()


@router.get("/list", response_model=ToolsListResponse)
async def list_tools():
    """List all available tools and their capabilities"""
    
    tools = [
        ToolDefinition(
            name="get_sales_data",
            description="Retrieve sales data for products within specified time periods",
            parameters=[
                ToolParameter(name="product", type="string", description="Specific product name to filter", required=False),
                ToolParameter(name="category", type="string", description="Product category filter", required=False),
                ToolParameter(name="start_date", type="date", description="Start date in YYYY-MM-DD format", required=False),
                ToolParameter(name="end_date", type="date", description="End date in YYYY-MM-DD format", required=False),
                ToolParameter(name="group_by", type="enum", description="Grouping period (day, week, month, year)", required=False, default="day")
            ],
            examples=[
                "get_sales_data(product='Red Cotton T-Shirt', start_date='2024-01-01')",
                "get_sales_data(category='Electronics', group_by='month')"
            ]
        ),
        ToolDefinition(
            name="get_inventory_status",
            description="Check current inventory levels with alerts for low stock",
            parameters=[
                ToolParameter(name="product", type="string", description="Specific product to check", required=False),
                ToolParameter(name="category", type="string", description="Category filter", required=False),
                ToolParameter(name="low_stock_threshold", type="integer", description="Threshold for low stock alerts", required=False, default=10)
            ],
            examples=[
                "get_inventory_status(product='iPhone 15 Pro')",
                "get_inventory_status(category='Electronics', low_stock_threshold=20)"
            ]
        ),
        ToolDefinition(
            name="get_customer_info",
            description="Retrieve customer information and purchase history",
            parameters=[
                ToolParameter(name="customer_id", type="string", description="Specific customer ID", required=False),
                ToolParameter(name="email", type="string", description="Customer email address", required=False),
                ToolParameter(name="include_orders", type="boolean", description="Include order history", required=False, default=True)
            ],
            examples=[
                "get_customer_info(customer_id='123')",
                "get_customer_info(email='john@example.com')"
            ]
        ),
        ToolDefinition(
            name="get_order_details",
            description="Retrieve detailed information about specific orders",
            parameters=[
                ToolParameter(name="order_id", type="string", description="Specific order ID", required=False),
                ToolParameter(name="customer_id", type="string", description="Get orders for specific customer", required=False),
                ToolParameter(name="status", type="string", description="Filter by order status", required=False),
                ToolParameter(name="start_date", type="date", description="Orders from this date", required=False),
                ToolParameter(name="end_date", type="date", description="Orders until this date", required=False)
            ],
            examples=[
                "get_order_details(order_id='ord_123')",
                "get_order_details(status='pending', start_date='2024-01-01')"
            ]
        ),
        ToolDefinition(
            name="get_product_analytics",
            description="Generate product performance metrics and analytics",
            parameters=[
                ToolParameter(name="product", type="string", description="Specific product name", required=False),
                ToolParameter(name="category", type="string", description="Product category", required=False),
                ToolParameter(name="metric", type="string", description="Metric type (sales, views, conversion)", required=False, default="sales"),
                ToolParameter(name="period", type="string", description="Time period (week, month, quarter, year)", required=False, default="month")
            ],
            examples=[
                "get_product_analytics(category='Electronics', metric='sales')",
                "get_product_analytics(product='iPhone 15 Pro', period='quarter')"
            ]
        ),
        ToolDefinition(
            name="get_revenue_report",
            description="Create comprehensive revenue analysis reports",
            parameters=[
                ToolParameter(name="start_date", type="date", description="Report start date", required=False),
                ToolParameter(name="end_date", type="date", description="Report end date", required=False),
                ToolParameter(name="group_by", type="string", description="Group by category, product, or customer", required=False, default="category"),
                ToolParameter(name="include_trends", type="boolean", description="Include trend analysis", required=False, default=True)
            ],
            examples=[
                "get_revenue_report(start_date='2024-01-01', end_date='2024-03-31')",
                "get_revenue_report(group_by='product', include_trends=True)"
            ]
        )
    ]
    
    return ToolsListResponse(tools=tools)


@router.post("/execute")
async def execute_tool(tool_name: str, parameters: dict = None):
    """Execute a specific tool (mock implementation for prototype)"""
    if parameters is None:
        parameters = {}
    
    return {
        "tool": tool_name,
        "parameters": parameters,
        "result": "Mock execution result - this will be implemented with the tool registry",
        "execution_time_ms": 150,
        "success": True
    }