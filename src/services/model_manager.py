import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from src.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages AI model lifecycle and inference"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.active_model: Optional[str] = None
        self.model_stats: Dict[str, Dict] = {}
        self.load_lock = threading.Lock()
        self._initialize_model_stats()
    
    def _initialize_model_stats(self):
        """Initialize model statistics"""
        available_models = ["llama3-7b", "mistral-7b", "phi-3-mini"]
        for model_name in available_models:
            self.model_stats[model_name] = {
                "status": "available",
                "load_time": None,
                "last_used": None,
                "total_queries": 0,
                "total_inference_time": 0,
                "error_count": 0,
                "memory_usage": None
            }
    
    def load_model(self, model_name: str) -> bool:
        """Load a specific model"""
        with self.load_lock:
            try:
                if model_name in self.models:
                    logger.info(f"Model {model_name} already loaded")
                    self.active_model = model_name
                    return True
                
                logger.info(f"Loading model {model_name}...")
                start_time = time.time()
                
                # For prototype, we'll use a mock model
                # In production, this would load the actual model using llama-cpp-python
                mock_model = MockModel(model_name)
                
                load_time = time.time() - start_time
                
                self.models[model_name] = mock_model
                self.active_model = model_name
                self.model_stats[model_name].update({
                    "status": "loaded",
                    "load_time": f"{load_time:.1f}s",
                    "memory_usage": "2.5GB"  # Mock value
                })
                
                logger.info(f"Model {model_name} loaded successfully in {load_time:.1f}s")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                self.model_stats[model_name].update({
                    "status": "error",
                    "error_count": self.model_stats[model_name]["error_count"] + 1
                })
                return False
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a specific model"""
        with self.load_lock:
            try:
                if model_name not in self.models:
                    logger.warning(f"Model {model_name} not loaded")
                    return True
                
                del self.models[model_name]
                if self.active_model == model_name:
                    self.active_model = None
                
                self.model_stats[model_name].update({
                    "status": "available",
                    "memory_usage": None
                })
                
                logger.info(f"Model {model_name} unloaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unload model {model_name}: {e}")
                return False
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        return {
            "models": [
                {
                    "name": name,
                    **stats,
                    "last_used": stats["last_used"].isoformat() if stats["last_used"] else None
                }
                for name, stats in self.model_stats.items()
            ],
            "active_model": self.active_model,
            "total_loaded": len(self.models)
        }
    
    def inference(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Run inference on the active model"""
        if not self.active_model or self.active_model not in self.models:
            raise RuntimeError("No model loaded for inference")
        
        start_time = time.time()
        
        try:
            model = self.models[self.active_model]
            response = model.generate(prompt, max_tokens, temperature)
            
            inference_time = time.time() - start_time
            
            # Update statistics
            self.model_stats[self.active_model].update({
                "last_used": datetime.utcnow(),
                "total_queries": self.model_stats[self.active_model]["total_queries"] + 1,
                "total_inference_time": self.model_stats[self.active_model]["total_inference_time"] + inference_time
            })
            
            return response
            
        except Exception as e:
            self.model_stats[self.active_model]["error_count"] += 1
            logger.error(f"Inference error: {e}")
            raise
    
    def get_best_model_for_query(self, query: str) -> str:
        """Select the best model based on query complexity"""
        # Simple heuristic for prototype
        if len(query) > 200:
            return "llama3-7b"  # Complex queries
        elif any(word in query.lower() for word in ['analyze', 'compare', 'trend', 'insight']):
            return "mistral-7b"  # Analytical queries
        else:
            return "phi-3-mini"  # Simple queries
    
    def cleanup_unused_models(self, max_idle_time: int = 3600):
        """Unload models that haven't been used for a while"""
        with self.load_lock:
            current_time = datetime.utcnow()
            to_unload = []
            
            for model_name, stats in self.model_stats.items():
                if (stats["status"] == "loaded" and 
                    stats["last_used"] and
                    (current_time - stats["last_used"]).total_seconds() > max_idle_time):
                    to_unload.append(model_name)
            
            for model_name in to_unload:
                self.unload_model(model_name)
                logger.info(f"Auto-unloaded idle model: {model_name}")


class MockModel:
    """Mock model implementation for prototype"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.context_size = settings.MODEL_CONTEXT_SIZE
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Mock text generation"""
        # Simulate processing time
        time.sleep(0.5)  # 500ms mock inference time
        
        # Return mock responses based on prompt content
        if "sales" in prompt.lower():
            return "Based on the sales data analysis, your total revenue for the requested period is $15,432 with 324 units sold across various product categories."
        elif "inventory" in prompt.lower():
            return "Current inventory analysis shows 15 products below reorder levels, with Red Cotton T-Shirt being the most critical at 8 units remaining."
        elif "customer" in prompt.lower():
            return "Customer analysis reveals John Doe as your top customer with $2,500 in purchases, followed by Jane Smith with $1,800."
        elif "order" in prompt.lower():
            return "Order status summary: 25 pending, 15 processing, 45 shipped, and 78 fulfilled orders in the current period."
        else:
            return "I can help you analyze your e-commerce data including sales, inventory, customers, and orders. Please provide more specific information about what you'd like to know."


# Global model manager instance
model_manager = ModelManager()