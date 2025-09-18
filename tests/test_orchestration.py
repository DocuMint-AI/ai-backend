#!/usr/bin/env python3
"""
Test script for the orchestration router implementation.

This script validates the orchestration router functionality and
ensures the refactored main.py maintains existing functionality.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from main import app
    from routers.orchestration_router import (
        ProcessingPipelineResponse,
        ProcessingStatus,
        save_final_results,
        CONFIG
    )
    from fastapi.testclient import TestClient
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Install with: uv add fastapi uvicorn")
    sys.exit(1)


def test_app_structure():
    """Test that the app structure is correct."""
    print("Testing app structure...")
    
    # Check that the app has the expected routers
    router_tags = []
    for route in app.routes:
        if hasattr(route, 'tags') and route.tags:
            router_tags.extend(route.tags)
    
    expected_tags = ["Document Processing", "Document AI", "Pipeline Orchestration"]
    for tag in expected_tags:
        if tag in router_tags:
            print(f"✓ {tag} router is registered")
        else:
            print(f"✗ {tag} router is missing")
    
    # Check endpoints
    endpoints = [route.path for route in app.routes]
    
    expected_endpoints = [
        "/",
        "/upload",
        "/ocr-process",
        "/api/docai/parse",
        "/api/v1/process-document",
        "/api/v1/pipeline-status/{pipeline_id}",
        "/api/v1/pipeline-results/{pipeline_id}"
    ]
    
    for endpoint in expected_endpoints:
        if endpoint in endpoints:
            print(f"✓ Endpoint {endpoint} is available")
        else:
            print(f"✗ Endpoint {endpoint} is missing")


def test_orchestration_models():
    """Test that the orchestration models work correctly."""
    print("\nTesting orchestration models...")
    
    try:
        # Test ProcessingPipelineResponse creation
        response = ProcessingPipelineResponse(
            success=True,
            pipeline_id="test-123",
            message="Test message",
            total_processing_time=10.5,
            stage_timings={"upload": 1.0, "ocr": 5.0, "docai": 4.5}
        )
        print("✓ ProcessingPipelineResponse model works")
        
        # Test ProcessingStatus creation
        from datetime import datetime
        status = ProcessingStatus(
            pipeline_id="test-123",
            current_stage="uploading",
            progress_percentage=25.0,
            total_stages=4,
            completed_stages=1,
            start_time=datetime.now(),
            current_stage_start=datetime.now()
        )
        print("✓ ProcessingStatus model works")
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")


def test_config_and_paths():
    """Test configuration and path handling."""
    print("\nTesting configuration...")
    
    # Check data root path
    data_root = Path(CONFIG["data_root"])
    print(f"Data root: {data_root}")
    
    # Test that directories can be created
    try:
        processed_dir = data_root / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Can create processed directory")
        
        uploads_dir = data_root / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        print("✓ Can create uploads directory")
        
    except Exception as e:
        print(f"✗ Directory creation failed: {e}")


def test_save_results_function():
    """Test the save_final_results function."""
    print("\nTesting save_final_results function...")
    
    try:
        # Create test data
        test_pipeline_id = "test-pipeline-123"
        upload_result = {
            "success": True,
            "file_path": "/test/path/document.pdf",
            "file_info": {"size": 1024, "type": "pdf"}
        }
        ocr_result = {
            "success": True,
            "uid": "ocr-123",
            "total_pages": 5,
            "processed_pages": 5,
            "ocr_results_path": "/test/ocr/results.json"
        }
        docai_result = {
            "success": True,
            "document": {"text": "Sample text", "entities": []},
            "request_id": "docai-123"
        }
        stage_timings = {"upload": 1.0, "ocr": 5.0, "docai": 3.0}
        
        # Test save function
        results_path = save_final_results(
            test_pipeline_id,
            upload_result,
            ocr_result,
            docai_result,
            stage_timings
        )
        
        print(f"✓ Results saved to: {results_path}")
        
        # Verify file was created and contains expected data
        if Path(results_path).exists():
            with open(results_path, 'r') as f:
                saved_data = json.load(f)
            
            if saved_data.get("pipeline_id") == test_pipeline_id:
                print("✓ Saved data contains correct pipeline_id")
            else:
                print("✗ Saved data missing pipeline_id")
                
            # Clean up test file
            Path(results_path).unlink()
            print("✓ Test file cleaned up")
        else:
            print("✗ Results file was not created")
            
    except Exception as e:
        print(f"✗ Save results test failed: {e}")


def test_api_client():
    """Test API client functionality."""
    print("\nTesting API client...")
    
    try:
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        if response.status_code == 200:
            data = response.json()
            if "endpoints" in data and "pipeline_process" in data["endpoints"]:
                print("✓ Root endpoint includes orchestration endpoints")
            else:
                print("✗ Root endpoint missing orchestration endpoints")
        else:
            print(f"✗ Root endpoint failed: {response.status_code}")
        
        # Test orchestration health endpoint
        response = client.get("/api/v1/health")
        if response.status_code == 200:
            print("✓ Orchestration health endpoint works")
        else:
            print(f"✗ Orchestration health endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"✗ API client test failed: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ORCHESTRATION ROUTER VALIDATION TESTS")
    print("=" * 60)
    
    test_app_structure()
    test_orchestration_models()
    test_config_and_paths()
    test_save_results_function()
    test_api_client()
    
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    print("\nNote: Full integration testing requires:")
    print("- Google Cloud credentials configured")
    print("- PDF test files")
    print("- Running services (OCR, DocAI)")
    
    print("\nTo start the server:")
    print("uv run uvicorn main:app --reload")


if __name__ == "__main__":
    main()