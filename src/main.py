import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.config import settings
from src.core.events import lifespan, configure_startup_tasks, configure_shutdown_tasks
from src.api.routes import query, models, tools, health, sync, subscription, conversations, enhancement, chat
import uvicorn

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configure startup and shutdown tasks
configure_startup_tasks()
configure_shutdown_tasks()

# Create FastAPI app
app = FastAPI(
    title="E-commerce MCP Server",
    description="Local Model Context Protocol server for e-commerce data queries",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(query.router, prefix="", tags=["Query"])
app.include_router(subscription.router, prefix="", tags=["Subscription"])
app.include_router(conversations.router, prefix="", tags=["Conversations"])
app.include_router(models.router, prefix="/models", tags=["Models"])
app.include_router(tools.router, prefix="/tools", tags=["Tools"])
app.include_router(sync.router, prefix="/sync", tags=["Sync"])
app.include_router(enhancement.router, prefix="", tags=["Enhancement"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])


@app.get("/")
async def root():
    return {
        "message": "E-commerce MCP Server",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )