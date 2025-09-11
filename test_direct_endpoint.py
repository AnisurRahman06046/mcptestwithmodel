#!/usr/bin/env python3
"""
Test sync endpoint directly using the app
"""

import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_sync_status():
    try:
        print("Testing sync status endpoint directly...")
        
        # Import the app
        from src.main import app
        from fastapi.testclient import TestClient
        
        # Create test client
        client = TestClient(app)
        
        # Test the sync status endpoint
        response = client.get("/sync/status")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 404:
            print("\n❌ 404 Error - checking available routes:")
            for route in app.routes:
                if hasattr(route, 'path'):
                    print(f"   {route.path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sync_status())