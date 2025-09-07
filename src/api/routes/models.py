from fastapi import APIRouter, HTTPException
from src.models.api import ModelsStatusResponse, ModelStatus, SystemResources
from src.services.real_model_manager import real_model_manager as model_manager
import psutil
from datetime import datetime

router = APIRouter()


@router.get("/status", response_model=ModelsStatusResponse)
async def get_models_status():
    """Get status of all available AI models"""
    try:
        memory = psutil.virtual_memory()
        
        # Get model status from model manager
        model_status_data = model_manager.get_model_status()
        
        models = []
        for model_data in model_status_data["models"]:
            models.append(ModelStatus(
                name=model_data["name"],
                status=model_data["status"],
                memory_usage=model_data.get("memory_usage"),
                load_time=model_data.get("load_time"),
                last_used=datetime.fromisoformat(model_data["last_used"]) if model_data.get("last_used") else None
            ))
        
        system_resources = SystemResources(
            total_memory=f"{memory.total / (1024**3):.1f}GB",
            available_memory=f"{memory.available / (1024**3):.1f}GB",
            gpu_memory="N/A",  # Could be enhanced to detect GPU
            gpu_utilization="N/A"
        )
        
        return ModelsStatusResponse(
            models=models,
            active_model=model_status_data["active_model"],
            system_resources=system_resources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model status: {str(e)}")


@router.post("/load/{model_name}")
async def load_model(model_name: str):
    """Load a specific model"""
    # Get available models from the model manager
    model_status = model_manager.get_model_status()
    valid_models = [m["name"] for m in model_status["models"]]
    
    if model_name not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model name. Available models: {valid_models}")
    
    try:
        success = model_manager.load_model(model_name)
        if success:
            return {
                "message": f"Model {model_name} loaded successfully",
                "status": "loaded",
                "active_model": model_manager.active_model
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to load model {model_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading model: {str(e)}")


@router.delete("/unload/{model_name}")
async def unload_model(model_name: str):
    """Unload a specific model"""
    try:
        success = model_manager.unload_model(model_name)
        if success:
            return {
                "message": f"Model {model_name} unloaded successfully",
                "status": "unloaded",
                "active_model": model_manager.active_model
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to unload model {model_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error unloading model: {str(e)}")