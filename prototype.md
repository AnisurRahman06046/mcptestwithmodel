# E-commerce MCP Server Prototype - Project Documentation

## Project Description

This prototype implements a local Model Context Protocol (MCP) server that enables testing of natural language queries for e-commerce data using mock data. The solution runs entirely locally, leveraging local AI models (Llama 3, Mistral, Phi-3) to process queries and retrieve data from a mock e-commerce database. The prototype is designed for testing via Postman, allowing developers to send prompts and receive responses without requiring access to the actual platform backend.

### Key Objectives
- Create a functional MCP server prototype with local AI models
- Implement mock e-commerce database for testing
- Enable query testing via Postman without backend dependencies
- Validate natural language processing capabilities
- Demonstrate tool execution and data retrieval
- Provide a foundation for full integration with the platform

### Prototype Scope
- Single-server implementation
- Mock data for products, orders, customers, and inventory
- HTTP-based API for Postman testing (WebSocket/SSE not included in prototype)
- Local model inference using quantized models
- Basic authentication simulation
- Simple response formatting

---

## Requirement Analysis

### Functional Requirements

#### Query Processing
- **FR1**: Accept natural language queries via HTTP POST endpoint
- **FR2**: Process queries using local AI models
- **FR3**: Generate natural language responses based on mock data
- **FR4**: Support multiple query types (sales, inventory, customers, orders)
- **FR5**: Return structured responses in JSON format

#### Model Management
- **FR6**: Support at least one local AI model (Llama 3 recommended)
- **FR7**: Load model on server startup
- **FR8**: Provide fallback to smaller model if primary fails
- **FR9**: Support model switching via configuration

#### Mock Data Access
- **FR10**: Implement mock database with sample e-commerce data
- **FR11**: Define tools for accessing mock data:
  - `get_sales_data(product, period)`
  - `get_inventory_status(product)`
  - `get_customer_info(customer_id)`
  - `get_order_details(order_id)`
- **FR12**: Enforce mock data permissions (all data accessible in prototype)

#### API Interface
- **FR13**: Provide HTTP POST endpoint `/query`
- **FR14**: Accept JSON payload with prompt and context
- **FR15**: Return JSON response with answer and structured data
- **FR16**: Include mock authentication headers for testing

#### Error Handling
- **FR17**: Handle model loading errors gracefully
- **FR18**: Return meaningful error messages for invalid queries
- **FR19**: Validate request format and parameters
- **FR20**: Log errors for debugging

### Non-Functional Requirements

#### Performance
- **NFR1**: Simple query response time < 5 seconds
- **NFR2**: Model loading time < 60 seconds
- **NFR3**: Support 5 concurrent requests without degradation
- **NFR4**: Memory usage < 8GB during operation

#### Reliability
- **NFR5**: System uptime > 95% during testing
- **NFR6**: Graceful error handling with recovery
- **NFR7**: No crashes during normal operation
- **NFR8**: Consistent responses for identical queries

#### Usability
- **NFR9**: Simple API interface for Postman testing
- **NFR10**: Clear error messages
- **NFR11**: Consistent response format
- **NFR12**: Easy configuration of models and data

#### Security
- **NFR13**: No external API calls
- **NFR14**: Input sanitization for queries
- **NFR15**: Mock authentication simulation
- **NFR16**: No sensitive data in responses

---

## Project Breakdown

### Phase 1: Prototype Setup (Days 1-2)

#### 1.1 Environment Preparation
**Tasks:**
- Install Python 3.9+ and required packages
- Set up local inference environment (llama.cpp or Ollama)
- Download quantized Llama 3 model (7B-Q4_K_M recommended)
- Create project structure with proper directory layout
- Configure development environment and dependencies

**Deliverable**: Development environment ready with all dependencies installed

**Estimated Time**: 4-6 hours

#### 1.2 Mock Database Implementation
**Tasks:**
- Create SQLite database with comprehensive e-commerce schema
- Implement data models using SQLAlchemy
- Populate database with realistic sample data:
  - 50 products across 5 categories (Electronics, Clothing, Books, Home & Garden, Sports)
  - 200 orders with varying statuses and dates
  - 100 customers with detailed profiles and purchase history
  - Inventory levels for all products with realistic stock levels
- Create database seeding scripts for consistent test data
- Implement database connection and basic CRUD operations

**Deliverable**: Mock database with comprehensive sample data and access layer

