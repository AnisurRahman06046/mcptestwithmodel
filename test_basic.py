#!/usr/bin/env python3
"""
Basic test script to verify the core functionality without requiring full dependencies
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from src.config.settings import settings
        print("✓ Settings imported successfully")
        
        from src.models.database import Product, Customer, Order, OrderItem, Inventory
        print("✓ Database models imported successfully")
        
        from src.models.api import QueryRequest, QueryResponse
        print("✓ API models imported successfully")
        
        from src.database.connection import init_database
        print("✓ Database connection module imported successfully")
        
        from src.services.model_manager import ModelManager
        print("✓ Model manager imported successfully")
        
        from src.services.tool_registry import ToolRegistry
        print("✓ Tool registry imported successfully")
        
        from src.services.query_processor import QueryProcessor
        print("✓ Query processor imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_database_init():
    """Test database initialization"""
    try:
        from src.database.connection import init_database
        init_database()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def test_model_manager():
    """Test model manager basic functionality"""
    try:
        from src.services.model_manager import ModelManager
        manager = ModelManager()
        status = manager.get_model_status()
        print(f"✓ Model manager working. Found {len(status['models'])} models")
        return True
    except Exception as e:
        print(f"✗ Model manager test failed: {e}")
        return False

def test_tool_registry():
    """Test tool registry"""
    try:
        from src.services.tool_registry import ToolRegistry
        registry = ToolRegistry()
        print(f"✓ Tool registry working. Found {len(registry.tools)} tools")
        return True
    except Exception as e:
        print(f"✗ Tool registry test failed: {e}")
        return False

def test_query_processor():
    """Test query processor basic functionality"""
    try:
        from src.services.query_processor import QueryProcessor
        processor = QueryProcessor()
        print("✓ Query processor initialized successfully")
        
        # Test intent classification
        intent = processor._classify_intent("What were our sales last month?")
        print(f"✓ Intent classification working: {intent}")
        
        # Test entity extraction
        entities = processor._extract_entities("How many red shirts did we sell last week?")
        print(f"✓ Entity extraction working: {entities}")
        
        return True
    except Exception as e:
        print(f"✗ Query processor test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("Running basic functionality tests...\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("Database Initialization", test_database_init),
        ("Model Manager", test_model_manager),
        ("Tool Registry", test_tool_registry),
        ("Query Processor", test_query_processor)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All basic tests passed! The prototype structure is working correctly.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)