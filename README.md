# E-commerce Local MCP Server

A local Model Context Protocol (MCP) server that integrates with e-commerce platforms, enabling shop owners to query their business data using natural language through AI models running on local infrastructure.

## Overview

This project provides a secure, privacy-focused solution for e-commerce platforms to offer AI-powered data queries without sending sensitive business data to external services. The server leverages multiple local AI models (Llama 3, Mistral, Phi-3) to process natural language queries and retrieve data from e-commerce databases.

## Key Features

- **Natural Language Queries**: Shop owners can ask questions about their business data in plain English
- **Local AI Processing**: All AI inference happens locally for data privacy and cost efficiency
- **Multi-Model Support**: Dynamic selection between Llama 3, Mistral, and Phi-3 based on query complexity
- **Secure Data Access**: Role-based permissions with secure authentication integration
- **Real-time Responses**: Low-latency query processing for seamless user experience
- **Comprehensive Tools**: Built-in tools for sales reports, inventory checks, customer analytics, and order management

## Target Users

- E-commerce platform shop owners
- Platform administrators
- Customer support teams

## Architecture

### Core Components

1. **MCP Server Core**: Central request processing hub with FastAPI
2. **Model Management System**: Dynamic AI model lifecycle management
3. **Tool Registry**: Extensible data operation definitions
4. **Data Access Layer**: Secure database interface with permission enforcement
5. **Integration Layer**: Platform authentication and API gateway

### Technology Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **AI Inference**: llama.cpp, Ollama, CUDA
- **Database**: PostgreSQL
- **Caching**: Redis
- **Authentication**: JWT integration with existing platform

## Performance Targets

- Simple queries: < 3 seconds response time
- Complex queries: < 10 seconds response time
- System uptime: > 99.5%
- Concurrent users: 10+ without degradation
- Query accuracy: 90%+ for data retrieval

## Development Phases

### Phase 1: Foundation Setup (Weeks 1-2)
- Infrastructure preparation with GPU support
- MCP server core implementation
- Security framework establishment

### Phase 2: Core Functionality (Weeks 3-5)
- Model management system
- Tool registry development
- Query processing pipeline

### Phase 3: Integration & Testing (Weeks 6-7)
- API integration with chat UI
- Comprehensive testing suite
- Performance optimization

### Phase 4: Deployment & Documentation (Week 8)
- Production deployment
- Documentation and training
- Operational handover

## Security Features

- Token-based authentication validation
- Role-based access control
- Input sanitization and injection prevention
- Comprehensive audit logging
- Local data processing (no external API calls)
- Encrypted data transmission

## Quick Start

### Prerequisites

- Python 3.9+
- CUDA-capable GPU (recommended)
- PostgreSQL database
- Redis server
- Access to e-commerce platform database

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd test

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Initialize database
python scripts/init_db.py

# Download AI models
python scripts/download_models.py

# Start the server
python main.py
```

### Configuration

Edit the `.env` file with your specific configuration:

```env
DATABASE_URL=postgresql://user:password@localhost/ecommerce_db
REDIS_URL=redis://localhost:6379
PLATFORM_AUTH_URL=https://your-platform.com/auth
GPU_MEMORY_LIMIT=8192
MODEL_CACHE_DIR=./models
```

## Usage Examples

### Basic Queries

- "What were my sales last week?"
- "Show me low inventory items"
- "How many orders are pending?"
- "Which products are my top sellers this month?"

### Advanced Analytics

- "Compare this month's revenue to last month"
- "Show customer acquisition trends"
- "Analyze seasonal sales patterns"
- "Generate inventory turnover report"

## API Endpoints

### Chat Interface
- `POST /chat/query` - Process natural language query
- `GET /chat/history/{session_id}` - Retrieve conversation history
- `POST /chat/session` - Create new chat session

### Model Management
- `GET /models/status` - Check model availability
- `POST /models/load/{model_name}` - Load specific model
- `DELETE /models/unload/{model_name}` - Unload model

### Tools
- `GET /tools/list` - Available data tools
- `POST /tools/execute` - Execute specific tool

## Available Tools

1. **Sales Analytics**: Revenue reports, trend analysis, period comparisons
2. **Inventory Management**: Stock levels, low inventory alerts, reorder suggestions
3. **Customer Insights**: Customer analytics, segmentation, behavior patterns
4. **Order Management**: Order status, fulfillment tracking, shipping analytics
5. **Product Performance**: Best sellers, product analytics, category insights

## Monitoring and Maintenance

### Health Checks
- `GET /health` - System health status
- `GET /metrics` - Performance metrics
- `GET /models/health` - AI model status

### Logging
- Application logs: `logs/app.log`
- Query logs: `logs/queries.log`
- Security audit: `logs/security.log`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run performance tests
pytest tests/performance/

# Generate coverage report
pytest --cov=src tests/
```

## Deployment

### Production Deployment

1. Set up production environment with GPU support
2. Configure secure database connections
3. Set up SSL certificates
4. Configure monitoring and alerting
5. Deploy using Docker or direct installation

### Docker Deployment

```bash
# Build the image
docker build -t ecommerce-mcp-server .

# Run the container
docker run -d \
  --gpus all \
  -p 8000:8000 \
  -v ./data:/app/data \
  -v ./models:/app/models \
  --env-file .env \
  ecommerce-mcp-server
```

## Support

For technical issues and feature requests, please:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed description
4. Contact the development team

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.