**Estimated Time**: 6-8 hours

#### 1.3 Basic MCP Server
**Tasks:**
- Implement HTTP server using FastAPI for better performance and documentation
- Create project structure with proper separation of concerns
- Set up basic routing and middleware
- Implement request/response models using Pydantic
- Add comprehensive logging system with rotating logs
- Create health check endpoint
- Implement basic error handling middleware

**Deliverable**: Basic MCP server skeleton with proper architecture

**Estimated Time**: 4-6 hours

### Phase 2: Model Integration (Days 3-4)

#### 2.1 Model Manager
**Tasks:**
- Implement ModelManager class for handling AI model lifecycle
- Create model loading functionality with proper error handling
- Implement model inference interface with timeout handling
- Add model switching capability based on configuration
- Create model health monitoring
- Implement fallback mechanisms for model failures
- Add model resource monitoring (memory, GPU usage)

**Deliverable**: Robust model manager with error handling and monitoring

**Estimated Time**: 8-10 hours

#### 2.2 Tool Registry
**Tasks:**
- Design and implement ToolRegistry class
- Define core tools for mock data access:
  - `get_sales_data`: Retrieve sales information by product, date range, category
  - `get_inventory_status`: Check current stock levels and availability
  - `get_customer_info`: Access customer profiles and purchase history
  - `get_order_details`: Retrieve order information and status
  - `get_product_analytics`: Generate product performance metrics
  - `get_revenue_report`: Create revenue analysis reports
- Implement tool parameter validation and sanitization
- Create tool result formatting and standardization
- Add tool execution monitoring and logging
- Implement tool permission system for future expansion

**Deliverable**: Complete tool registry with all core e-commerce tools

**Estimated Time**: 6-8 hours

#### 2.3 Query Processing Pipeline
**Tasks:**
- Implement QueryProcessor class for handling end-to-end processing
- Create dynamic prompt generation system based on available tools
- Implement model response parsing and validation
- Add tool call detection and execution
- Create conversation context management
- Implement query intent classification
- Add response post-processing and formatting
- Create query performance monitoring

**Deliverable**: Complete query processing pipeline with context management

**Estimated Time**: 8-10 hours

### Phase 3: API Implementation (Days 5-6)

#### 3.1 API Endpoint Development
**Tasks:**
- Implement comprehensive `/query` endpoint with full functionality
- Add `/models/status` endpoint for model health monitoring
- Create `/tools/list` endpoint for available tools discovery
- Implement `/health` endpoint for system health checks
- Add comprehensive request validation using Pydantic models
- Create structured response formatting with consistent schema
- Implement proper HTTP status codes and error responses
- Add request rate limiting and timeout handling
- Create API versioning structure for future expansion

**Deliverable**: Complete REST API with all required endpoints

**Estimated Time**: 6-8 hours

#### 3.2 Mock Authentication
**Tasks:**
- Implement JWT-based mock authentication system
- Create user context simulation with different roles
- Add shop-level data isolation simulation
- Implement token validation middleware
- Create mock user database with different permission levels
- Add session management for testing scenarios
- Implement API key authentication as alternative
- Create authentication bypass for development mode

**Deliverable**: Comprehensive mock authentication system

**Estimated Time**: 4-6 hours

#### 3.3 Response Formatting
**Tasks:**
- Define comprehensive JSON response schemas
- Implement structured data inclusion with type safety
- Add metadata inclusion (execution time, model used, tools called)
- Create error message standardization
- Implement response compression for large datasets
- Add pagination support for large result sets
- Create response caching mechanism
- Implement performance metrics collection

**Deliverable**: Standardized response system with comprehensive formatting

**Estimated Time**: 4-6 hours

### Phase 4: Testing & Documentation (Days 7-8)

#### 4.1 Test Suite
**Tasks:**
- Create comprehensive unit tests for all components (>80% coverage)
- Implement integration tests for end-to-end workflows
- Add performance tests with load testing scenarios
- Create comprehensive Postman collection with all test cases
- Implement automated testing pipeline
- Add mock data validation tests
- Create model response validation tests
- Implement API contract testing

**Deliverable**: Complete test suite with automation and documentation

**Estimated Time**: 10-12 hours

