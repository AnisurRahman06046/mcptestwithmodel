#!/usr/bin/env python3
"""
Model download script for E-commerce MCP Server
Downloads lightweight GGUF models for local inference
"""

import os
import sys
import requests
from pathlib import Path
from tqdm import tqdm
import hashlib

# Add src to path for importing settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from src.config.settings import settings
except ImportError:
    # Fallback if settings not available
    class Settings:
        MODEL_PATH = "./data/models"
    settings = Settings()

# Model configurations
AVAILABLE_MODELS = {
    "phi-3-mini": {
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "filename": "phi-3-mini-4k-instruct-q4.gguf",
        "size_mb": 2300,  # ~2.3GB
        "description": "Microsoft Phi-3 Mini 4K - Lightweight and efficient model",
        "context_size": 4096
    },
    "llama3-8b": {
        "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
        "filename": "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf", 
        "size_mb": 4800,  # ~4.8GB
        "description": "Meta Llama 3 8B Instruct - High quality responses",
        "context_size": 8192
    },
    "gemma-2b": {
        "url": "https://huggingface.co/google/gemma-2b-it-GGUF/resolve/main/gemma-2b-it.q4_k_m.gguf",
        "filename": "gemma-2b-it.q4_k_m.gguf",
        "size_mb": 1500,  # ~1.5GB
        "description": "Google Gemma 2B Instruct - Very lightweight",
        "context_size": 2048
    }
}

def ensure_model_directory():
    """Ensure model directory exists"""
    model_dir = Path(settings.MODEL_PATH)
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir

def download_file(url: str, filepath: Path, description: str = ""):
    """Download file with progress bar"""
    print(f"Downloading {description}...")
    print(f"URL: {url}")
    print(f"Destination: {filepath}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filepath, 'wb') as file, tqdm(
        desc=filepath.name,
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            size = file.write(chunk)
            pbar.update(size)
    
    print(f"✓ Download completed: {filepath}")

def verify_download(filepath: Path, expected_size_mb: int):
    """Verify downloaded file"""
    if not filepath.exists():
        return False
    
    actual_size_mb = filepath.stat().st_size / (1024 * 1024)
    expected_min = expected_size_mb * 0.95  # 5% tolerance
    expected_max = expected_size_mb * 1.05
    
    if expected_min <= actual_size_mb <= expected_max:
        print(f"✓ File size verification passed: {actual_size_mb:.1f}MB")
        return True
    else:
        print(f"✗ File size mismatch: {actual_size_mb:.1f}MB (expected ~{expected_size_mb}MB)")
        return False

def download_model(model_name: str, force_download: bool = False):
    """Download a specific model"""
    if model_name not in AVAILABLE_MODELS:
        print(f"✗ Unknown model: {model_name}")
        print(f"Available models: {', '.join(AVAILABLE_MODELS.keys())}")
        return False
    
    model_config = AVAILABLE_MODELS[model_name]
    model_dir = ensure_model_directory()
    filepath = model_dir / model_config["filename"]
    
    # Check if already downloaded
    if filepath.exists() and not force_download:
        if verify_download(filepath, model_config["size_mb"]):
            print(f"✓ Model {model_name} already downloaded and verified")
            return True
        else:
            print(f"⚠ Model file exists but verification failed, re-downloading...")
    
    try:
        download_file(
            model_config["url"],
            filepath,
            f"{model_name} ({model_config['size_mb']}MB)"
        )
        
        if verify_download(filepath, model_config["size_mb"]):
            print(f"✅ Successfully downloaded {model_name}")
            return True
        else:
            print(f"✗ Download verification failed for {model_name}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to download {model_name}: {e}")
        if filepath.exists():
            filepath.unlink()  # Remove partial download
        return False

def list_models():
    """List available models"""
    print("\n📋 Available Models:")
    print("-" * 80)
    
    for name, config in AVAILABLE_MODELS.items():
        model_path = Path(settings.MODEL_PATH) / config["filename"]
        status = "✓ Downloaded" if model_path.exists() else "⬇ Available"
        
        print(f"{name:12} | {config['size_mb']:>4}MB | {status:12} | {config['description']}")
    
    print("-" * 80)

def check_disk_space(model_name: str = None):
    """Check available disk space"""
    model_dir = Path(settings.MODEL_PATH)
    if model_dir.exists():
        import shutil
        free_space_gb = shutil.disk_usage(model_dir).free / (1024**3)
    else:
        free_space_gb = shutil.disk_usage(Path.cwd()).free / (1024**3)
    
    print(f"💾 Available disk space: {free_space_gb:.1f}GB")
    
    if model_name:
        required_gb = AVAILABLE_MODELS[model_name]["size_mb"] / 1024
        if free_space_gb < required_gb * 1.2:  # 20% buffer
            print(f"⚠ Warning: Low disk space for {model_name} (needs ~{required_gb:.1f}GB)")
            return False
    
    return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download AI models for E-commerce MCP Server")
    parser.add_argument("action", choices=["list", "download", "download-all"], 
                       help="Action to perform")
    parser.add_argument("--model", type=str, help="Model name to download")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    
    args = parser.parse_args()
    
    print("🤖 E-commerce MCP Server - Model Downloader")
    print("=" * 50)
    
    if args.action == "list":
        list_models()
        check_disk_space()
    
    elif args.action == "download":
        if not args.model:
            print("✗ Please specify --model parameter")
            list_models()
            return 1
        
        if not check_disk_space(args.model):
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return 1
        
        success = download_model(args.model, args.force)
        return 0 if success else 1
    
    elif args.action == "download-all":
        print("📥 Downloading all available models...")
        if not check_disk_space():
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return 1
        
        success_count = 0
        for model_name in AVAILABLE_MODELS.keys():
            print(f"\n📥 Downloading {model_name}...")
            if download_model(model_name, args.force):
                success_count += 1
        
        print(f"\n✅ Downloaded {success_count}/{len(AVAILABLE_MODELS)} models successfully")
        return 0 if success_count > 0 else 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠ Download cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)