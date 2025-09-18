#!/usr/bin/env python3
"""
Simple test runner for PDF to DocAI integration test.

This is a simplified wrapper that handles common setup and runs the main integration test.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Set up test environment and check dependencies."""
    
    # Load environment variables from .env file
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"✅ Loaded environment from {env_file}")
        except ImportError:
            print("⚠️ python-dotenv not installed, loading .env manually")
            # Load .env manually
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print("✅ Environment variables loaded manually")
    else:
        print("⚠️ No .env file found")
    
    # Check if we're in the right directory
    if not (project_root / "main.py").exists():
        print("❌ Error: Please run this from the ai-backend project root")
        return False
    
    # Check for required environment variables
    required_vars = [
        "GOOGLE_CLOUD_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "DOCAI_PROCESSOR_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before running the test.")
        return False
    
    print("✅ Environment check passed")
    return True

def run_basic_test():
    """Run a basic integration test."""
    
    print("🔍 Running Basic PDF to DocAI Integration Test")
    print("=" * 50)
    
    try:
        # Import the test module
        from scripts.test_pdf_to_docai import PDFToDocAITester
        
        # Create data directory
        data_dir = project_root / "data" / "integration_tests"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tester
        tester = PDFToDocAITester(data_dir=str(data_dir))
        
        # Check if we have an existing test PDF
        test_files_dir = project_root / "data" / "test-files"
        existing_pdf = None
        
        if test_files_dir.exists():
            for pdf_file in test_files_dir.glob("*.pdf"):
                existing_pdf = str(pdf_file)
                print(f"📄 Found existing test PDF: {pdf_file.name}")
                break
        
        # Run the test
        print("\n🚀 Starting integration test...")
        results = tester.run_complete_test(pdf_path=existing_pdf)
        
        # Print summary
        print("\n📊 Test Summary:")
        summary = results.get("test_summary", {})
        if summary.get("overall_success", False):
            print("✅ Integration test PASSED!")
            return True
        else:
            print("❌ Integration test had issues")
            errors = results.get("errors", [])
            if errors:
                print("Errors encountered:")
                for error in errors[:3]:  # Show first 3 errors
                    print(f"  • {error}")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_component_tests():
    """Run individual component tests."""
    
    print("🔧 Running Component Tests")
    print("=" * 30)
    
    # Test 1: FastAPI app startup
    print("1️⃣ Testing FastAPI app...")
    try:
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        if response.status_code == 200:
            print("   ✅ FastAPI app is working")
        else:
            print(f"   ❌ FastAPI app returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ FastAPI app test failed: {e}")
        return False
    
    # Test 2: DocAI endpoints
    print("2️⃣ Testing DocAI endpoints...")
    try:
        config_response = client.get("/api/docai/config")
        if config_response.status_code == 200:
            print("   ✅ DocAI config endpoint working")
        else:
            print(f"   ❌ DocAI config returned {config_response.status_code}")
            
        processors_response = client.get("/api/docai/processors")
        if processors_response.status_code == 200:
            print("   ✅ DocAI processors endpoint working")
        else:
            print(f"   ❌ DocAI processors returned {processors_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ DocAI endpoints test failed: {e}")
        return False
    
    # Test 3: Vision OCR
    print("3️⃣ Testing Vision OCR...")
    try:
        # Handle the hyphenated filename
        import importlib.util
        ocr_module_path = project_root / "services" / "preprocessing" / "OCR-processing.py"
        
        if ocr_module_path.exists():
            spec = importlib.util.spec_from_file_location("OCR_processing", ocr_module_path)
            ocr_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ocr_module)
            GoogleVisionOCR = ocr_module.GoogleVisionOCR
            
            ocr = GoogleVisionOCR.from_env()
            print("   ✅ Vision OCR client initialized")
        else:
            print("   ❌ OCR module file not found")
            return False
        
    except Exception as e:
        print(f"   ❌ Vision OCR test failed: {e}")
        return False
    
    print("✅ All component tests passed!")
    return True

def main():
    """Main function."""
    
    print("🧪 PDF to DocAI Integration Test Runner")
    print("=" * 40)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Run component tests first
    print("\n" + "=" * 40)
    if not run_component_tests():
        print("❌ Component tests failed. Fix issues before running integration test.")
        sys.exit(1)
    
    # Run basic integration test
    print("\n" + "=" * 40)
    success = run_basic_test()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Tests completed with issues.")
        sys.exit(1)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)