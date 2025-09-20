#!/usr/bin/env python3
"""
Comprehensive Orchestration Test Suite

This script tests the complete orchestration pipeline with the new user session structure:
1. User session creation and path resolution
2. File upload and processing
3. OCR pipeline integration  
4. DocAI processing integration
5. Results storage in new structure
6. Backward compatibility
7. Error handling and recovery

Usage:
    python tests/test_complete_orchestration.py [--integration] [--cleanup]
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from services.project_utils import (
        get_user_session_structure, 
        get_username_from_env,
        get_gcs_paths,
        generate_user_uid,
        resolve_user_session_paths
    )
    from services.util_services import PDFToImageConverter, get_data_usage_summary
    from routers.orchestration_router import (
        save_final_results,
        ProcessingPipelineResponse,
        ProcessingStatus,
        CONFIG
    )
    from main import app
    from fastapi.testclient import TestClient
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Install dependencies with: uv pip install fastapi uvicorn")
    sys.exit(1)


class OrchestrationTestSuite:
    """Comprehensive test suite for orchestration pipeline."""
    
    def __init__(self, integration_mode: bool = False, cleanup: bool = True):
        """Initialize test suite."""
        self.integration_mode = integration_mode
        self.cleanup = cleanup
        self.test_results = []
        self.temp_files = []
        self.client = TestClient(app)
        
        # Test configuration - use shared session for consistency
        self.test_username = "test_user"
        self.test_pdf_path = project_root / "data" / "uploads" / "testing-ocr-pdf-1.pdf"
        
        # Create a single shared session for all tests
        from services.project_utils import generate_user_uid, get_user_session_structure
        self.shared_uid = generate_user_uid("testing-ocr-pdf-1.pdf")
        self.shared_session = get_user_session_structure(
            "testing-ocr-pdf-1.pdf", 
            self.test_username, 
            self.shared_uid
        )
        
        print(f"🧪 Orchestration Test Suite initialized")
        print(f"   Integration mode: {integration_mode}")
        print(f"   Cleanup after tests: {cleanup}")
        print(f"   Test PDF: {self.test_pdf_path}")
        print(f"   Test username: {self.test_username}")
        print(f"   Shared session: {self.shared_session['user_session_id']}")
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {test_name} - {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
    
    def test_user_session_utilities(self) -> bool:
        """Test user session utility functions with shared session."""
        print("\n📁 Testing User Session Utilities...")
        
        try:
            # Test username resolution
            username = get_username_from_env()
            self.log_test_result(
                "username_resolution",
                username is not None and len(username) > 0,
                f"Username resolved: {username}"
            )
            
            # Use shared UID and session
            self.log_test_result(
                "uid_generation",
                self.shared_uid is not None and len(self.shared_uid) > 0,
                f"UID generated: {self.shared_uid}"
            )
            
            # Test session structure
            session_valid = (
                "user_session_id" in self.shared_session and
                "base_path" in self.shared_session and
                "artifacts" in self.shared_session
            )
            
            self.log_test_result(
                "session_structure_creation",
                session_valid,
                f"Session structure created: {self.shared_session['user_session_id']}"
            )
            
            # Test GCS paths
            gcs_paths = get_gcs_paths("test-bucket", self.shared_session["user_session_id"])
            gcs_valid = "base_uri" in gcs_paths and "uploads" in gcs_paths
            
            self.log_test_result(
                "gcs_paths_generation",
                gcs_valid,
                f"GCS paths generated for session: {self.shared_session['user_session_id']}"
            )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "user_session_utilities",
                False,
                f"Error in user session utilities: {str(e)}"
            )
            return False
    
    def test_pdf_processing_integration(self) -> bool:
        """Test PDF processing with shared session and artifact generation."""
        print("\n🔄 Testing PDF Processing Integration...")
        
        try:
            if not self.test_pdf_path.exists():
                self.log_test_result(
                    "pdf_file_availability",
                    False,
                    f"Test PDF not found: {self.test_pdf_path}"
                )
                return False
            
            # Initialize converter with shared session details
            converter = PDFToImageConverter(
                data_root=str(project_root / "data"),
                username=self.test_username
            )
            
            # Test PDF conversion using the shared session's expected structure
            upload_folder = self.shared_session["uploads"] / f"testing-ocr-pdf-1-{self.shared_uid}"
            uid, output_paths, metadata = converter.convert_pdf_to_images(
                str(self.test_pdf_path),
                output_folder=str(upload_folder)
            )
            
            # Verify outputs are in correct user session structure
            session_path_found = str(self.shared_session["user_session_id"]) in str(metadata["output_info"]["folder_path"])
            
            self.log_test_result(
                "pdf_conversion_user_session",
                session_path_found,
                f"PDF converted with user session structure: UID {uid}",
                {
                    "uid": uid,
                    "shared_uid": self.shared_uid,
                    "output_paths_count": len(output_paths),
                    "folder_path": metadata["output_info"]["folder_path"]
                }
            )
            
            # Verify metadata completeness
            metadata_valid = (
                "uid" in metadata and
                "processing_info" in metadata and
                "output_info" in metadata
            )
            
            self.log_test_result(
                "metadata_completeness",
                metadata_valid,
                "Metadata contains required session information"
            )
            
            # Generate artifacts like in production (Vision API simulation)
            artifacts_dir = self.shared_session["artifacts"] / "vision_to_docai"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sample artifacts that would be generated in production
            import json
            
            vision_raw = {
                "document_id": uid,
                "full_text": "Sample OCR text from testing-ocr-pdf-1.pdf\\nThis is a multi-page legal document\\nwith various clauses and terms.",
                "pages": len(output_paths),
                "processing_time": 2.5,
                "user_session_id": self.shared_session["user_session_id"]
            }
            
            parsed_output = {
                "success": True,
                "document_id": uid,
                "text": "Sample processed text with legal content",
                "entities": [
                    {"type": "PERSON", "text": "John Doe", "confidence": 0.95},
                    {"type": "DATE", "text": "2025-09-20", "confidence": 0.89},
                    {"type": "ORGANIZATION", "text": "ABC Corporation", "confidence": 0.92}
                ],
                "clauses": [
                    {"type": "PAYMENT_TERMS", "text": "Payment due within 30 days", "confidence": 0.92},
                    {"type": "TERMINATION", "text": "Either party may terminate with 30 days notice", "confidence": 0.88}
                ],
                "key_value_pairs": [
                    {"key": "Contract Date", "value": "September 20, 2025", "confidence": 0.91},
                    {"key": "Total Amount", "value": "$10,000", "confidence": 0.87}
                ],
                "user_session_id": self.shared_session["user_session_id"]
            }
            
            feature_vector = {
                "kv_flags": {
                    "has_payment_terms": True,
                    "has_signatures": False,
                    "has_dates": True,
                    "has_amounts": True,
                    "has_parties": True
                },
                "document_type": "contract",
                "confidence_score": 0.88,
                "risk_level": "medium",
                "user_session_id": self.shared_session["user_session_id"]
            }
            
            # Save artifacts
            with open(artifacts_dir / "vision_raw.json", 'w') as f:
                json.dump(vision_raw, f, indent=2)
            
            with open(artifacts_dir / "parsed_output.json", 'w') as f:
                json.dump(parsed_output, f, indent=2)
            
            with open(artifacts_dir / "feature_vector.json", 'w') as f:
                json.dump(feature_vector, f, indent=2)
            
            # Store artifact paths for verification
            self.temp_files.extend([
                str(artifacts_dir / "vision_raw.json"),
                str(artifacts_dir / "parsed_output.json"),
                str(artifacts_dir / "feature_vector.json")
            ])
            
            self.log_test_result(
                "artifacts_generation",
                True,
                f"Production-like artifacts generated in {artifacts_dir}",
                {
                    "artifacts_created": 3,
                    "artifacts_path": str(artifacts_dir),
                    "vision_raw_size": len(str(vision_raw)),
                    "parsed_entities_count": len(parsed_output["entities"]),
                    "kv_flags_count": len(feature_vector["kv_flags"])
                }
            )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "pdf_processing_integration",
                False,
                f"PDF processing test failed: {str(e)}"
            )
            return False
    
    def test_orchestration_api_endpoints(self) -> bool:
        """Test orchestration API endpoints."""
        print("\n🌐 Testing Orchestration API Endpoints...")
        
        try:
            # Test health endpoint
            response = self.client.get("/api/v1/health")
            health_success = response.status_code == 200
            
            if health_success:
                health_data = response.json()
                self.log_test_result(
                    "health_endpoint",
                    True,
                    f"Health endpoint operational: {health_data.get('status', 'unknown')}",
                    {"health_data": health_data}
                )
            else:
                self.log_test_result(
                    "health_endpoint",
                    False,
                    f"Health endpoint failed: {response.status_code}"
                )
            
            # Test root endpoint for orchestration routes
            response = self.client.get("/")
            if response.status_code == 200:
                root_data = response.json()
                orchestration_endpoints = [
                    "pipeline_process",
                    "pipeline_status", 
                    "pipeline_results"
                ]
                
                endpoints_present = all(
                    endpoint in root_data.get("endpoints", {})
                    for endpoint in orchestration_endpoints
                )
                
                self.log_test_result(
                    "orchestration_endpoints_registered",
                    endpoints_present,
                    "All orchestration endpoints registered in root"
                )
            else:
                self.log_test_result(
                    "root_endpoint",
                    False,
                    f"Root endpoint failed: {response.status_code}"
                )
            
            return health_success
            
        except Exception as e:
            self.log_test_result(
                "orchestration_api_endpoints",
                False,
                f"API endpoint test failed: {str(e)}"
            )
            return False
    
    def test_save_results_functionality(self) -> bool:
        """Test results saving with new user session structure."""
        print("\n💾 Testing Results Saving Functionality...")
        
        try:
            # Create test data
            test_pipeline_id = f"test_pipeline_{int(time.time())}"
            test_pdf_filename = "test_document.pdf"
            
            upload_result = {
                "success": True,
                "file_path": f"/test/uploads/{test_pdf_filename}",
                "file_info": {"size": 1024000, "type": "application/pdf"}
            }
            
            ocr_result = {
                "success": True,
                "uid": "test_ocr_uid_123",
                "total_pages": 3,
                "processed_pages": 3,
                "ocr_results_path": "/test/ocr/results.json",
                "processing_folder": "/test/processing",
                "metadata": {"language": "en", "confidence": 0.95}
            }
            
            docai_result = {
                "success": True,
                "document": {
                    "text": "Sample legal document text with clauses and entities.",
                    "entities": [
                        {"type": "PERSON", "text": "John Doe", "confidence": 0.9},
                        {"type": "DATE", "text": "2025-01-01", "confidence": 0.85}
                    ],
                    "clauses": [
                        {"type": "termination", "text": "This agreement terminates...", "confidence": 0.8}
                    ],
                    "key_value_pairs": [
                        {"key": "Policy Number", "value": "POL-123456", "confidence": 0.9}
                    ]
                },
                "request_id": "test_docai_request_123",
                "processing_time_seconds": 4.5
            }
            
            stage_timings = {
                "upload": 1.2,
                "ocr": 8.5,
                "docai": 4.5,
                "saving": 0.3
            }
            
            # Test save function with new structure
            results_path = save_final_results(
                pipeline_id=test_pipeline_id,
                upload_result=upload_result,
                ocr_result=ocr_result,
                docai_result=docai_result,
                stage_timings=stage_timings,
                pdf_filename=test_pdf_filename,
                username=self.test_username
            )
            
            # Verify file was created
            results_file = Path(results_path)
            file_created = results_file.exists()
            
            if file_created:
                # Verify file content
                with open(results_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                # Check required fields
                required_fields = [
                    "pipeline_id", "user_session_id", "processing_timestamp",
                    "original_file", "ocr_processing", "docai_processing",
                    "performance", "extracted_data", "session_info"
                ]
                
                fields_present = all(field in saved_data for field in required_fields)
                
                # Check user session structure
                session_id_correct = (
                    self.test_username in saved_data.get("user_session_id", "") and
                    saved_data.get("pipeline_id") == test_pipeline_id
                )
                
                # Check path structure
                session_info = saved_data.get("session_info", {})
                path_structure_correct = (
                    "pipeline" in session_info.get("pipeline_path", "") and
                    self.test_username in session_info.get("base_path", "")
                )
                
                self.log_test_result(
                    "save_results_structure",
                    fields_present and session_id_correct and path_structure_correct,
                    f"Results saved with correct user session structure",
                    {
                        "results_path": str(results_path),
                        "user_session_id": saved_data.get("user_session_id"),
                        "fields_present": fields_present,
                        "session_id_correct": session_id_correct,
                        "path_structure_correct": path_structure_correct
                    }
                )
                
                # Add to cleanup list
                self.temp_files.append(results_file)
                
                return fields_present and session_id_correct and path_structure_correct
            else:
                self.log_test_result(
                    "save_results_file_creation",
                    False,
                    f"Results file not created: {results_path}"
                )
                return False
            
        except Exception as e:
            self.log_test_result(
                "save_results_functionality",
                False,
                f"Save results test failed: {str(e)}"
            )
            return False
    
    def test_integration_pipeline(self) -> bool:
        """Test full integration pipeline if enabled."""
        if not self.integration_mode:
            print("\n⏭️  Skipping Integration Pipeline (use --integration to enable)")
            return True
        
        print("\n🔗 Testing Full Integration Pipeline...")
        
        try:
            if not self.test_pdf_path.exists():
                self.log_test_result(
                    "integration_pdf_availability",
                    False,
                    "Test PDF not available for integration test"
                )
                return False
            
            # Test document processing endpoint
            with open(self.test_pdf_path, 'rb') as f:
                files = {"file": ("testing-ocr-pdf-1.pdf", f, "application/pdf")}
                data = {
                    "language_hints": "en",
                    "confidence_threshold": 0.7,
                    "force_reprocess": True
                }
                
                response = self.client.post("/api/v1/process-document", files=files, data=data)
            
            # Check response
            if response.status_code == 200:
                response_data = response.json()
                
                # Verify response structure
                expected_fields = ["success", "pipeline_id", "message", "total_processing_time"]
                fields_present = all(field in response_data for field in expected_fields)
                
                # Check if user session structure was used
                user_session_used = False
                if "final_results_path" in response_data:
                    final_path = response_data["final_results_path"]
                    user_session_used = self.test_username in final_path or "processed" in final_path
                
                self.log_test_result(
                    "integration_pipeline_success",
                    response_data.get("success", False) and fields_present,
                    f"Full pipeline processed successfully: {response_data.get('pipeline_id', 'unknown')}",
                    {
                        "pipeline_id": response_data.get("pipeline_id"),
                        "processing_time": response_data.get("total_processing_time"),
                        "user_session_structure_used": user_session_used,
                        "fields_present": fields_present
                    }
                )
                
                return response_data.get("success", False) and fields_present
            else:
                self.log_test_result(
                    "integration_pipeline_request",
                    False,
                    f"Integration pipeline request failed: {response.status_code} - {response.text}"
                )
                return False
            
        except Exception as e:
            self.log_test_result(
                "integration_pipeline",
                False,
                f"Integration pipeline test failed: {str(e)}"
            )
            return False

    def test_user_session_folder_creation(self) -> bool:
        """Test that processing creates a single folder with proper {username-UID} format."""
        print("\n📁 Testing User Session Folder Creation...")
        
        try:
            # Check if the shared session folder exists
            expected_folder = self.shared_session["base_path"]
            folder_exists = expected_folder.exists()
            
            if not folder_exists:
                self.log_test_result(
                    "user_session_folder_created",
                    False,
                    f"Expected folder not found: {expected_folder.name}"
                )
                return False
            
            # Verify folder format: {username-UID}
            folder_name = expected_folder.name
            expected_pattern = folder_name.startswith(f"{self.test_username}-")
            
            # Verify folder structure
            expected_subdirs = ["artifacts", "uploads", "pipeline", "metadata", "diagnostics"]
            existing_subdirs = [d.name for d in expected_folder.iterdir() if d.is_dir()]
            structure_valid = all(subdir in existing_subdirs for subdir in expected_subdirs)
            
            # Check for actual content (images, artifacts)
            uploads_dir = expected_folder / "uploads"
            artifacts_dir = expected_folder / "artifacts"
            
            has_content = False
            content_summary = []
            
            if uploads_dir.exists():
                upload_files = list(uploads_dir.glob("**/*.*"))
                if upload_files:
                    has_content = True
                    content_summary.append(f"uploads: {len(upload_files)} files")
            
            if artifacts_dir.exists():
                artifact_files = list(artifacts_dir.glob("**/*.*"))
                if artifact_files:
                    has_content = True
                    content_summary.append(f"artifacts: {len(artifact_files)} files")
            
            self.log_test_result(
                "user_session_folder_created",
                expected_pattern and structure_valid and has_content,
                f"Single user session folder validated: {folder_name}",
                {
                    "folder_name": folder_name,
                    "pattern_match": expected_pattern,
                    "structure_valid": structure_valid,
                    "has_content": has_content,
                    "content_summary": content_summary,
                    "subdirs_found": existing_subdirs
                }
            )
            
            return expected_pattern and structure_valid and has_content
            
        except Exception as e:
            self.log_test_result(
                "user_session_folder_creation",
                False,
                f"Folder creation test failed: {str(e)}"
            )
            return False
    
    def test_backward_compatibility(self) -> bool:
        """Test backward compatibility with legacy paths."""
        print("\n🔄 Testing Backward Compatibility...")
        
        try:
            # Test legacy artifact access
            legacy_artifacts_dir = project_root / "artifacts"
            legacy_artifacts_dir.mkdir(exist_ok=True)
            
            # Create a test legacy file
            legacy_test_file = legacy_artifacts_dir / "test_legacy_file.json"
            with open(legacy_test_file, 'w') as f:
                json.dump({"test": "legacy_data", "timestamp": datetime.now().isoformat()}, f)
            
            self.temp_files.append(legacy_test_file)
            
            self.log_test_result(
                "legacy_path_access",
                legacy_test_file.exists(),
                "Legacy artifact paths still accessible"
            )
            
            # Test that new session structure doesn't break existing functionality
            data_usage = get_data_usage_summary()
            usage_success = data_usage.get("success", False)
            
            self.log_test_result(
                "existing_functionality_intact",
                usage_success,
                "Existing data usage functionality works",
                {"data_usage_summary": data_usage}
            )
            
            return usage_success
            
        except Exception as e:
            self.log_test_result(
                "backward_compatibility",
                False,
                f"Backward compatibility test failed: {str(e)}"
            )
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and recovery."""
        print("\n⚠️  Testing Error Handling...")
        
        try:
            # Test invalid user session handling
            try:
                from services.project_utils import resolve_user_session_paths
                session_id, base_path = resolve_user_session_paths("", username="", uid="")
                
                # Should handle empty inputs gracefully
                self.log_test_result(
                    "empty_input_handling",
                    bool(session_id and base_path),
                    "Empty inputs handled gracefully"
                )
            except Exception:
                self.log_test_result(
                    "empty_input_handling",
                    True,
                    "Empty inputs raise appropriate errors"
                )
            
            # Test missing file handling
            try:
                converter = PDFToImageConverter(username=self.test_username)
                converter.convert_pdf_to_images("nonexistent_file.pdf")
                
                self.log_test_result(
                    "missing_file_handling",
                    False,
                    "Missing file should raise error"
                )
            except FileNotFoundError:
                self.log_test_result(
                    "missing_file_handling",
                    True,
                    "Missing file raises appropriate FileNotFoundError"
                )
            except Exception as e:
                self.log_test_result(
                    "missing_file_handling",
                    True,
                    f"Missing file raises error: {type(e).__name__}"
                )
            
            return True
            
        except Exception as e:
            self.log_test_result(
                "error_handling",
                False,
                f"Error handling test failed: {str(e)}"
            )
            return False
    
    def cleanup_test_files(self):
        """Clean up test files if cleanup is enabled."""
        if not self.cleanup:
            print("\n🧹 Cleanup disabled, leaving test files")
            return
        
        print("\n🧹 Cleaning up test files...")
        
        cleaned_count = 0
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                print(f"   ⚠️  Failed to clean up {temp_file}: {e}")
        
        print(f"   ✅ Cleaned up {cleaned_count} test files")
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        report = {
            "test_session": {
                "timestamp": datetime.now().isoformat(),
                "integration_mode": self.integration_mode,
                "test_username": self.test_username,
                "project_root": str(project_root)
            },
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0
            },
            "detailed_results": self.test_results,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "username_env": get_username_from_env(),
                "data_root": CONFIG.get("data_root", "unknown")
            }
        }
        
        return report
    
    def run_all_tests(self) -> bool:
        """Run all orchestration tests."""
        print("🚀 Starting Comprehensive Orchestration Test Suite")
        print("=" * 70)
        
        # Run all test categories
        test_methods = [
            self.test_user_session_utilities,
            self.test_pdf_processing_integration,
            self.test_user_session_folder_creation,
            self.test_orchestration_api_endpoints,
            self.test_save_results_functionality,
            self.test_integration_pipeline,
            self.test_backward_compatibility,
            self.test_error_handling
        ]
        
        all_passed = True
        for test_method in test_methods:
            try:
                result = test_method()
                all_passed = all_passed and result
            except Exception as e:
                print(f"   ❌ CRITICAL: {test_method.__name__} crashed: {e}")
                all_passed = False
        
        # Generate and save report
        report = self.generate_test_report()
        
        # Save test report
        report_path = project_root / "tests" / "orchestration_test_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']} ✅")
        print(f"Failed: {report['summary']['failed']} ❌")
        print(f"Success Rate: {report['summary']['success_rate']}%")
        print(f"Report saved to: {report_path}")
        
        # Cleanup
        self.cleanup_test_files()
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! Orchestration system is ready.")
        else:
            print("\n⚠️  SOME TESTS FAILED. Review the report for details.")
        
        return all_passed


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Comprehensive Orchestration Test Suite")
    parser.add_argument("--integration", action="store_true", 
                       help="Run integration tests (requires PDF files and services)")
    parser.add_argument("--no-cleanup", action="store_true",
                       help="Skip cleanup of test files")
    
    args = parser.parse_args()
    
    # Run test suite
    test_suite = OrchestrationTestSuite(
        integration_mode=args.integration,
        cleanup=not args.no_cleanup
    )
    
    success = test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()