#!/usr/bin/env python3
"""
Test sync routes loading
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("Testing sync router import...")
    from src.api.routes.sync import router
    print("✅ Sync router imported successfully")
    print(f"Router prefix: {router.prefix}")
    print(f"Number of routes: {len(router.routes)}")
    
    for route in router.routes:
        if hasattr(route, 'path'):
            print(f"  Route: {route.path} - {route.methods}")
            
except Exception as e:
    print(f"❌ Error importing sync router: {e}")
    import traceback
    traceback.print_exc()