#!/usr/bin/env python3
"""
Comprehensive test runner for AI Backend Document Processing API.

This script runs all tests for the router-based FastAPI architecture,
including unit tests, integration tests, and validation tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """
    Run a command and return success status and output.
    
    Args:
        cmd: Command to run as list of strings
        description: Description for logging
        
    Returns:
        Tuple of (success, output)
    """
    print(f"\n🔍 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        if success:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        
        return success, result.stdout
        
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False, str(e)


def test_router_migration():
    """Test the router migration functionality."""
    print("\n🔍 Testing Router Migration")
    print("=" * 60)
    
    try:
        # Test main.py imports
        from main import app
        print("✅ Main app imports successfully")
        
        # Test router imports
        from routers import processing_handler
        print("✅ Processing handler router imports successfully")
        
        # Test endpoint registration
        from fastapi.routing import APIRoute
        endpoints = [route.path for route in app.routes if isinstance(route, APIRoute)]
        expected_endpoints = [
            "/", "/health", "/upload", "/ocr-process", 
            "/results/{uid}", "/folders", "/cleanup/{uid}",
            "/admin/purge", "/admin/data-usage"
        ]
        
        missing = set(expected_endpoints) - set(endpoints)
        if missing:
            print(f"❌ Missing endpoints: {missing}")
            return False
        
        print(f"✅ All {len(expected_endpoints)} endpoints registered")
        print("✅ Router migration test - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Router migration test - FAILED: {e}")
        return False


def run_unit_tests():
    """Run unit tests for services."""
    return run_command(
        ["python", "-m", "pytest", "tests/test_ocr_processing.py", "-v"],
        "Unit Tests - OCR Processing"
    )


def run_parsing_tests():
    """Run parsing unit tests."""
    return run_command(
        ["python", "-m", "pytest", "tests/test_parsing.py", "-v"],
        "Unit Tests - Text Parsing"
    )


def run_integration_tests():
    """Run integration tests with router architecture."""
    return run_command(
        ["python", "-m", "pytest", "tests/integration-tests.py", "-v", "-s"],
        "Integration Tests - Router Architecture"
    )


def run_schema_validation():
    """Run DocAI schema validation tests."""
    return run_command(
        ["python", "tests/test_final_validation.py"],
        "Schema Validation - DocAI Format"
    )


def run_structure_validation():
    """Run OCR structure validation."""
    return run_command(
        ["python", "tests/test_ocr_structure.py"],
        "Structure Validation - OCR Output"
    )


def run_docai_tests():
    """Run DocAI integration tests."""
    return run_command(
        ["python", "-m", "pytest", "tests/test_docai_schema.py", "-v"],
        "DocAI Tests - Schema and Integration"
    )


def run_docai_endpoints():
    """Run DocAI endpoint tests."""
    return run_command(
        ["python", "tests/test_docai_endpoints.py"],
        "DocAI Tests - Endpoint Testing"
    )


def run_docai_integration():
    """Run comprehensive DocAI integration test."""
    return run_command(
        ["python", "tests/test_docai_integration.py"],
        "DocAI Tests - Comprehensive Integration"
    )


def check_test_requirements():
    """Check if test requirements are installed."""
    print("\n🔍 Checking Test Requirements")
    print("=" * 60)
    
    required_packages = [
        "pytest", "fastapi", "httpx", "google-cloud-vision"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {missing_packages}")
        print("Install with: pip install -r tests/test_requirements.txt")
        return False
    else:
        print("✅ All test requirements satisfied")
        return True


def run_all_tests(fast_mode: bool = False):
    """
    Run all tests in sequence.
    
    Args:
        fast_mode: Skip slower integration tests
    """
    print("🚀 AI Backend - Comprehensive Test Suite")
    print("🏗  Router-Based Architecture")
    print("=" * 80)
    
    # Check requirements first
    if not check_test_requirements():
        print("\n❌ Test requirements not satisfied. Exiting.")
        return False
    
    # Test router migration
    if not test_router_migration():
        print("\n❌ Router migration test failed. Exiting.")
        return False
    
    # Track results
    test_results = []
    
    # Run unit tests
    success, _ = run_unit_tests()
    test_results.append(("Unit Tests - OCR", success))
    
    success, _ = run_parsing_tests()
    test_results.append(("Unit Tests - Parsing", success))
    
    success, _ = run_docai_tests()
    test_results.append(("DocAI Schema Tests", success))
    
    success, _ = run_docai_endpoints()
    test_results.append(("DocAI Endpoint Tests", success))
    
    success, _ = run_docai_integration()
    test_results.append(("DocAI Integration Tests", success))
    
    # Run validation tests
    success, _ = run_schema_validation()
    test_results.append(("Schema Validation", success))
    
    success, _ = run_structure_validation()
    test_results.append(("Structure Validation", success))
    
    # Run integration tests (slower)
    if not fast_mode:
        print("\n⚠️  Integration tests require the FastAPI server to be running")
        print("   Start server: python main.py")
        print("   Or skip with --fast flag")
        
        response = input("\nContinue with integration tests? (y/n): ")
        if response.lower().startswith('y'):
            success, _ = run_integration_tests()
            test_results.append(("Integration Tests", success))
    else:
        print("\n⏭  Skipping integration tests (fast mode)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_name:<30} {status}")
    
    print(f"\nResults: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your API is ready for production.")
        return True
    else:
        print(f"\n❌ {total - passed} test suite(s) failed. Please review the output above.")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test runner for AI Backend Router Architecture"
    )
    parser.add_argument(
        "--fast", 
        action="store_true",
        help="Skip integration tests (faster execution)"
    )
    parser.add_argument(
        "--test",
        choices=[
            "migration", "unit", "parsing", "integration", 
            "schema", "structure", "docai", "docai-endpoints", 
            "docai-integration", "all"
        ],
        default="all",
        help="Specific test suite to run"
    )
    
    args = parser.parse_args()
    
    if args.test == "migration":
        success = test_router_migration()
    elif args.test == "unit":
        success, _ = run_unit_tests()
    elif args.test == "parsing":
        success, _ = run_parsing_tests()
    elif args.test == "integration":
        success, _ = run_integration_tests()
    elif args.test == "schema":
        success, _ = run_schema_validation()
    elif args.test == "structure":
        success, _ = run_structure_validation()
    elif args.test == "docai":
        success, _ = run_docai_tests()
    elif args.test == "docai-endpoints":
        success, _ = run_docai_endpoints()
    elif args.test == "docai-integration":
        success, _ = run_docai_integration()
    else:  # all
        success = run_all_tests(fast_mode=args.fast)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()