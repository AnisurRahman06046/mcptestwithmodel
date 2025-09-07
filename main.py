#!/usr/bin/env python3
"""
E-commerce MCP Server Prototype
Main entry point for the application
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app
from src.config import settings
import uvicorn

if __name__ == "__main__":
    print("Starting E-commerce MCP Server Prototype...")
    print(f"Server will run on http://{settings.HOST}:{settings.PORT}")
    print(f"API Documentation available at http://{settings.HOST}:{settings.PORT}/docs")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )