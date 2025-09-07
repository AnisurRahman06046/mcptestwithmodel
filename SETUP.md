# E-commerce MCP Server Prototype - Setup Guide

## Prerequisites

### System Requirements
- Python 3.9 or higher
- pip package manager
- 8GB+ RAM (recommended)
- 20GB+ free disk space

### Operating System Support
- Linux (Ubuntu 20.04+ recommended)
- macOS (Big Sur+)
- Windows 10/11 with WSL2

## Installation Steps

### 1. Clone and Navigate to Project
```bash
cd /path/to/project/test
```

### 2. Create Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment
```bash
cp .env.example .env
# Edit .env file with your preferred settings
```

### 5. Initialize Database
The database will be automatically created and seeded when you first run the server.

## Running the Server

### Development Mode
```bash
python main.py
```

### Alternative Method
```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

### Server Access
- **Main Server**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health

## Testing the Prototype

### 1. Import Postman Collection
- Open Postman
- Import the file: `postman/ecommerce-mcp-server.postman_collection.json`
- Set the base_url variable to: `http://127.0.0.1:8000`

### 2. Run Basic Tests
```bash
# Run unit tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_api.py -v
```

### 3. Sample API Calls

#### Health Check
```bash
curl -X GET "http://127.0.0.1:8000/health"
```

#### Sales Query
```bash
curl -X POST "http://127.0.0.1:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What were our sales last month?",
       "context": {
         "user_id": "test_user",
         "shop_id": "test_shop"
       }
     }'
```

#### Load AI Model
```bash
curl -X POST "http://127.0.0.1:8000/models/load/llama3-7b"
```

## Expected Behavior

### 1. Server Startup
When you run the server, you should see:
```
INFO:     Starting E-commerce MCP Server...
INFO:     Database tables created successfully
INFO:     Starting database seeding...
INFO:     Created 50 products
INFO:     Created 100 customers
INFO:     Created 200 orders
INFO:     Database seeding completed successfully
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2. Database Creation
- SQLite database will be created at `data/database/ecommerce.db`
- Sample data will be populated automatically
- 50 products across 5 categories
- 100 mock customers
- 200 mock orders

### 3. Query Processing
Sample queries that should work:
- "What were our sales last month?"
- "Which products are running low on stock?"
- "Who are my top customers?"
- "How many pending orders do I have?"
- "Analyze electronics category performance"

### 4. Model Management
- Models are mocked in prototype (no actual AI model files needed)
- Loading/unloading simulates real model management
- Status tracking works correctly

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000
# Kill the process
kill -9 <PID>
```

#### Database Issues
```bash
# Delete and recreate database
rm -f data/database/ecommerce.db
# Restart server to recreate
```

#### Module Import Errors
```bash
# Ensure you're in the right directory and virtual environment
pwd
which python
# Reinstall dependencies
pip install -r requirements.txt
```

#### Memory Issues
- Reduce MOCK_*_COUNT values in .env
- Close other applications
- Use a machine with more RAM

### Logs Location
- Application logs: `logs/app.log`
- Console output shows real-time information

### Performance Expectations
- Simple queries: < 2 seconds
- Complex queries: < 5 seconds
- Model loading: < 10 seconds (mocked)
- Database queries: < 500ms

## Development Notes

### Adding New Tools
1. Add tool function to `src/services/tool_registry.py`
2. Update tool definitions in `src/api/routes/tools.py`
3. Add tool selection logic in `src/services/query_processor.py`

### Modifying Mock Data
- Edit `src/database/seed_data.py`
- Delete database file and restart server
- Or adjust quantities in `.env` file

### Extending Query Processing
- Update intent patterns in `src/services/query_processor.py`
- Add new entity extraction rules
- Modify tool selection logic

### API Documentation
- FastAPI automatically generates docs at `/docs`
- Swagger UI available at `/docs`
- ReDoc available at `/redoc`

## Production Considerations

This is a prototype. For production deployment:

1. **Replace Mock Models**: Integrate real AI models (llama.cpp, Ollama)
2. **Database**: Migrate to PostgreSQL or MySQL
3. **Authentication**: Implement real JWT authentication
4. **Caching**: Add Redis for query caching
5. **Monitoring**: Add APM and logging solutions
6. **Security**: Implement rate limiting, input validation
7. **Scaling**: Add load balancing, container orchestration

## Support

For issues or questions:
1. Check this setup guide
2. Review the logs in `logs/app.log`
3. Test with the provided Postman collection
4. Verify all dependencies are installed correctly