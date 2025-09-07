"""
Unit test runner for AI backend preprocessing services.

This module provides a unified entry point for running all unit tests
in the preprocessing services including OCR processing and text parsing.
"""

import os
import sys
import unittest

# Add current directory to path for test imports
sys.path.insert(0, os.path.dirname(__file__))

# Import test modules
from test_ocr_processing import TestOCRResult, TestGoogleVisionOCR, TestGoogleVisionOCRIntegration
from test_parsing import TestParsedDocument, TestLocalTextParser, TestLocalTextParserIntegration


def create_test_suite():
    """
    Create a comprehensive test suite for all preprocessing services.
    
    Returns:
        unittest.TestSuite: Complete test suite with all test cases
    """
    suite = unittest.TestSuite()
    
    # OCR Processing Tests
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestOCRResult))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGoogleVisionOCR))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGoogleVisionOCRIntegration))
    
    # Text Parsing Tests
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestParsedDocument))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLocalTextParser))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLocalTextParserIntegration))
    
    return suite


def run_tests(verbosity=2):
    """
    Run all unit tests with specified verbosity.
    
    Args:
        verbosity: Test output verbosity level (0-2)
        
    Returns:
        unittest.TestResult: Test execution results
    """
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


def run_specific_service_tests(service_name, verbosity=2):
    """
    Run tests for a specific service.
    
    Args:
        service_name: Name of service ('ocr' or 'parsing')
        verbosity: Test output verbosity level
        
    Returns:
        unittest.TestResult: Test execution results
    """
    suite = unittest.TestSuite()
    
    if service_name.lower() == 'ocr':
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestOCRResult))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGoogleVisionOCR))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGoogleVisionOCRIntegration))
    elif service_name.lower() == 'parsing':
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestParsedDocument))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLocalTextParser))
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLocalTextParserIntegration))
    else:
        raise ValueError(f"Unknown service: {service_name}. Use 'ocr' or 'parsing'")
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


if __name__ == '__main__':
    """
    Command-line interface for running tests.
    
    Usage:
        python unit-tests.py              # Run all tests
        python unit-tests.py ocr          # Run OCR tests only
        python unit-tests.py parsing      # Run parsing tests only
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Run unit tests for preprocessing services')
    parser.add_argument('service', nargs='?', choices=['ocr', 'parsing'], 
                       help='Specific service to test (optional)')
    parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2], default=2,
                       help='Test output verbosity level')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("AI Backend Preprocessing Services - Unit Tests")
    print("=" * 70)
    
    try:
        if args.service:
            print(f"Running tests for {args.service.upper()} service...")
            result = run_specific_service_tests(args.service, args.verbosity)
        else:
            print("Running all unit tests...")
            result = run_tests(args.verbosity)
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped)}")
        
        if result.failures:
            print(f"\nFAILURES ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print(f"\nERRORS ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        if result.skipped:
            print(f"\nSKIPPED ({len(result.skipped)}):")
            for test, reason in result.skipped:
                print(f"  - {test}: {reason}")
        
        # Exit with appropriate code
        exit_code = 0 if result.wasSuccessful() else 1
        print(f"\nTests {'PASSED' if result.wasSuccessful() else 'FAILED'}!")
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)