#!/usr/bin/env python3
"""
Unified Test Runner for AI Backend Document Processing API

This script provides a centralized way to run all tests in the tests/ directory
with proper path configuration and comprehensive reporting.
"""

import os
import sys
import unittest
import subprocess
import argparse
import importlib.util
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class TestRunner:
    """Unified test runner for all AI Backend tests."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "test_results": {}
        }
        
        # Add project root to Python path
        sys.path.insert(0, str(self.project_root))
    
    def discover_test_files(self) -> List[Path]:
        """Discover all test files in the tests directory."""
        test_files = []
        
        # Pattern-based discovery
        patterns = [
            "test_*.py",
            "*_test.py", 
            "unit-tests.py"
        ]
        
        for pattern in patterns:
            test_files.extend(self.test_dir.glob(pattern))
        
        # Remove specific files that are not standard test files
        exclude_files = {
            "create_test_image.py",  # Utility script
            "__init__.py"            # Package file
        }
        
        test_files = [f for f in test_files if f.name not in exclude_files]
        
        return sorted(test_files)
    
    def run_unittest_file(self, test_file: Path) -> Dict[str, Any]:
        """Run a unittest file and return results."""
        print(f"\\n{'='*60}")
        print(f"Running: {test_file.name}")
        print(f"{'='*60}")
        
        result = {
            "file": test_file.name,
            "status": "success",
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "output": [],
            "error_details": []
        }
        
        try:
            # Try to import and run as unittest module
            spec = importlib.util.spec_from_file_location(
                test_file.stem, test_file
            )
            module = importlib.util.module_from_spec(spec)
            
            # Execute the module
            spec.loader.exec_module(module)
            
            # Check if it has unittest test cases
            if hasattr(module, 'unittest') or any(
                hasattr(getattr(module, attr), '__bases__') and 
                any(base.__name__ == 'TestCase' for base in getattr(module, attr).__bases__)
                for attr in dir(module) if not attr.startswith('_')
            ):
                # Run as unittest
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromModule(module)
                runner = unittest.TextTestRunner(
                    verbosity=2, 
                    stream=sys.stdout,
                    buffer=True
                )
                test_result = runner.run(suite)
                
                result["tests_run"] = test_result.testsRun
                result["failures"] = len(test_result.failures)
                result["errors"] = len(test_result.errors)
                result["skipped"] = len(test_result.skipped)
                
                if test_result.failures or test_result.errors:
                    result["status"] = "failed"
                    result["error_details"] = [
                        str(failure) for failure in test_result.failures + test_result.errors
                    ]
            
            else:
                # Run as script with main function
                if hasattr(module, 'main'):
                    print(f"Running {test_file.name} as script...")
                    module.main()
                    result["tests_run"] = 1
                    result["status"] = "success"
                else:
                    print(f"No tests found in {test_file.name}")
                    result["status"] = "skipped"
                    result["skipped"] = 1
        
        except Exception as e:
            print(f"Error running {test_file.name}: {e}")
            result["status"] = "error"
            result["errors"] = 1
            result["error_details"] = [str(e)]
        
        return result
    
    def run_script_file(self, test_file: Path) -> Dict[str, Any]:
        """Run a test script and return results."""
        print(f"\\n{'='*60}")
        print(f"Running script: {test_file.name}")
        print(f"{'='*60}")
        
        result = {
            "file": test_file.name,
            "status": "success",
            "tests_run": 1,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "output": [],
            "error_details": []
        }
        
        try:
            # Run as subprocess to capture output
            cmd = [sys.executable, str(test_file)]
            process = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            result["output"] = process.stdout.split('\\n')
            
            if process.returncode == 0:
                print("✅ Script completed successfully")
                result["status"] = "success"
            else:
                print(f"❌ Script failed with return code {process.returncode}")
                result["status"] = "failed"
                result["failures"] = 1
                result["error_details"] = [process.stderr]
        
        except subprocess.TimeoutExpired:
            result["status"] = "error"
            result["errors"] = 1
            result["error_details"] = ["Test timed out after 5 minutes"]
        
        except Exception as e:
            result["status"] = "error"
            result["errors"] = 1
            result["error_details"] = [str(e)]
        
        return result
    
    def run_all_tests(self, pattern: str = None) -> None:
        """Run all discovered tests."""
        print("🧪 AI Backend Document Processing - Test Suite")
        print("="*60)
        print(f"Test directory: {self.test_dir}")
        print(f"Project root: {self.project_root}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        test_files = self.discover_test_files()
        
        if pattern:
            test_files = [f for f in test_files if pattern in f.name]
        
        if not test_files:
            print("No test files found!")
            return
        
        print(f"Found {len(test_files)} test files:")
        for test_file in test_files:
            print(f"  - {test_file.name}")
        print()
        
        # Run each test file
        for test_file in test_files:
            if test_file.name.endswith('.py'):
                # Determine how to run the test
                if any(keyword in test_file.name.lower() for keyword in 
                       ['unit', 'test_', 'docai', 'ocr', 'parsing']):
                    result = self.run_unittest_file(test_file)
                else:
                    result = self.run_script_file(test_file)
                
                # Update overall results
                self.results["test_results"][test_file.name] = result
                self.results["total_tests"] += result.get("tests_run", 0)
                
                if result["status"] == "success":
                    self.results["passed"] += result.get("tests_run", 1)
                elif result["status"] == "failed":
                    self.results["failed"] += result.get("failures", 0)
                    self.results["errors"] += result.get("errors", 0)
                elif result["status"] == "error":
                    self.results["errors"] += 1
                elif result["status"] == "skipped":
                    self.results["skipped"] += result.get("skipped", 1)
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print test execution summary."""
        print("\\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        
        print(f"Total test files: {len(self.results['test_results'])}")
        print(f"Total tests run: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Errors: {self.results['errors']}")
        print(f"Skipped: {self.results['skipped']}")
        
        success_rate = (
            self.results["passed"] / max(self.results["total_tests"], 1) * 100
        )
        print(f"Success rate: {success_rate:.1f}%")
        
        # Print details for failed tests
        if self.results["failed"] > 0 or self.results["errors"] > 0:
            print("\\n" + "-"*60)
            print("FAILED/ERROR DETAILS")
            print("-"*60)
            
            for file_name, result in self.results["test_results"].items():
                if result["status"] in ["failed", "error"]:
                    print(f"\\n❌ {file_name}:")
                    for detail in result.get("error_details", []):
                        print(f"   {detail}")
        
        # Overall status
        print("\\n" + "="*60)
        if self.results["failed"] == 0 and self.results["errors"] == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️ SOME TESTS FAILED - See details above")
        
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Unified test runner for AI Backend tests"
    )
    parser.add_argument(
        "--pattern", "-p",
        help="Run only tests matching this pattern",
        default=None
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available test files without running them"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.list:
        test_files = runner.discover_test_files()
        print("Available test files:")
        for test_file in test_files:
            print(f"  - {test_file.name}")
        return
    
    runner.run_all_tests(pattern=args.pattern)


if __name__ == "__main__":
    main()