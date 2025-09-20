#!/usr/bin/env python3
"""
DocAI Output Diagnostic Validation Script

This script tests the DocAI output diagnostic system to ensure it properly
tracks and validates all output files created during document processing.

Usage:
    python tests/test_docai_output_validation.py

Features:
- Validates DocAI output tracking functionality
- Tests file integrity verification
- Generates comprehensive output mapping
- Provides runtime verification of all artifacts
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_docai_output_diagnostic import DocAIOutputTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocAIOutputValidationTest:
    """
    Test suite for DocAI output diagnostic system validation.
    """
    
    def __init__(self):
        """Initialize validation test."""
        self.project_root = project_root
        self.test_artifacts_dir = Path("artifacts/docai_validation_test")
        self.test_artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_results = {
            'test_session_id': f"validation_{int(datetime.now().timestamp())}",
            'start_time': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': {}
        }
        
        logger.info("🧪 DocAI Output Validation Test initialized")
    
    def test_tracker_initialization(self) -> bool:
        """Test DocAI output tracker initialization."""
        test_name = "tracker_initialization"
        logger.info(f"🔍 Testing: {test_name}")
        
        try:
            tracker = DocAIOutputTracker(artifacts_base_dir="artifacts")
            
            # Verify tracker has required attributes
            required_attrs = ['tracking_session', 'known_output_patterns', 'artifacts_base_dir']
            for attr in required_attrs:
                if not hasattr(tracker, attr):
                    raise AssertionError(f"Tracker missing required attribute: {attr}")
            
            # Verify known output patterns are complete
            expected_patterns = [
                'artifacts/vision_to_docai/docai_raw_full.json',
                'artifacts/vision_to_docai/feature_vector.json',
                'artifacts/vision_to_docai/diagnostics.json',
                'artifacts/vision_to_docai/parsed_output.json'
            ]
            
            for pattern in expected_patterns:
                if pattern not in tracker.known_output_patterns:
                    raise AssertionError(f"Missing expected output pattern: {pattern}")
            
            self.test_results['test_details'][test_name] = {
                'status': 'passed',
                'session_id': tracker.tracking_session['session_id'],
                'patterns_tracked': len(tracker.known_output_patterns)
            }
            
            logger.info(f"✅ {test_name}: PASSED")
            self.test_results['tests_passed'] += 1
            return True
            
        except Exception as e:
            self.test_results['test_details'][test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ {test_name}: FAILED - {e}")
            self.test_results['tests_failed'] += 1
            return False
    
    def test_file_monitoring(self) -> bool:
        """Test file monitoring and tracking capabilities."""
        test_name = "file_monitoring"
        logger.info(f"🔍 Testing: {test_name}")
        
        try:
            tracker = DocAIOutputTracker(artifacts_base_dir="artifacts")
            
            # Start monitoring
            tracker.start_monitoring()
            
            # Create test files to simulate DocAI output
            test_files = [
                "artifacts/vision_to_docai/test_docai_raw.json",
                "artifacts/vision_to_docai/test_parsed_output.json"
            ]
            
            created_files = []
            for test_file in test_files:
                file_path = Path(test_file)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                test_content = {
                    "test": True,
                    "timestamp": datetime.now().isoformat(),
                    "content": "This is a test file for DocAI output validation"
                }
                
                with open(file_path, 'w') as f:
                    json.dump(test_content, f, indent=2)
                
                created_files.append(file_path)
                
                # Track the file operation
                tracker.track_file_operation(
                    operation_type="create",
                    file_path=str(file_path),
                    details={"test_file": True, "size_bytes": file_path.stat().st_size}
                )
            
            # Verify tracking session has operations
            operations = tracker.tracking_session.get('file_operations', [])
            if len(operations) == 0:
                raise AssertionError("No file operations tracked")
            
            # Clean up test files
            for file_path in created_files:
                if file_path.exists():
                    file_path.unlink()
            
            self.test_results['test_details'][test_name] = {
                'status': 'passed',
                'operations_tracked': len(operations),
                'test_files_created': len(created_files)
            }
            
            logger.info(f"✅ {test_name}: PASSED")
            self.test_results['tests_passed'] += 1
            return True
            
        except Exception as e:
            self.test_results['test_details'][test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ {test_name}: FAILED - {e}")
            self.test_results['tests_failed'] += 1
            return False
    
    def test_file_verification(self) -> bool:
        """Test file integrity verification capabilities."""
        test_name = "file_verification"
        logger.info(f"🔍 Testing: {test_name}")
        
        try:
            tracker = DocAIOutputTracker(artifacts_base_dir="artifacts")
            
            # Create test file with known content
            test_file = Path("artifacts/vision_to_docai/verification_test.json")
            test_file.parent.mkdir(parents=True, exist_ok=True)
            
            test_content = {
                "text": "Sample document text for verification testing",
                "entities": [
                    {"type": "PERSON", "text": "John Doe", "confidence": 0.95},
                    {"type": "DATE", "text": "2025-01-01", "confidence": 0.88}
                ],
                "pages": [
                    {"page_number": 1, "width": 612, "height": 792}
                ]
            }
            
            with open(test_file, 'w') as f:
                json.dump(test_content, f, indent=2)
            
            # Verify the file
            verification = tracker.verify_file_integrity(test_file)
            
            # Check verification results
            expected_checks = ['exists', 'size_bytes', 'valid_json', 'content_type']
            for check in expected_checks:
                if check not in verification:
                    raise AssertionError(f"Missing verification check: {check}")
            
            if not verification['exists']:
                raise AssertionError("File verification failed - file should exist")
            
            if not verification['valid_json']:
                raise AssertionError("File verification failed - JSON should be valid")
            
            if verification['size_bytes'] == 0:
                raise AssertionError("File verification failed - file should not be empty")
            
            # Clean up
            test_file.unlink()
            
            self.test_results['test_details'][test_name] = {
                'status': 'passed',
                'file_size_bytes': verification['size_bytes'],
                'verification_checks': len(verification),
                'content_valid': verification['valid_json']
            }
            
            logger.info(f"✅ {test_name}: PASSED")
            self.test_results['tests_passed'] += 1
            return True
            
        except Exception as e:
            self.test_results['test_details'][test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ {test_name}: FAILED - {e}")
            self.test_results['tests_failed'] += 1
            return False
    
    def test_output_mapping_generation(self) -> bool:
        """Test output mapping artifact generation."""
        test_name = "output_mapping_generation"
        logger.info(f"🔍 Testing: {test_name}")
        
        try:
            tracker = DocAIOutputTracker(artifacts_base_dir="artifacts")
            
            # Start monitoring and simulate processing
            tracker.start_monitoring()
            
            # Simulate creating some DocAI output files
            test_outputs = {
                "artifacts/vision_to_docai/test_raw.json": {"text": "Test document", "entities": []},
                "artifacts/vision_to_docai/test_features.json": {"features": {"word_count": 2}}
            }
            
            for file_path, content in test_outputs.items():
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    json.dump(content, f)
            
            # Capture post-processing state
            post_state = tracker.capture_post_processing_state()
            
            # Generate output mapping
            output_mapping = tracker.generate_output_mapping()
            
            # Verify output mapping structure
            required_sections = ['session_info', 'docai_output_files', 'verification_summary']
            for section in required_sections:
                if section not in output_mapping:
                    raise AssertionError(f"Missing output mapping section: {section}")
            
            # Verify session info
            session_info = output_mapping['session_info']
            if 'session_id' not in session_info or 'generation_time' not in session_info:
                raise AssertionError("Incomplete session info in output mapping")
            
            # Clean up test files
            for file_path in test_outputs.keys():
                path = Path(file_path)
                if path.exists():
                    path.unlink()
            
            self.test_results['test_details'][test_name] = {
                'status': 'passed',
                'mapping_sections': len(output_mapping),
                'files_in_mapping': len(output_mapping.get('docai_output_files', {})),
                'session_id': session_info['session_id']
            }
            
            logger.info(f"✅ {test_name}: PASSED")
            self.test_results['tests_passed'] += 1
            return True
            
        except Exception as e:
            self.test_results['test_details'][test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ {test_name}: FAILED - {e}")
            self.test_results['tests_failed'] += 1
            return False
    
    def test_diagnostic_artifacts_saving(self) -> bool:
        """Test diagnostic artifacts saving functionality."""
        test_name = "diagnostic_artifacts_saving"
        logger.info(f"🔍 Testing: {test_name}")
        
        try:
            tracker = DocAIOutputTracker(artifacts_base_dir="artifacts")
            
            # Setup tracking session with some data
            tracker.start_monitoring()
            tracker.capture_post_processing_state()
            tracker.generate_output_mapping()
            
            # Save diagnostic artifacts
            saved_artifacts = tracker.save_diagnostic_artifacts(
                output_dir=str(self.test_artifacts_dir / "diagnostic_test")
            )
            
            # Verify artifacts were saved
            expected_artifacts = ['output_mapping', 'tracking_session', 'verification_details', 'summary_report']
            for artifact_type in expected_artifacts:
                if artifact_type not in saved_artifacts:
                    raise AssertionError(f"Missing saved artifact: {artifact_type}")
                
                artifact_path = Path(saved_artifacts[artifact_type])
                if not artifact_path.exists():
                    raise AssertionError(f"Artifact file does not exist: {artifact_path}")
                
                if artifact_path.stat().st_size == 0:
                    raise AssertionError(f"Artifact file is empty: {artifact_path}")
            
            # Test specific artifact content
            mapping_file = Path(saved_artifacts['output_mapping'])
            with open(mapping_file, 'r') as f:
                mapping_content = json.load(f)
            
            if 'session_info' not in mapping_content:
                raise AssertionError("Output mapping missing session info")
            
            self.test_results['test_details'][test_name] = {
                'status': 'passed',
                'artifacts_saved': len(saved_artifacts),
                'artifacts_list': list(saved_artifacts.keys()),
                'output_directory': str(self.test_artifacts_dir / "diagnostic_test")
            }
            
            logger.info(f"✅ {test_name}: PASSED")
            self.test_results['tests_passed'] += 1
            return True
            
        except Exception as e:
            self.test_results['test_details'][test_name] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ {test_name}: FAILED - {e}")
            self.test_results['tests_failed'] += 1
            return False
    
    def run_all_tests(self) -> dict:
        """Run all validation tests."""
        logger.info("🚀 Starting DocAI Output Diagnostic Validation Tests")
        logger.info("=" * 70)
        
        # Define test suite
        tests = [
            self.test_tracker_initialization,
            self.test_file_monitoring,
            self.test_file_verification,
            self.test_output_mapping_generation,
            self.test_diagnostic_artifacts_saving
        ]
        
        # Run all tests
        for test_func in tests:
            test_func()
        
        # Calculate final results
        total_tests = self.test_results['tests_passed'] + self.test_results['tests_failed']
        success_rate = (self.test_results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
        
        self.test_results.update({
            'end_time': datetime.now().isoformat(),
            'total_tests': total_tests,
            'success_rate': round(success_rate, 1)
        })
        
        return self.test_results
    
    def print_test_summary(self) -> None:
        """Print comprehensive test summary."""
        results = self.test_results
        
        print("\n" + "=" * 70)
        print("📊 DOCAI OUTPUT DIAGNOSTIC VALIDATION SUMMARY")
        print("=" * 70)
        
        print(f"Session ID: {results['test_session_id']}")
        print(f"Start Time: {results['start_time']}")
        print(f"End Time: {results.get('end_time', 'N/A')}")
        
        print(f"\n📈 Test Results:")
        print(f"  Total Tests: {results['total_tests']}")
        print(f"  Tests Passed: {results['tests_passed']} ✅")
        print(f"  Tests Failed: {results['tests_failed']} ❌")
        print(f"  Success Rate: {results['success_rate']}%")
        
        print(f"\n📋 Test Details:")
        for test_name, details in results['test_details'].items():
            status_icon = "✅" if details['status'] == 'passed' else "❌"
            print(f"  {status_icon} {test_name.replace('_', ' ').title()}")
            
            if details['status'] == 'failed' and 'error' in details:
                print(f"      Error: {details['error']}")
        
        # Overall assessment
        if results['success_rate'] == 100:
            print(f"\n🎉 ALL TESTS PASSED - DocAI Output Diagnostic System is fully functional!")
        elif results['success_rate'] >= 80:
            print(f"\n⚠️  MOSTLY PASSING - DocAI Output Diagnostic System is mostly functional")
        else:
            print(f"\n❌ MULTIPLE FAILURES - DocAI Output Diagnostic System needs attention")
        
        print("=" * 70)
    
    def save_test_results(self) -> str:
        """Save test results to file."""
        results_file = self.test_artifacts_dir / "validation_test_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Test results saved to: {results_file}")
        return str(results_file)

def main():
    """Main test execution function."""
    print("🧪 DocAI Output Diagnostic Validation Test Suite")
    print("=" * 60)
    
    # Initialize and run tests
    validator = DocAIOutputValidationTest()
    test_results = validator.run_all_tests()
    
    # Print summary
    validator.print_test_summary()
    
    # Save results
    results_file = validator.save_test_results()
    
    # Determine exit code
    if test_results['success_rate'] == 100:
        exit_code = 0
    elif test_results['success_rate'] >= 80:
        exit_code = 1
    else:
        exit_code = 2
    
    print(f"\n🏁 Test suite completed with exit code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)