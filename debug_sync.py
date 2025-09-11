#!/usr/bin/env python3
"""
Debug sync routes issue
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

print("=== Debug Sync Routes ===")

try:
    print("1. Testing basic imports...")
    from fastapi import FastAPI
    print("✅ FastAPI imported")
    
    print("2. Testing settings import...")
    from src.config.settings import settings
    print(f"✅ Settings imported - SYNC_ENABLED: {getattr(settings, 'SYNC_ENABLED', 'Not set')}")
    
    print("3. Testing sync router import...")
    from src.api.routes.sync import router as sync_router
    print(f"✅ Sync router imported - Routes: {len(sync_router.routes)}")
    
    print("4. Testing main app import...")
    from src.main import app
    print(f"✅ Main app imported - Total routes: {len(app.routes)}")
    
    print("5. Checking if sync routes are in main app...")
    sync_routes = [route for route in app.routes if hasattr(route, 'path') and '/sync' in route.path]
    print(f"Found {len(sync_routes)} sync routes in main app:")
    for route in sync_routes[:5]:  # Show first 5
        print(f"   {route.path}")
    
    print("6. Testing a simple endpoint creation...")
    test_app = FastAPI()
    test_app.include_router(sync_router, prefix="/sync")
    test_routes = [route for route in test_app.routes if hasattr(route, 'path')]
    print(f"Test app has {len(test_routes)} routes")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()