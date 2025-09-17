#!/usr/bin/env python3
"""
Test script to verify the router migration is working correctly.

This script performs basic validation of the migrated FastAPI structure:
1. Import validation
2. App initialization
3. Endpoint registration
4. Basic health check
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test that all modules can be imported correctly."""
    print("🔍 Testing imports...")
    
    try:
        # Test main module import
        import main
        print("✅ Main module imported successfully")
        
        # Test router imports
        from routers import processing_handler
        print("✅ Processing handler router imported successfully")
        
        # Test FastAPI app creation
        app = main.app
        print(f"✅ FastAPI app created with {len(app.routes)} routes")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        traceback.print_exc()
        return False


def test_endpoints():
    """Test that all expected endpoints are registered."""
    print("\n🔍 Testing endpoint registration...")
    
    try:
        from main import app
        from fastapi.routing import APIRoute
        
        # Get all API routes
        endpoints = [route.path for route in app.routes if isinstance(route, APIRoute)]
        
        # Expected endpoints from the original processing-handler.py
        expected_endpoints = [
            "/",           # Root endpoint
            "/health",     # Health check
            "/upload",     # File upload
            "/ocr-process", # OCR processing
            "/results/{uid}", # Get results
            "/folders",    # List folders
            "/cleanup/{uid}", # Cleanup
            "/admin/purge", # Admin purge
            "/admin/data-usage" # Admin data usage
        ]
        
        print("📋 Expected endpoints:")
        for endpoint in expected_endpoints:
            if endpoint in endpoints:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint} - MISSING")
        
        print(f"\n📊 Total endpoints found: {len(endpoints)}")
        print(f"📊 Expected endpoints: {len(expected_endpoints)}")
        
        missing = set(expected_endpoints) - set(endpoints)
        if missing:
            print(f"❌ Missing endpoints: {missing}")
            return False
        else:
            print("✅ All expected endpoints are registered")
            return True
            
    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        traceback.print_exc()
        return False


def test_router_structure():
    """Test the router structure and organization."""
    print("\n🔍 Testing router structure...")
    
    try:
        from routers import processing_handler
        
        # Check router instance
        router = processing_handler.router
        print(f"✅ Router instance created: {type(router)}")
        
        # Check router has routes
        route_count = len(router.routes)
        print(f"✅ Router has {route_count} routes")
        
        # Check that router is an APIRouter
        from fastapi import APIRouter
        if isinstance(router, APIRouter):
            print("✅ Router is properly typed as APIRouter")
        else:
            print(f"❌ Router type is incorrect: {type(router)}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Router structure test failed: {e}")
        traceback.print_exc()
        return False


def test_configuration():
    """Test that configuration is properly loaded."""
    print("\n🔍 Testing configuration...")
    
    try:
        from routers.processing_handler import CONFIG
        
        print("📋 Configuration loaded:")
        for key, value in CONFIG.items():
            print(f"  {key}: {value}")
        
        # Check essential config items
        essential_configs = ["data_root", "image_format", "image_dpi", "max_file_size_mb"]
        for config in essential_configs:
            if config in CONFIG:
                print(f"✅ {config} is configured")
            else:
                print(f"❌ {config} is missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Router Migration Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_endpoints, 
        test_router_structure,
        test_configuration
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("\n✅ Router migration completed successfully!")
        print("\nYou can now run the application with:")
        print("  python main.py")
        print("  or")
        print("  uvicorn main:app --reload")
        return 0
    else:
        print(f"❌ Some tests failed ({passed}/{total})")
        print("\n🔧 Please check the failed tests and fix any issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())