#### 4.2 Documentation
**Tasks:**
- Create comprehensive API documentation with OpenAPI/Swagger
- Write detailed setup and installation instructions
- Document model configuration and switching procedures
- Create troubleshooting guide with common issues
- Write architecture documentation with diagrams
- Create developer guide for extending functionality
- Document all configuration options
- Create performance tuning guide

**Deliverable**: Complete documentation package

**Estimated Time**: 6-8 hours

#### 4.3 Demo Scripts and Validation
**Tasks:**
- Create comprehensive sample queries covering all use cases
- Implement automated data seeding and cleanup scripts
- Add performance monitoring and benchmarking tools
- Create demo presentation materials
- Implement system monitoring dashboard
- Create load testing scripts
- Add deployment verification scripts
- Create user acceptance testing scenarios

**Deliverable**: Complete demo and validation package

**Estimated Time**: 4-6 hours

---

## Technical Architecture

### System Components

#### 1. Core Application Layer
```
src/
├── main.py              # Application entry point
├── config/              # Configuration management
│   ├── settings.py      # Application settings
│   └── models.py        # Model configurations
├── api/                 # API endpoints
│   ├── routes/          # Route handlers
│   └── middleware/      # Custom middleware
├── services/            # Business logic
│   ├── query_processor.py
│   ├── model_manager.py
│   └── tool_registry.py
├── models/              # Data models
├── database/            # Database layer
└── utils/               # Utility functions
```

#### 2. Mock Database Schema
```sql
-- Products table with comprehensive attributes
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    description TEXT,
    sku TEXT UNIQUE,
    brand TEXT,
    weight REAL,
    dimensions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customers table with detailed profiles
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    total_orders INTEGER DEFAULT 0,
    total_spent REAL DEFAULT 0.0,
    loyalty_tier TEXT DEFAULT 'Bronze',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_purchase_date TIMESTAMP
);

-- Orders table with comprehensive tracking
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    total_amount REAL NOT NULL,
    shipping_address TEXT,
    payment_method TEXT,
    discount_applied REAL DEFAULT 0.0,
    shipping_cost REAL DEFAULT 0.0,
    notes TEXT,
    fulfilled_date TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Order items for detailed product tracking
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount REAL DEFAULT 0.0,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Inventory with detailed tracking
CREATE TABLE inventory (
    product_id INTEGER PRIMARY KEY,
    quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    max_stock_level INTEGER DEFAULT 1000,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    supplier TEXT,
    cost_per_unit REAL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Sales analytics view
CREATE VIEW sales_summary AS
SELECT 
    p.category,
    DATE(o.order_date) as sale_date,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.quantity * oi.unit_price) as total_revenue
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'fulfilled'
GROUP BY p.category, DATE(o.order_date);
```

#### 3. API Endpoint Specification

##### POST /query
Process natural language queries and return structured responses.

**Request Format:**
```json
{
  "query": "How many red shirts did we sell last week?",
  "context": {
    "user_id": "user_123",
    "shop_id": "shop_456",
    "timezone": "UTC",
    "currency": "USD"
  },
  "options": {
    "include_structured_data": true,
    "max_results": 50,
    "preferred_model": "llama3"
  }
}
```

**Response Format:**
```json
{
  "success": true,
  "response": "You sold 15 red shirts last week, generating $450 in revenue.",
  "structured_data": {
    "product": "red shirts",
    "period": {
      "start": "2024-01-15",
      "end": "2024-01-21"
    },
    "metrics": {
      "quantity": 15,
      "revenue": 450.00,
      "average_price": 30.00
    }
  },
  "metadata": {
    "model_used": "llama3-7b",
    "execution_time_ms": 3200,
    "tools_called": ["get_sales_data", "get_product_info"],
    "confidence_score": 0.95
  },
  "debug": {
    "query_intent": "sales_inquiry",
    "extracted_entities": ["red shirts", "last week"],
    "sql_queries": ["SELECT SUM(quantity)..."]
  }
}
```

##### GET /models/status
Check the status of available AI models.

**Response Format:**
```json
{
  "models": [
    {
      "name": "llama3-7b",
      "status": "loaded",
      "memory_usage": "6.2GB",
      "load_time": "45s",
      "last_used": "2024-01-22T10:30:00Z"
    },
    {
      "name": "mistral-7b",
      "status": "available",
      "estimated_load_time": "30s"
    }
  ],
  "active_model": "llama3-7b",
  "system_resources": {
    "total_memory": "16GB",
    "available_memory": "8.5GB",
    "gpu_memory": "12GB",
    "gpu_utilization": "75%"
  }
}
```

