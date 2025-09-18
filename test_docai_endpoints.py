#!/usr/bin/env python3
"""
Simple test script for DocAI FastAPI endpoints.

Tests the DocAI router endpoints directly without the full FastAPI server.
"""

import asyncio
import json
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Import FastAPI testing components
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import our DocAI router directly without going through __init__.py
import sys
sys.path.append('./routers')
sys.path.append('./services')

# Import the router module directly
import importlib.util
spec = importlib.util.spec_from_file_location("doc_ai_router", "./routers/doc_ai_router.py")
doc_ai_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc_ai_router_module)
docai_router = doc_ai_router_module.router

async def test_docai_endpoints():
    """Test DocAI endpoints directly."""
    
    print("🧪 Testing DocAI FastAPI Endpoints")
    print("=" * 50)
    
    # Create a simple FastAPI app with just the DocAI router
    app = FastAPI(title="DocAI Test App")
    app.include_router(docai_router)
    
    # Create test client
    client = TestClient(app)
    
    # Test 1: Health check
    print("\n1️⃣ Testing health endpoint...")
    try:
        response = client.get("/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   Service status: {health_data.get('status', 'unknown')}")
            print("   ✅ Health check passed")
        else:
            print(f"   ❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Configuration endpoint
    print("\n2️⃣ Testing configuration endpoint...")
    try:
        response = client.get("/api/docai/config")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            config_data = response.json()
            print(f"   Project ID: {config_data.get('project_id')}")
            print(f"   Processor ID: {config_data.get('default_processor_id')}")
            print("   ✅ Configuration endpoint passed")
        else:
            print(f"   ❌ Configuration failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
    
    # Test 3: Processors endpoint
    print("\n3️⃣ Testing processors endpoint...")
    try:
        response = client.get("/api/docai/processors")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            processors_data = response.json()
            print(f"   Total processors: {processors_data.get('total', 0)}")
            print("   ✅ Processors endpoint passed")
        else:
            print(f"   ❌ Processors failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Processors error: {e}")
    
    # Test 4: Document parsing with GCS URI (the one we uploaded during testing)
    print("\n4️⃣ Testing document parsing endpoint...")
    
    # Use the GCS URI from our test
    gcs_uri = f"gs://{os.getenv('GOOGLE_CLOUD_PROJECT_ID')}-docai-test/test-documents/testing-ocr-pdf-1.pdf"
    
    parse_request = {
        "gcs_uri": gcs_uri,
        "confidence_threshold": 0.7,
        "include_raw_response": False,
        "metadata": {
            "test_type": "endpoint_test",
            "source": "existing_gcs_file"
        }
    }
    
    try:
        print(f"   Parsing: {gcs_uri}")
        response = client.post("/api/docai/parse", json=parse_request)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            parse_data = response.json()
            
            if parse_data.get("success"):
                document = parse_data.get("document", {})
                metadata = document.get("metadata", {})
                
                print(f"   ✅ Document parsed successfully!")
                print(f"   Document ID: {metadata.get('document_id')}")
                print(f"   Processing time: {parse_data.get('processing_time_seconds', 0):.2f}s")
                print(f"   Text length: {len(document.get('full_text', ''))}")
                print(f"   Entities: {len(document.get('named_entities', []))}")
                print(f"   Clauses: {len(document.get('clauses', []))}")
                
                # Save the API response for inspection
                timestamp = parse_data.get('request_id', 'unknown')
                api_result_file = Path("./data/processed") / f"api_test_result_{timestamp}.json"
                with open(api_result_file, 'w', encoding='utf-8') as f:
                    json.dump(parse_data, f, indent=2, default=str)
                print(f"   📁 API result saved: {api_result_file}")
                
            else:
                print(f"   ❌ Document parsing failed: {parse_data.get('error_message')}")
                
        else:
            print(f"   ❌ Parse request failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Parse endpoint error: {e}")
    
    # Test 5: Error handling with invalid GCS URI
    print("\n5️⃣ Testing error handling...")
    try:
        invalid_request = {
            "gcs_uri": "invalid-uri-format",
            "confidence_threshold": 0.7
        }
        
        response = client.post("/api/docai/parse", json=invalid_request)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 422:
            print("   ✅ Correctly rejected invalid GCS URI (422 validation error)")
        elif response.status_code == 200:
            parse_data = response.json()
            if not parse_data.get("success"):
                print(f"   ✅ Correctly handled error: {parse_data.get('error_message')}")
            else:
                print("   ❌ Should have failed with invalid URI")
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error handling test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 DocAI endpoint testing completed!")

if __name__ == "__main__":
    asyncio.run(test_docai_endpoints())