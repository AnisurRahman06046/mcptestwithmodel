# Real AI Models Setup Guide

## 🤖 Overview

The E-commerce MCP Server now supports **real AI models** using `llama-cpp-python` for local inference. This guide will help you download, configure, and use actual AI models instead of mock responses.

## 🎯 Available Models

### Recommended Models

| Model          | Size   | Description              | Use Case                        | Memory Required |
| -------------- | ------ | ------------------------ | ------------------------------- | --------------- |
| **phi-3-mini** | ~2.3GB | Microsoft Phi-3 Mini 4K  | General queries, fast responses | 4GB RAM         |
| **gemma-2b**   | ~1.5GB | Google Gemma 2B Instruct | Simple queries, very fast       | 3GB RAM         |
| **llama3-8b**  | ~4.8GB | Meta Llama 3 8B Instruct | Complex analysis, best quality  | 8GB RAM         |

### Model Selection Logic

- **Simple queries**: `gemma-2b` (fastest)
- **General queries**: `phi-3-mini` (balanced)
- **Complex analysis**: `llama3-8b` (highest quality)

## 📦 Installation Steps

### 1. Install Dependencies

```bash
# Install with CPU support (basic)
pip install llama-cpp-python==0.2.20

# OR install with GPU support (NVIDIA CUDA)
pip install llama-cpp-python==0.2.20 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# OR install with Metal support (Apple Silicon)
pip install llama-cpp-python==0.2.20 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal
```

### 2. Download Models

#### Option A: Using the Download Script (Recommended)

```bash
# List available models
python scripts/download_models.py list

# Download a specific lightweight model
python scripts/download_models.py download --model phi-3-mini

# Download all models (requires ~8GB+ disk space)
python scripts/download_models.py download-all
```

#### Option B: Manual Download

```bash
# Create model directory
mkdir -p data/models

# Download Phi-3 Mini (recommended for testing)
cd data/models
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
```

### 3. Configure Environment

Update your `.env` file:

```env
# Model Configuration
MODEL_PATH=./data/models
DEFAULT_MODEL=phi-3-mini
MODEL_CONTEXT_SIZE=4096
MODEL_THREADS=4
MODEL_GPU_LAYERS=20  # Adjust based on your GPU (0 for CPU-only)
```

## 🚀 Usage

### 1. Start the Server

```bash
python main.py
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### 2. Check Model Status

```bash
curl -X GET "http://127.0.0.1:8000/models/status"
```

### 3. Load a Model

```bash
curl -X POST "http://127.0.0.1:8000/models/load/phi-3-mini"
```

### 4. Test with Real AI

```bash
curl -X POST "http://127.0.0.1:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What were our top selling products last month?",
       "context": {"user_id": "test", "shop_id": "demo"}
     }'
```

## 🔧 Configuration Options

### Model-Specific Settings

Edit `src/services/real_model_manager.py` to adjust model configurations:

```python
"phi-3-mini": {
    "filename": "phi-3-mini-4k-instruct-q4.gguf",
    "context_size": 4096,
    "n_gpu_layers": 20,  # Number of layers to offload to GPU
    "temperature": 0.7   # Response creativity (0.0-1.0)
}
```

### GPU Acceleration

#### NVIDIA GPUs

```bash
# Install CUDA support
pip uninstall llama-cpp-python
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# Increase GPU layers in .env
MODEL_GPU_LAYERS=35  # Higher = more GPU usage
```

#### Apple Silicon (M1/M2/M3)

```bash
# Install Metal support
pip uninstall llama-cpp-python
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal

# Enable Metal acceleration
MODEL_GPU_LAYERS=20
```

#### CPU Only

```bash
# Set to 0 for CPU-only inference
MODEL_GPU_LAYERS=0
MODEL_THREADS=8  # Match your CPU cores
```

## 🎛️ Model Management

### Automatic Model Selection

The system automatically selects the best model based on query complexity:

```python
# Simple query → gemma-2b (if available)
"How many orders do I have?"

# Complex query → llama3-8b (if available)
"Analyze seasonal trends in electronics sales and provide recommendations"
```

### Manual Model Loading

```bash
# Via API
curl -X POST "http://127.0.0.1:8000/models/load/llama3-8b"

# Via Python
from src.services.real_model_manager import real_model_manager
real_model_manager.load_model("llama3-8b")
```

### Memory Management

```bash
# Unload unused models
curl -X DELETE "http://127.0.0.1:8000/models/unload/phi-3-mini"