##### GET /tools/list
List all available tools and their capabilities.

**Response Format:**
```json
{
  "tools": [
    {
      "name": "get_sales_data",
      "description": "Retrieve sales data for products within specified time periods",
      "parameters": {
        "product": "string (optional)",
        "category": "string (optional)",
        "start_date": "date (optional)",
        "end_date": "date (optional)",
        "group_by": "enum [day, week, month, year]"
      },
      "examples": [
        "get_sales_data(product='red shirt', start_date='2024-01-01')"
      ]
    }
  ]
}
```

#### 4. Tool Definitions

##### Sales Analytics Tools
```python
def get_sales_data(
    product: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day"
) -> Dict[str, Any]:
    """
    Retrieve comprehensive sales data with flexible filtering.
    
    Args:
        product: Specific product name to filter
        category: Product category filter
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        group_by: Grouping period (day, week, month, year)
    
    Returns:
        Dictionary with sales metrics, trends, and breakdowns
    """
    # Implementation with database queries
    return {
        "total_quantity": 150,
        "total_revenue": 4500.00,
        "average_order_value": 30.00,
        "trend": "increasing",
        "breakdown": [
            {"period": "2024-01-15", "quantity": 25, "revenue": 750.00},
            {"period": "2024-01-16", "quantity": 30, "revenue": 900.00}
        ]
    }
```

##### Inventory Management Tools
```python
def get_inventory_status(
    product: Optional[str] = None,
    category: Optional[str] = None,
    low_stock_threshold: int = 10
) -> Dict[str, Any]:
    """
    Check current inventory levels with alerts for low stock.
    
    Args:
        product: Specific product to check
        category: Category filter
        low_stock_threshold: Threshold for low stock alerts
    
    Returns:
        Dictionary with inventory levels and stock alerts
    """
    return {
        "total_products": 50,
        "low_stock_items": [
            {
                "product": "Red Shirt - Medium",
                "current_stock": 5,
                "reorder_level": 10,
                "status": "low_stock"
            }
        ],
        "out_of_stock_items": [],
        "total_value": 125000.00
    }
```

##### Customer Analytics Tools
```python
def get_customer_info(
    customer_id: Optional[str] = None,
    email: Optional[str] = None,
    include_orders: bool = True
) -> Dict[str, Any]:
    """
    Retrieve customer information and purchase history.
    
    Args:
        customer_id: Specific customer ID
        email: Customer email address
        include_orders: Include order history
    
    Returns:
        Dictionary with customer profile and analytics
    """
    return {
        "customer": {
            "id": "cust_123",
            "name": "John Doe",
            "email": "john@example.com",
            "total_orders": 15,
            "total_spent": 2500.00,
            "loyalty_tier": "Gold",
            "avg_order_value": 166.67
        },
        "recent_orders": [] if not include_orders else [
            {
                "order_id": "ord_456",
                "date": "2024-01-20",
                "total": 85.00,
                "status": "fulfilled"
            }
        ]
    }
```

### Sample Test Queries for Postman

#### Sales Queries
```json
{
  "query": "What were our total sales last month?",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "Show me the best selling products in the electronics category",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "Compare sales between Q1 and Q2 this year",
  "context": {"shop_id": "shop_123"}
}
```

#### Inventory Queries
```json
{
  "query": "Which products are running low on stock?",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "What's the current inventory value?",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "Show me products that need reordering",
  "context": {"shop_id": "shop_123"}
}
```

#### Customer Queries
```json
{
  "query": "Who are my top 10 customers by total spending?",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "How many new customers did we acquire last month?",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "Show me customers who haven't ordered in the last 90 days",
  "context": {"shop_id": "shop_123"}
}
```

#### Complex Analytics Queries
```json
{
  "query": "What's the profit margin for each product category?",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "Analyze seasonal trends for clothing products",
  "context": {"shop_id": "shop_123"}
}

{
  "query": "Which marketing campaigns generated the highest ROI?",
  "context": {"shop_id": "shop_123"}
}
```

## Success Metrics

### Functional Success Criteria
- **Query Processing**: 100% of sample queries return valid, contextually appropriate responses
- **Tool Execution**: All tools execute correctly and return properly formatted data
- **Model Integration**: Model switching works seamlessly based on configuration
- **Data Accuracy**: All mock data queries return consistent, realistic results
- **Error Handling**: Graceful handling of invalid queries, malformed requests, and system errors

