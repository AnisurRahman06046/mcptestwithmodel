from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.models.api import HealthCheck
from src.database import get_db
from src.services.real_model_manager import real_model_manager as model_manager
from src.config import settings
import time
import psutil
from datetime import datetime

router = APIRouter()

# Store start time for uptime calculation
start_time = time.time()


@router.get("/", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        database_connected = True
    except Exception:
        database_connected = False
    
    uptime = time.time() - start_time
    model_loaded = model_manager.active_model is not None
    
    return HealthCheck(
        status="healthy" if database_connected else "degraded",
        timestamp=datetime.utcnow(),
        uptime=uptime,
        database_connected=database_connected,
        model_loaded=model_loaded,
        version="1.0.0"
    )


@router.get("/system")
async def system_info():
    """System resource information"""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage_percent": cpu_percent,
            "memory": {
                "total": f"{memory.total / (1024**3):.1f}GB",
                "available": f"{memory.available / (1024**3):.1f}GB",
                "used_percent": memory.percent
            },
            "disk": {
                "total": f"{disk.total / (1024**3):.1f}GB",
                "free": f"{disk.free / (1024**3):.1f}GB",
                "used_percent": (disk.used / disk.total) * 100
            }
        }
    except Exception as e:
        return {"error": f"Unable to get system info: {str(e)}"}