# Check memory usage
curl -X GET "http://127.0.0.1:8000/health/system"
```

## 📊 Performance Expectations

### Response Times (Approximate)

| Model      | CPU (8 cores) | GPU (RTX 3060) | GPU (RTX 4080)  |
| ---------- | ------------- | -------------- | --------------- |
| gemma-2b   | 2-4 seconds   | 0.5-1 seconds  | 0.3-0.5 seconds |
| phi-3-mini | 3-6 seconds   | 1-2 seconds    | 0.5-1 seconds   |
| llama3-8b  | 8-15 seconds  | 2-4 seconds    | 1-2 seconds     |

### Memory Usage

| Model      | RAM Usage | VRAM Usage (GPU) |
| ---------- | --------- | ---------------- |
| gemma-2b   | ~2GB      | ~1.5GB           |
| phi-3-mini | ~3GB      | ~2.5GB           |
| llama3-8b  | ~6GB      | ~5GB             |

## 🧪 Testing Real Models

### 1. Model Loading Test

```python
# Test script
from src.services.real_model_manager import real_model_manager

# Check available models
status = real_model_manager.get_model_status()
print("Available models:", [m["name"] for m in status["models"] if m["file_exists"]])

# Load model
success = real_model_manager.load_model("phi-3-mini")
print("Model loaded:", success)

# Test inference
if success:
    response = real_model_manager.inference("What is 2+2?", max_tokens=50)
    print("Response:", response)
```

### 2. End-to-End Query Test

```bash
# Sales query
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze our sales performance for electronics products last month",
    "context": {"user_id": "test", "shop_id": "demo"}
  }' | jq '.response'
```

### 3. Compare Mock vs Real Models

```bash
# Check if using real model
curl -X GET "http://127.0.0.1:8000/models/status" | jq '.llama_cpp_available'

# Query response should be more natural and context-aware with real models
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Model File Not Found

```
Error: Model file not found: ./data/models/phi-3-mini-4k-instruct-q4.gguf
```

**Solution**: Download the model using the script:

```bash
python scripts/download_models.py download --model phi-3-mini
```

#### 2. Out of Memory

```
Error: Failed to allocate memory for model
```

**Solution**:

- Reduce `MODEL_GPU_LAYERS` in `.env`
- Use a smaller model (gemma-2b)
- Close other applications

#### 3. Slow Loading

```
Model loading takes >2 minutes
```

**Solution**:

- Check if using SSD storage
- Increase `MODEL_THREADS` for CPU loading
- Verify GPU drivers for GPU acceleration

#### 4. Import Error

```
ImportError: No module named 'llama_cpp'
```

**Solution**:

```bash
pip install llama-cpp-python==0.2.20
```

### Performance Optimization

#### 1. Speed Up Loading

```env
# Use faster model loading
MODEL_THREADS=8  # Match CPU cores
MODEL_GPU_LAYERS=35  # More GPU layers
```

#### 2. Reduce Memory Usage

```env
# Smaller context window
MODEL_CONTEXT_SIZE=2048

# Fewer GPU layers
MODEL_GPU_LAYERS=10
```

#### 3. Improve Response Quality

```python
# In model config, increase temperature for creativity
"temperature": 0.8

# Or decrease for consistency
"temperature": 0.3
```

## 📝 Model-Specific Notes

### Phi-3 Mini

- **Best for**: General-purpose queries, development, testing
- **Strengths**: Fast, good quality, efficient
- **Weaknesses**: Limited context compared to larger models

### Gemma 2B

- **Best for**: Simple queries, very fast responses
- **Strengths**: Extremely fast, low memory usage
- **Weaknesses**: Less capable for complex analysis

### Llama 3 8B

- **Best for**: Complex analysis, detailed responses
- **Strengths**: High quality, excellent understanding
- **Weaknesses**: Slower, higher memory requirements

## 🎯 Production Considerations

### 1. Model Caching

- Keep frequently used models loaded
- Implement model warming strategies
- Monitor memory usage patterns

### 2. Scaling

- Use model serving frameworks (vLLM, TensorRT-LLM)
- Implement request queuing
- Consider model quantization for speed

### 3. Security

- Validate all user inputs before model inference
- Implement rate limiting
- Monitor for prompt injection attempts

---

## 🚀 Quick Start Checklist

- [ ] Install `llama-cpp-python` with appropriate backend
- [ ] Download at least one model (recommended: `phi-3-mini`)
- [ ] Configure `.env` with model settings
- [ ] Start server and verify model loading
- [ ] Test queries and compare with mock responses
- [ ] Monitor performance and adjust settings

**Ready to experience real AI-powered e-commerce analytics!** 🎉