### Performance Benchmarks
- **Response Time**: Average query response time < 5 seconds for simple queries, < 10 seconds for complex queries
- **Model Loading**: Initial model loading completes in < 60 seconds
- **Memory Usage**: Total system memory usage < 8GB during normal operation
- **Concurrent Requests**: Support for 5 concurrent requests without performance degradation
- **Throughput**: Process minimum 50 queries per hour continuously

### Reliability Metrics
- **Uptime**: System maintains > 95% uptime during testing periods
- **Error Rate**: < 5% error rate for valid queries
- **Crash Recovery**: System recovers gracefully from model failures or timeouts
- **Data Consistency**: Identical queries return consistent results across multiple requests

### Usability Standards
- **API Clarity**: Postman collection executes without manual intervention
- **Error Messages**: All error responses include actionable information
- **Documentation**: Complete API documentation with examples
- **Response Format**: Consistent JSON schema across all endpoints

## Hardware and Software Requirements

### Development Environment
| Component | Minimum | Recommended | Optimal |
|-----------|---------|-------------|---------|
| **CPU** | 4-core Intel i5 | 8-core Intel i7 | 16-core AMD Ryzen 9 |
| **RAM** | 8GB | 16GB | 32GB |
| **GPU** | Not required | RTX 3060 (12GB) | RTX 4080 (16GB) |
| **Storage** | 20GB SSD | 50GB NVMe SSD | 100GB NVMe SSD |
| **Network** | 1 Mbps | 10 Mbps | 100 Mbps |

### Software Dependencies
- **Operating System**: Linux (Ubuntu 20.04+), macOS (Big Sur+), or Windows 10/11
- **Python**: 3.9+ with pip package manager
- **Database**: SQLite 3.36+ (included with Python)
- **Model Runtime**: llama.cpp or Ollama for local inference
- **Testing**: Postman application for API testing
- **Development**: Git for version control, VS Code or PyCharm for development

### Python Package Requirements
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
llama-cpp-python==0.2.18
numpy==1.24.3
pandas==2.0.3
pytest==7.4.3
pytest-cov==4.1.0
httpx==0.25.2
```

## Risk Assessment and Mitigation

### Technical Risks
1. **Model Loading Failures**
   - Risk: AI models fail to load due to memory constraints or corruption
   - Mitigation: Implement fallback models, memory monitoring, and model validation

2. **Performance Degradation**
   - Risk: Response times exceed acceptable limits under load
   - Mitigation: Implement query caching, model warm-up, and resource monitoring

3. **Data Inconsistency**
   - Risk: Mock data becomes inconsistent or corrupted during testing
   - Mitigation: Implement data validation, automated seeding, and backup procedures

### Operational Risks
1. **Environment Setup Issues**
   - Risk: Developers struggle with complex environment setup
   - Mitigation: Provide Docker containers, automated setup scripts, and detailed documentation

2. **Testing Complexity**
   - Risk: Testing procedures become too complex for effective validation
   - Mitigation: Create simplified Postman collections, automated test suites, and clear test scenarios

3. **Integration Challenges**
   - Risk: Prototype doesn't translate well to production integration
   - Mitigation: Design architecture with production patterns, document integration points, and create migration guides

## Future Expansion Roadmap

### Phase 2 Enhancements (Post-Prototype)
- **Multi-Model Support**: Implement dynamic model selection based on query complexity
- **Real-time Updates**: Add WebSocket support for real-time query processing
- **Advanced Analytics**: Implement machine learning-based trend analysis
- **Caching Layer**: Add Redis-based caching for improved performance

### Phase 3 Production Features
- **Scalability**: Implement horizontal scaling and load balancing
- **Security**: Add comprehensive authentication and authorization
- **Monitoring**: Implement APM and business intelligence dashboards
- **Multi-tenancy**: Support multiple shops with data isolation

### Integration Considerations
- **Database Migration**: Strategies for transitioning from SQLite to production databases
- **Authentication Integration**: Connecting with existing platform authentication systems
- **API Gateway**: Implementing rate limiting, throttling, and API versioning
- **Deployment**: Containerization and orchestration for production environments

This comprehensive prototype documentation provides a solid foundation for developing and testing the e-commerce MCP server with clear objectives, detailed technical specifications, and practical implementation guidance.