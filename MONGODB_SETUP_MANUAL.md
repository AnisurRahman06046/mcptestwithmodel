# MongoDB E-commerce MCP Server - Developer Manual

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [MongoDB Setup](#mongodb-setup)
3. [Installation Guide](#installation-guide)
4. [Configuration](#configuration)
5. [Running the Server](#running-the-server)
6. [Database Management](#database-management)
7. [API Usage](#api-usage)
8. [Troubleshooting](#troubleshooting)
9. [Development Workflow](#development-workflow)
10. [Production Deployment](#production-deployment)

---

## 🏗️ Architecture Overview

### **Clean Architecture Structure**
```
src/
├── core/                    # Application core logic
│   ├── events.py           # FastAPI lifespan events
│   └── startup.py          # Startup orchestration
├── database/               # Database layer
│   ├── mongodb.py          # MongoDB connection & client
│   ├── manager.py          # Database lifecycle management
│   ├── seeder.py           # Sample data seeding
│   └── connection.py       # Compatibility layer
├── models/                 # Data models
│   ├── mongodb_models.py   # MongoDB document models (UUID-based)
│   └── api.py              # API request/response models
├── services/               # Business logic
│   ├── tool_registry.py    # MongoDB data access tools
│   ├── query_processor.py  # Natural language processing
│   └── real_model_manager.py # AI model management
└── api/                    # API layer
    └── routes/             # API endpoints
```

### **Key Components**
- **MongoDB Atlas**: Cloud database with connection pooling
- **AsyncMongoClient**: Modern async MongoDB operations
- **UUID Primary Keys**: Clean, scalable document IDs
- **Pydantic Models**: Type-safe data validation
- **Clean Architecture**: Separated concerns and dependencies

---

## 🔧 MongoDB Setup

### **1. MongoDB Atlas Configuration**
```bash
# Environment variables
ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net
DB_NAME=your_database_name
```

### **2. Database Collections**
The system uses 4 main collections:
- `products` - Product catalog
- `customers` - Customer information
- `orders` - Order history with embedded items
- `inventory` - Stock levels and supplier info

### **3. Document Schema (UUID-based)**
```python
# Example Product document
{
  "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
  "name": "MacBook Pro",
  "category": "Electronics", 
  "price": 1299.99,
  "sku": "APPLE-MBP-M2-13",
  "created_at": "2025-01-01T10:00:00Z"
}
```

---

## 🚀 Installation Guide

### **Prerequisites**
- Python 3.9+
- MongoDB Atlas account
- Virtual environment

### **Step 1: Clone and Setup**
```bash
git clone <repository-url>
cd test
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### **Step 2: Install Dependencies**
```bash
pip install -r requirements.txt
pip install 'pymongo[srv]>=4.14.0'  # Latest PyMongo with async support
pip install pydantic[email]         # Email validation
```

### **Step 3: Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your MongoDB Atlas credentials
```

### **Required Dependencies**
```
pymongo[srv]>=4.14.0    # MongoDB driver with async support
pydantic[email]>=2.5.0  # Data validation with email support
fastapi>=0.104.1        # Web framework
uvicorn>=0.24.0         # ASGI server
faker>=21.0.0           # Sample data generation
```

---

## ⚙️ Configuration

### **.env File Structure**
```env
# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# MongoDB Configuration
ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net
DB_NAME=your_database_name

# Performance Settings
MONGODB_MIN_POOL_SIZE=1
MONGODB_MAX_POOL_SIZE=10
MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
MONGODB_CONNECT_TIMEOUT_MS=10000

# Mock Data Settings
SEED_DATABASE=true
MOCK_USER_COUNT=100
MOCK_PRODUCT_COUNT=50
MOCK_ORDER_COUNT=200

# Model Configuration
MODEL_PATH=./data/models
DEFAULT_MODEL=llama3-7b
```

### **MongoDB Connection Settings**
```python
# Production-ready connection pooling
mongodb_client = AsyncMongoClient(
    settings.ATLAS_URI,
    minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
    maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
    serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    retryWrites=True,
    retryReads=True
)
```

---

## 🏃 Running the Server

### **Development Server**
```bash
# Method 1: Using uvicorn directly (recommended)
.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# Method 2: Using main.py wrapper
.venv/bin/python main.py
```

### **Server Startup Logs**
```
🚀 Starting E-commerce MCP Server
📊 Server Configuration:
   - Host: 127.0.0.1:8000
   - Debug Mode: True
   - Log Level: INFO
🔌 Connecting to MongoDB Atlas...
✅ Database connection established successfully!
📦 Connected to database: your_database_name
🌱 Seeding database with mock data...
✅ Database seeded successfully!
🎉 E-commerce MCP Server started successfully!
📖 API Documentation: http://127.0.0.1:8000/docs
```

### **Verify Installation**
```bash
# Health check
curl -X GET "http://127.0.0.1:8000/health/"

# Expected response:
{
  "status": "healthy",
  "database_connected": true,
  "model_loaded": false,
  "uptime": 45.2,
  "version": "1.0.0"
}
```

---

## 🗄️ Database Management

### **MongoDB Client Access**
```python
from src.database.mongodb import mongodb_client

# Get database instance
db = mongodb_client.database

# Collection operations
products = await db.products.find({}).to_list(length=10)
customer = await db.customers.find_one({"email": "user@example.com"})
```

### **Seeding Database**
```python
from src.database.seeder import mongodb_seeder

# Seed all collections
await mongodb_seeder.seed_all()

# Clear all data (for re-seeding)
await mongodb_seeder.clear_all_data()
```

### **Manual Data Operations**
```python
# Insert product
product = Product(
    name="New Product",
    category="Electronics",
    price=299.99,
    sku="NEW-PROD-001"
)
await db.products.insert_one(product.dict(by_alias=True))

# Query with aggregation
pipeline = [
    {"$match": {"category": "Electronics"}},
    {"$group": {"_id": "$category", "avg_price": {"$avg": "$price"}}}
]
result = await db.products.aggregate(pipeline).to_list(length=10)
```

---

## 🔌 API Usage

### **Available Endpoints**
```
GET  /                    # Server info
GET  /health/            # Health check
GET  /docs               # API documentation
POST /query              # Natural language queries
GET  /models/status      # AI model status
POST /models/load/{name} # Load AI model
GET  /tools/list         # Available tools
```

### **Query Examples**
```bash
# Sales query
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What were our total sales last month?"}'

# Inventory query
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which products are running low on stock?"}'

# Customer query
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Who are my top 5 customers by spending?"}'
```

### **Sample Response Structure**
```json
{
  "success": true,
  "response": "Based on your data, you have 15 products with low stock levels...",
  "structured_data": {
    "results": [
      {
        "product_name": "MacBook Pro",
        "current_stock": 3,
        "reorder_level": 10
      }
    ]
  },
  "metadata": {
    "execution_time_ms": 245,
    "tools_called": ["get_inventory_status"],
    "confidence_score": 0.92
  }
}
```

---

## 🔧 Troubleshooting

### **Common Issues & Solutions**

#### **1. MongoDB Connection Issues**
```bash
# Error: ServerSelectionTimeoutError
# Solution: Check Atlas URI and network connectivity
curl -X GET "https://httpbin.org/ip"  # Test internet connection
```

#### **2. PyMongo Async Import Error**
```bash
# Error: cannot import name 'AsyncMongoClient'
# Solution: Update PyMongo to latest version
pip install --upgrade 'pymongo[srv]>=4.14.0'
```

#### **3. Email Validator Missing**
```bash
# Error: email-validator is not installed
# Solution: Install email validation
pip install pydantic[email]
```

#### **4. Virtual Environment Issues**
```bash
# Activate virtual environment first
source .venv/bin/activate

# Verify Python path
which python
# Should show: /path/to/project/.venv/bin/python
```

#### **5. Port Already in Use**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn src.main:app --port 8001
```

### **Debug Mode**
```python
# Enable debug logging
LOG_LEVEL=DEBUG

# Check MongoDB connection manually
python -c "
import asyncio
from src.database.mongodb import mongodb_client
asyncio.run(mongodb_client.connect())
"
```

### **Database Connection Testing**
```bash
# Test MongoDB connection
python -c "
import asyncio
from src.database.mongodb import mongodb_client

async def test():
    success = await mongodb_client.connect()
    if success:
        health = await mongodb_client.health_check()
        print(f'Status: {health}')
    await mongodb_client.disconnect()

asyncio.run(test())
"
```

---

## 👨‍💻 Development Workflow

### **Adding New Features**

#### **1. Create New Tool**
```python
# In src/services/tool_registry.py
async def get_new_analytics(self, db, parameter: str) -> Dict[str, Any]:
    # MongoDB aggregation pipeline
    pipeline = [
        {"$match": {"field": parameter}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    cursor = db.collection.aggregate(pipeline)
    results = await cursor.to_list(length=100)
    return {"data": results}

# Register the tool
self.tools["get_new_analytics"] = self.get_new_analytics
```

#### **2. Add New Model**
```python
# In src/models/mongodb_models.py
class NewModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    name: str = Field(..., min_length=1, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        schema_extra = {"example": {"name": "Example"}}
```

#### **3. Database Migration**
```python
# Create migration script
async def migrate_add_new_field():
    db = mongodb_client.database
    await db.products.update_many(
        {},
        {"$set": {"new_field": "default_value"}}
    )
```

### **Testing Strategy**
```python
# Unit tests
pytest tests/unit/

# Integration tests with MongoDB
pytest tests/integration/

# API tests
pytest tests/api/
```

---

## 🚀 Production Deployment

### **Environment Setup**
```bash
# Production environment variables
DEBUG=false
LOG_LEVEL=INFO
SEED_DATABASE=false  # Don't seed in production

# MongoDB Atlas production cluster
ATLAS_URI=mongodb+srv://prod_user:secure_password@prod-cluster.mongodb.net
DB_NAME=production_db

# Connection pool for production
MONGODB_MIN_POOL_SIZE=5
MONGODB_MAX_POOL_SIZE=50
```

### **Docker Deployment**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY main.py .

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Performance Optimization**
```python
# Production MongoDB settings
mongodb_client = AsyncMongoClient(
    settings.ATLAS_URI,
    minPoolSize=10,
    maxPoolSize=100,
    maxIdleTimeMS=30000,
    compressors="zstd,zlib,snappy",  # Enable compression
    readPreference="secondaryPreferred"  # Read from secondaries
)
```

### **Monitoring**
```python
# Add monitoring endpoints
@app.get("/metrics")
async def get_metrics():
    return {
        "database_health": await mongodb_client.health_check(),
        "active_connections": mongodb_client.topology_description.servers,
        "memory_usage": psutil.virtual_memory().percent
    }
```

### **Security Checklist**
- ✅ Use MongoDB Atlas with authentication
- ✅ Enable SSL/TLS for all connections
- ✅ Set up IP whitelisting
- ✅ Use environment variables for secrets
- ✅ Enable audit logging
- ✅ Regular security updates

---

## 📚 Additional Resources

### **MongoDB Operations**
- [MongoDB Aggregation Pipeline](https://docs.mongodb.com/manual/aggregation/)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [MongoDB Atlas Setup](https://docs.atlas.mongodb.com/)

### **FastAPI Resources**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Models](https://pydantic-docs.helpmanual.io/)

### **Development Tools**
- MongoDB Compass - GUI for database management
- Postman Collection - API testing (included in `/postman/`)

---

## 🆘 Support & Contact

### **Getting Help**
1. Check this manual first
2. Review server logs in `logs/app.log`
3. Test MongoDB connection independently
4. Check API documentation at `/docs`

### **Common Commands Reference**
```bash
# Server management
.venv/bin/python -m uvicorn src.main:app --reload

# Database operations
python -c "from src.database.seeder import mongodb_seeder; import asyncio; asyncio.run(mongodb_seeder.clear_all_data())"

# Health check
curl -X GET "http://localhost:8000/health/"

# View logs
tail -f logs/app.log
```

---

**This manual covers the complete MongoDB E-commerce MCP Server setup and operation. Keep it updated as the system evolves!** 📖✨