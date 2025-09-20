#!/usr/bin/env python3
"""
Quick Orchestration Validation Script

This script performs a rapid validation of the orchestration system
to ensure all components are working correctly with the new user session structure.

Usage:
    python docs/validate_orchestration.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing Imports...")
    try:
        from services.project_utils import (
            get_user_session_structure, 
            get_username_from_env,
            generate_user_uid
        )
        from services.util_services import PDFToImageConverter
        from fastapi.testclient import TestClient
        from main import app
        print("   ✅ All imports successful")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_user_session_utilities():
    """Test user session utility functions."""
    print("🔧 Testing User Session Utilities...")
    try:
        from services.project_utils import (
            get_username_from_env,
            generate_user_uid,
            get_user_session_structure
        )
        
        username = get_username_from_env()
        uid = generate_user_uid("test_document.pdf")
        session = get_user_session_structure("test_document.pdf", username, uid)
        
        print(f"   ✅ Username: {username}")
        print(f"   ✅ UID: {uid}")
        print(f"   ✅ Session ID: {session['user_session_id']}")
        print(f"   ✅ Base Path: {session['base_path']}")
        
        return True
    except Exception as e:
        print(f"   ❌ User session utilities failed: {e}")
        return False

def test_api_health():
    """Test API health endpoint."""
    print("🌐 Testing API Health...")
    try:
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health endpoint: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"   ❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ API health test failed: {e}")
        return False

def test_pdf_processing():
    """Test PDF processing with user session structure."""
    print("📄 Testing PDF Processing...")
    try:
        from services.util_services import PDFToImageConverter
        from services.project_utils import get_username_from_env
        
        # Check if test file exists
        test_pdf = project_root / "data" / "uploads" / "testing-ocr-pdf-1.pdf"
        if not test_pdf.exists():
            print("   ⚠️  Test PDF not found, skipping processing test")
            return True
        
        username = get_username_from_env()
        converter = PDFToImageConverter(data_root=str(project_root / "data"), username=username)
        
        # Process PDF
        uid, images, metadata = converter.convert_pdf_to_images(str(test_pdf))
        
        print(f"   ✅ PDF processed: UID {uid}")
        print(f"   ✅ Images created: {len(images)}")
        print(f"   ✅ User session path: {metadata['output_info']['folder_path']}")
        
        return True
    except Exception as e:
        print(f"   ❌ PDF processing failed: {e}")
        return False

def check_user_session_folders():
    """Check existing user session folders."""
    print("📁 Checking User Session Folders...")
    try:
        processed_dir = project_root / "data" / "processed"
        if not processed_dir.exists():
            print("   ⚠️  No processed directory found")
            return True
        
        folders = [f for f in processed_dir.iterdir() if f.is_dir()]
        user_session_folders = [f for f in folders if "-" in f.name]
        
        print(f"   📊 Total folders: {len(folders)}")
        print(f"   📊 User session folders: {len(user_session_folders)}")
        
        if user_session_folders:
            # Show newest few folders
            sorted_folders = sorted(user_session_folders, key=lambda x: x.stat().st_mtime, reverse=True)
            print("   📁 Recent user session folders:")
            for folder in sorted_folders[:3]:
                print(f"      • {folder.name}")
                # Check subdirectories
                subdirs = [d.name for d in folder.iterdir() if d.is_dir()]
                expected_dirs = ["artifacts", "uploads", "pipeline", "metadata", "diagnostics"]
                present_dirs = [d for d in expected_dirs if d in subdirs]
                print(f"        Subdirs: {len(present_dirs)}/{len(expected_dirs)} ({', '.join(present_dirs)})")
        
        return True
    except Exception as e:
        print(f"   ❌ Folder check failed: {e}")
        return False

def generate_report():
    """Generate a validation report."""
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("User Session Utilities", test_user_session_utilities),
        ("API Health", test_api_health),
        ("PDF Processing", test_pdf_processing),
        ("User Session Folders", check_user_session_folders)
    ]
    
    results = {}
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print()
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed += 1
        except Exception as e:
            print(f"   ❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    print(f"\n🎯 RESULTS: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Orchestration system is ready.")
        status = "READY"
    elif passed >= total * 0.8:
        print("✅ MOSTLY WORKING - Minor issues detected.")
        status = "MOSTLY_READY"
    else:
        print("⚠️  ISSUES DETECTED - Review failed tests.")
        status = "NEEDS_ATTENTION"
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "tests_passed": passed,
        "tests_total": total,
        "success_rate": (passed/total)*100,
        "test_results": results
    }
    
    report_file = project_root / "docs" / "validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Report saved: {report_file}")
    
    return passed == total

def main():
    """Main validation function."""
    print("🧪 ORCHESTRATION VALIDATION")
    print("=" * 50)
    print(f"Project: {project_root}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = generate_report()
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Validation crashed: {e}")
        sys.exit(1)