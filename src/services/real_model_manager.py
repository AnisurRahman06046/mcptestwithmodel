import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from src.config import settings

logger = logging.getLogger(__name__)

# Try to import llama-cpp-python, fallback to mock if not available
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
    logger.info("llama-cpp-python available - using real models")
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama-cpp-python not available - falling back to mock models")


class RealModelManager:
    """Manages real AI model lifecycle and inference using llama-cpp-python"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.active_model: Optional[str] = None
        self.model_stats: Dict[str, Dict] = {}
        self.load_lock = threading.Lock()
        self.model_configs = self._get_model_configs()
        self._initialize_model_stats()
    
    def _get_model_configs(self) -> Dict[str, Dict]:
        """Get available model configurations"""
        return {
            "phi-3-mini": {
                "filename": "phi-3-mini-4k-instruct-q4.gguf",
                "context_size": 4096,
                "description": "Microsoft Phi-3 Mini - Lightweight and efficient",
                "n_gpu_layers": 35,  # GPU acceleration - will fallback to CPU if no GPU
                "temperature": 0.7
            },
            "llama3-8b": {
                "filename": "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                "context_size": 4096,  # Reduced context size for better performance
                "description": "Meta Llama 3 8B - High quality responses",
                "n_gpu_layers": 0,  # Use CPU only
                "temperature": 0.7
            },
            "gemma-2b": {
                "filename": "gemma-2b-it.q4_k_m.gguf",
                "context_size": 2048,
                "description": "Google Gemma 2B - Very lightweight",
                "n_gpu_layers": 15,
                "temperature": 0.8
            },
            "qwen2.5-3b": {
                "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
                "context_size": 4096,
                "description": "Qwen2.5 3B - Excellent reasoning and multilingual support",
                "n_gpu_layers": 0,  # CPU-only system
                "temperature": 0.7
            },
            "qwen2.5-1.5b": {
                "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
                "context_size": 2048,
                "description": "Qwen2.5 1.5B - Ultra-fast lightweight model",
                "n_gpu_layers": 0,  # CPU-only system
                "temperature": 0.7
            }
        }
    
    def _initialize_model_stats(self):
        """Initialize model statistics"""
        for model_name, config in self.model_configs.items():
            model_path = Path(settings.MODEL_PATH) / config["filename"]
            status = "available" if model_path.exists() else "not_found"
            
            self.model_stats[model_name] = {
                "status": status,
                "load_time": None,
                "last_used": None,
                "total_queries": 0,
                "total_inference_time": 0,
                "error_count": 0,
                "memory_usage": None,
                "model_path": str(model_path),
                "file_exists": model_path.exists(),
                "file_size_mb": round(model_path.stat().st_size / (1024*1024), 1) if model_path.exists() else 0
            }
    
    def load_model(self, model_name: str) -> bool:
        """Load a specific model"""
        with self.load_lock:
            try:
                if model_name not in self.model_configs:
                    logger.error(f"Unknown model: {model_name}")
                    return False
                
                if model_name in self.models:
                    logger.info(f"Model {model_name} already loaded")
                    self.active_model = model_name
                    return True
                
                # Check if model file exists
                config = self.model_configs[model_name]
                model_path = Path(settings.MODEL_PATH) / config["filename"]
                
                if not model_path.exists():
                    logger.error(f"Model file not found: {model_path}")
                    self.model_stats[model_name]["status"] = "not_found"
                    return False
                
                logger.info(f"Loading model {model_name} from {model_path}...")
                start_time = time.time()
                
                if LLAMA_CPP_AVAILABLE:
                    # Load real model using llama-cpp-python
                    n_gpu_layers = config["n_gpu_layers"]
                    logger.info(f"Attempting to load with config: n_ctx={config['context_size']}, n_gpu_layers={n_gpu_layers}")

                    try:
                        model = Llama(
                            model_path=str(model_path),
                            n_ctx=config["context_size"],
                            n_threads=getattr(settings, 'MODEL_THREADS', 6),
                            n_gpu_layers=n_gpu_layers,
                            verbose=False,  # Reduce verbosity for performance
                            seed=42  # For reproducible outputs during development
                        )
                    except Exception as gpu_error:
                        logger.warning(f"GPU loading failed, falling back to CPU: {gpu_error}")
                        # Fallback to CPU-only
                        model = Llama(
                            model_path=str(model_path),
                            n_ctx=config["context_size"],
                            n_threads=getattr(settings, 'MODEL_THREADS', 6),
                            n_gpu_layers=0,  # CPU only fallback
                            verbose=False,
                            seed=42
                        )
                    
                    # Verify model loaded correctly
                    if model.model is None:
                        raise RuntimeError("Model failed to load - model object is None")
                    
                    wrapper = RealModelWrapper(model, model_name, config)
                else:
                    # Fallback to mock model
                    logger.warning("Using mock model as fallback")
                    wrapper = MockModelWrapper(model_name, config)
                
                load_time = time.time() - start_time
                
                self.models[model_name] = wrapper
                self.active_model = model_name
                
                # Update stats
                self.model_stats[model_name].update({
                    "status": "loaded",
                    "load_time": f"{load_time:.1f}s",
                    "memory_usage": f"{wrapper.get_memory_usage():.1f}MB"
                })
                
                logger.info(f"Model {model_name} loaded successfully in {load_time:.1f}s")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}", exc_info=True)
                logger.error(f"Model path: {model_path}")
                logger.error(f"LLAMA_CPP_AVAILABLE: {LLAMA_CPP_AVAILABLE}")
                logger.error(f"Model config: {config}")
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
                
                # Cleanup model
                model_wrapper = self.models[model_name]
                model_wrapper.cleanup()
                
                del self.models[model_name]
                if self.active_model == model_name:
                    self.active_model = None
                
                self.model_stats[model_name].update({
                    "status": "available" if self.model_stats[model_name]["file_exists"] else "not_found",
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
            "total_loaded": len(self.models),
            "llama_cpp_available": LLAMA_CPP_AVAILABLE
        }
    
    def inference(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> dict:
        """Run inference on the active model and return text with token usage"""
        if not self.active_model or self.active_model not in self.models:
            raise RuntimeError("No model loaded for inference")
        
        start_time = time.time()
        
        try:
            model_wrapper = self.models[self.active_model]
            result = model_wrapper.generate(prompt, max_tokens, temperature)
            
            inference_time = time.time() - start_time
            
            # Update statistics
            self.model_stats[self.active_model].update({
                "last_used": datetime.utcnow(),
                "total_queries": self.model_stats[self.active_model]["total_queries"] + 1,
                "total_inference_time": self.model_stats[self.active_model]["total_inference_time"] + inference_time
            })
            
            logger.info(f"Inference completed in {inference_time:.2f}s using {self.active_model}")
            logger.info(f"Token usage - Prompt: {result['token_usage']['prompt_tokens']}, Completion: {result['token_usage']['completion_tokens']}, Total: {result['token_usage']['total_tokens']}")
            
            return result
            
        except Exception as e:
            self.model_stats[self.active_model]["error_count"] += 1
            logger.error(f"Inference error: {e}")
            raise
    
    def get_best_model_for_query(self, query: str) -> str:
        """Select the best model based on query complexity"""
        # Get available models (have files and can be loaded)
        available_models = [
            name for name, stats in self.model_stats.items() 
            if stats["file_exists"] and stats["status"] != "error"
        ]
        
        if not available_models:
            return None
        
        # Simple heuristic for model selection
        query_len = len(query)
        query_lower = query.lower()
        
        # Complex analytical queries - use best available model
        if any(word in query_lower for word in ['analyze', 'compare', 'trend', 'insight', 'performance']):
            if "qwen2.5-3b" in available_models:
                return "qwen2.5-3b"  # Best reasoning for analysis
            elif "llama3-8b" in available_models:
                return "llama3-8b"
            elif "phi-3-mini" in available_models:
                return "phi-3-mini"

        # Long queries - use model with good context
        elif query_len > 200:
            if "qwen2.5-3b" in available_models:
                return "qwen2.5-3b"
            elif "llama3-8b" in available_models:
                return "llama3-8b"
            elif "phi-3-mini" in available_models:
                return "phi-3-mini"

        # Greetings and simple queries - prioritize speed
        elif any(word in query_lower for word in ['hello', 'hi', 'how are you', 'thanks', 'thank you']):
            if "qwen2.5-1.5b" in available_models:
                return "qwen2.5-1.5b"  # Ultra-fast for greetings
            elif "qwen2.5-3b" in available_models:
                return "qwen2.5-3b"
            elif "gemma-2b" in available_models:
                return "gemma-2b"

        # Default/other queries - balanced choice
        else:
            if "qwen2.5-3b" in available_models:
                return "qwen2.5-3b"  # Good balance of speed and quality
            elif "phi-3-mini" in available_models:
                return "phi-3-mini"
            elif "gemma-2b" in available_models:
                return "gemma-2b"
        
        # Fallback to first available
        return available_models[0]
    
    def auto_load_best_model(self, query: str) -> bool:
        """Automatically load the best model for a query"""
        best_model = self.get_best_model_for_query(query)
        if not best_model:
            logger.error("No suitable model available")
            return False
        
        if self.active_model != best_model:
            logger.info(f"Auto-loading {best_model} for query")
            return self.load_model(best_model)
        
        return True
    
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
                if model_name != self.active_model:  # Don't unload active model
                    self.unload_model(model_name)
                    logger.info(f"Auto-unloaded idle model: {model_name}")


class RealModelWrapper:
    """Wrapper for real llama-cpp-python models"""
    
    def __init__(self, model: 'Llama', model_name: str, config: Dict):
        self.model = model
        self.model_name = model_name
        self.config = config
        self.context_size = config["context_size"]
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> dict:
        """Generate text using the real model and return with token usage"""
        try:
            # Use the temperature from config if not specified
            temp = temperature if temperature != 0.7 else self.config.get("temperature", 0.7)
            
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temp,
                echo=False,  # Don't echo the prompt
                stop=["Human:", "\n\nHuman:", "User:", "\n\nUser:"]  # Stop sequences
            )
            
            generated_text = response['choices'][0]['text'].strip()
            
            # Extract token usage from response
            usage = response.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            # Fallback: estimate tokens if not provided by model
            if prompt_tokens == 0:
                prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
            if completion_tokens == 0:
                completion_tokens = len(generated_text.split()) * 1.3
            
            return {
                "text": generated_text,
                "token_usage": {
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(prompt_tokens + completion_tokens)
                }
            }
            
        except Exception as e:
            logger.error(f"Model generation error: {e}")
            raise
    
    def get_memory_usage(self) -> float:
        """Estimate memory usage (simplified)"""
        # This is a rough estimate - actual usage depends on model size and context
        return 1000.0  # Return estimated MB
    
    def cleanup(self):
        """Cleanup model resources"""
        # llama-cpp-python handles cleanup automatically
        pass


class MockModelWrapper:
    """Mock model wrapper for fallback when llama-cpp-python isn't available"""
    
    def __init__(self, model_name: str, config: Dict):
        self.model_name = model_name
        self.config = config
        self.context_size = config["context_size"]
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> dict:
        """Mock text generation with token usage"""
        time.sleep(1.0)  # Simulate inference time
        
        # Return model-specific mock responses
        if "sales" in prompt.lower():
            text = f"Based on the sales data analysis using {self.model_name}, your total revenue shows strong performance with detailed breakdowns available."
        elif "inventory" in prompt.lower():
            text = f"Inventory analysis from {self.model_name} indicates several products require attention, with specific recommendations for stock optimization."
        elif "customer" in prompt.lower():
            text = f"Customer insights generated by {self.model_name} reveal important patterns in purchasing behavior and loyalty metrics."
        elif "order" in prompt.lower():
            text = f"Order analysis using {self.model_name} shows current fulfillment status and processing trends across different categories."
        else:
            text = f"Analysis completed using {self.model_name}. The data shows various insights that can help optimize your e-commerce operations."
        
        # Mock token usage calculation
        prompt_tokens = int(len(prompt.split()) * 1.3)
        completion_tokens = int(len(text.split()) * 1.3)
        
        return {
            "text": text,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        }
    
    def get_memory_usage(self) -> float:
        return 50.0  # Mock usage
    
    def cleanup(self):
        pass


# Global model manager instance
real_model_manager = RealModelManager()