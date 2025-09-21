#!/usr/bin/env python3
"""
Setup and Verification Script for Google Vision API

This script performs comprehensive setup and verification of the Google Vision API
environment, including dependencies, credentials, and connectivity testing.

Steps:
1. Environment Validation - Check virtual environment
2. Dependencies Installation - Verify and install required packages
3. Credentials Check - Validate Google Cloud credentials
4. Vision Client Initialization - Test client creation
5. Sanity Test Call - Verify API connectivity
6. Final Report - Summary of all checks

Exit Codes:
- 0: All checks passed successfully
- 1: One or more checks failed
"""

import os
import sys
import subprocess
import logging
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Setup logging with clear formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Required packages for Vision API functionality
REQUIRED_PACKAGES = [
    'google-cloud-vision',
    'google-cloud-storage', 
    'PyMuPDF',
    'pdfplumber',
    'pypdf'
]

# Credentials file path
CREDENTIALS_PATH = Path("data/.cheetah/gcloud/vision-credentials.json")

class VisionSetupVerifier:
    """Handles setup and verification of Google Vision API environment."""
    
    def __init__(self):
        """Initialize the verifier with status tracking."""
        self.status = {
            'environment': False,
            'dependencies': False,
            'credentials': False,
            'vision_client': False,
            'test_call': False
        }
        self.errors = []
        self.project_root = Path(__file__).parent.parent
    
    def log_step(self, step_name: str, message: str, success: bool = True):
        """Log a step with clear success/failure indicator."""
        indicator = "✅" if success else "❌"
        logger.info(f"{indicator} {step_name}: {message}")
        if not success:
            self.errors.append(f"{step_name}: {message}")
    
    def check_virtual_environment(self) -> bool:
        """
        Check if a virtual environment is active.
        
        Returns:
            bool: True if virtual environment is detected or system Python is acceptable
        """
        logger.info("="*60)
        logger.info("STEP 1: Environment Validation")
        logger.info("="*60)
        
        # Check for common virtual environment indicators
        venv_indicators = [
            os.environ.get('VIRTUAL_ENV'),           # Standard venv/virtualenv
            os.environ.get('CONDA_DEFAULT_ENV'),     # Conda environment
            os.environ.get('PIPENV_ACTIVE'),         # Pipenv
            sys.prefix != sys.base_prefix            # Any virtual environment
        ]
        
        venv_active = any(venv_indicators)
        
        if venv_active:
            venv_name = (
                os.environ.get('VIRTUAL_ENV', '').split(os.sep)[-1] or
                os.environ.get('CONDA_DEFAULT_ENV') or
                'detected'
            )
            self.log_step("Environment", f"Virtual environment active: {venv_name}")
            
            # Log Python executable path for verification
            logger.info(f"   Python executable: {sys.executable}")
            self.status['environment'] = True
        else:
            # Check if system Python has write permissions (can install packages)
            try:
                import tempfile
                import site
                # Check if we can write to site-packages (indicates good system Python setup)
                site_packages = site.getsitepackages()[0] if site.getsitepackages() else None
                can_install = site_packages and os.access(site_packages, os.W_OK)
                
                if can_install:
                    self.log_step("Environment", "Using system Python with package installation capability")
                    logger.info(f"   Python executable: {sys.executable}")
                    logger.info("   Note: Virtual environment recommended for project isolation")
                    self.status['environment'] = True
                else:
                    self.log_step("Environment", "System Python detected - package installation may require admin privileges", False)
                    logger.info("   Recommendation: Use a virtual environment for better package management")
                    self.status['environment'] = False
            except Exception:
                self.log_step("Environment", "No virtual environment detected (using system Python)", False)
                logger.info("   Recommendation: Use a virtual environment for better package management")
                self.status['environment'] = False
        
        return self.status['environment']
    
    def install_dependencies(self) -> bool:
        """
        Verify and install required dependencies.
        
        Returns:
            bool: True if all dependencies are available
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Dependencies Installation")
        logger.info("="*60)
        
        installed_packages = self._get_installed_packages()
        missing_packages = []
        
        # Check each required package
        for package in REQUIRED_PACKAGES:
            if self._is_package_installed(package, installed_packages):
                self.log_step("Package Check", f"{package} - already installed")
            else:
                missing_packages.append(package)
                self.log_step("Package Check", f"{package} - missing", False)
        
        # Install missing packages
        if missing_packages:
            logger.info(f"\nInstalling {len(missing_packages)} missing packages...")
            success = self._install_packages(missing_packages)
            
            if success:
                self.log_step("Installation", f"Successfully installed: {', '.join(missing_packages)}")
                # Verify installation
                verification_failed = []
                installed_packages = self._get_installed_packages()  # Refresh package list
                
                for package in missing_packages:
                    if not self._is_package_installed(package, installed_packages):
                        verification_failed.append(package)
                
                if verification_failed:
                    self.log_step("Verification", f"Failed to verify: {', '.join(verification_failed)}", False)
                    self.status['dependencies'] = False
                    return False
            else:
                self.log_step("Installation", "Failed to install missing packages", False)
                self.status['dependencies'] = False
                return False
        
        self.log_step("Dependencies", "All required packages available")
        self.status['dependencies'] = True
        return True
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """Get list of installed packages."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                check=True
            )
            packages = json.loads(result.stdout)
            return {pkg['name'].lower().replace('-', '_'): pkg['version'] for pkg in packages}
        except Exception:
            # Fallback method
            return {}
    
    def _is_package_installed(self, package_name: str, installed_packages: Dict[str, str]) -> bool:
        """Check if a package is installed."""
        # Normalize package name for comparison
        normalized_name = package_name.lower().replace('-', '_')
        
        # Check direct match
        if normalized_name in installed_packages:
            return True
        
        # Check alternative naming patterns
        alternatives = [
            package_name.lower().replace('_', '-'),
            package_name.lower().replace('-', '_')
        ]
        
        for alt in alternatives:
            if alt in installed_packages:
                return True
        
        # Try import test as final check
        try:
            if package_name == 'google-cloud-vision':
                import google.cloud.vision
            elif package_name == 'google-cloud-storage':
                import google.cloud.storage
            elif package_name == 'PyMuPDF':
                import fitz
            elif package_name == 'pdfplumber':
                import pdfplumber
            elif package_name == 'pypdf':
                import pypdf
            return True
        except ImportError:
            return False
    
    def _install_packages(self, packages: List[str]) -> bool:
        """Install packages using pip."""
        try:
            cmd = [sys.executable, '-m', 'pip', 'install'] + packages
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("Installation output:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    logger.info(f"   {line}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Installation failed: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during installation: {e}")
            return False
    
    def check_credentials(self) -> bool:
        """
        Check Google Cloud credentials configuration.
        
        Returns:
            bool: True if credentials are properly configured
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Credentials Check")
        logger.info("="*60)
        
        # Resolve credentials path relative to project root
        credentials_full_path = self.project_root / CREDENTIALS_PATH
        
        # Check if credentials file exists
        if not credentials_full_path.exists():
            self.log_step("Credentials File", f"File not found: {credentials_full_path}", False)
            logger.info(f"   Expected location: {credentials_full_path.absolute()}")
            logger.info("   Please ensure the Google Cloud service account key is placed at this location")
            self.status['credentials'] = False
            return False
        
        self.log_step("Credentials File", f"Found at {credentials_full_path}")
        
        # Validate file format
        try:
            with open(credentials_full_path, 'r', encoding='utf-8') as f:
                cred_data = json.load(f)
            
            # Check for required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in cred_data]
            
            if missing_fields:
                self.log_step("Credentials Format", f"Missing required fields: {missing_fields}", False)
                self.status['credentials'] = False
                return False
            
            self.log_step("Credentials Format", "Valid service account key format")
            
        except json.JSONDecodeError:
            self.log_step("Credentials Format", "Invalid JSON format", False)
            self.status['credentials'] = False
            return False
        except Exception as e:
            self.log_step("Credentials Format", f"Error reading file: {e}", False)
            self.status['credentials'] = False
            return False
        
        # Check environment variable
        env_credentials = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        expected_path = str(credentials_full_path.absolute())
        
        if env_credentials:
            if os.path.abspath(env_credentials) == expected_path:
                self.log_step("Environment Variable", f"GOOGLE_APPLICATION_CREDENTIALS correctly set")
            else:
                self.log_step("Environment Variable", 
                            f"GOOGLE_APPLICATION_CREDENTIALS points to different file: {env_credentials}", False)
                logger.info(f"   Expected: {expected_path}")
                logger.info("   Updating environment variable for this session...")
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expected_path
                self.log_step("Environment Variable", "Updated for current session")
        else:
            logger.info("   GOOGLE_APPLICATION_CREDENTIALS not set, setting for this session...")
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = expected_path
            self.log_step("Environment Variable", "Set for current session")
        
        self.status['credentials'] = True
        return True
    
    def initialize_vision_client(self) -> bool:
        """
        Test Google Vision client initialization.
        
        Returns:
            bool: True if client initializes successfully
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 4: Vision Client Initialization")
        logger.info("="*60)
        
        try:
            from google.cloud import vision
            
            # Try to create the client
            client = vision.ImageAnnotatorClient()
            self.log_step("Vision Client", "Successfully initialized")
            
            # Store client for next test
            self._vision_client = client
            self.status['vision_client'] = True
            return True
            
        except ImportError as e:
            self.log_step("Vision Client", f"Import error: {e}", False)
            self.status['vision_client'] = False
            return False
        except Exception as e:
            self.log_step("Vision Client", f"Initialization failed: {e}", False)
            self.status['vision_client'] = False
            return False
    
    def test_vision_api_call(self) -> bool:
        """
        Perform a minimal Vision API test call.
        
        Returns:
            bool: True if API call succeeds
        """
        logger.info("\n" + "="*60)
        logger.info("STEP 5: Sanity Test Call")
        logger.info("="*60)
        
        if not hasattr(self, '_vision_client'):
            self.log_step("Test Call", "Vision client not available", False)
            self.status['test_call'] = False
            return False
        
        try:
            # Perform minimal API call with empty request
            # This tests authentication and basic connectivity
            response = self._vision_client.batch_annotate_images(requests=[])
            
            self.log_step("Test Call", "Successfully connected to Vision API")
            logger.info(f"   Response type: {type(response).__name__}")
            
            self.status['test_call'] = True
            return True
            
        except Exception as e:
            self.log_step("Test Call", f"API call failed: {e}", False)
            
            # Provide specific guidance for common errors
            error_str = str(e).lower()
            if 'authentication' in error_str or 'credential' in error_str:
                logger.info("   → Check that your service account key has Vision API permissions")
                logger.info("   → Verify that the Vision API is enabled in your Google Cloud project")
            elif 'quota' in error_str or 'billing' in error_str:
                logger.info("   → Check that billing is enabled for your Google Cloud project")
                logger.info("   → Verify that you haven't exceeded API quotas")
            elif 'network' in error_str or 'connection' in error_str:
                logger.info("   → Check your internet connection")
                logger.info("   → Verify that firewall settings allow Google Cloud API access")
            
            self.status['test_call'] = False
            return False
    
    def print_final_report(self) -> bool:
        """
        Print final status report.
        
        Returns:
            bool: True if all checks passed
        """
        logger.info("\n" + "="*60)
        logger.info("FINAL REPORT")
        logger.info("="*60)
        
        all_passed = True
        
        # Print status for each component
        for component, status in self.status.items():
            indicator = "✅" if status else "❌"
            component_name = component.replace('_', ' ').title()
            logger.info(f"{indicator} {component_name}: {'OK' if status else 'FAILED'}")
            
            if not status:
                all_passed = False
        
        logger.info("="*60)
        
        if all_passed:
            logger.info("🎉 ALL CHECKS PASSED! Google Vision API is ready to use.")
            logger.info("\nYou can now:")
            logger.info("   • Run OCR processing scripts")
            logger.info("   • Use the document processing pipeline")
            logger.info("   • Process PDFs with Vision API")
        else:
            logger.error("❌ SETUP INCOMPLETE! Please address the failed checks above.")
            logger.info("\nFailed components:")
            for error in self.errors:
                logger.info(f"   • {error}")
        
        return all_passed
    
    def run_all_checks(self) -> bool:
        """
        Run all verification steps in sequence.
        
        Returns:
            bool: True if all checks pass
        """
        logger.info("🔧 Google Vision API Setup and Verification")
        logger.info(f"Project root: {self.project_root.absolute()}")
        logger.info(f"Python executable: {sys.executable}")
        
        # Run all checks in order
        checks = [
            self.check_virtual_environment,
            self.install_dependencies,
            self.check_credentials,
            self.initialize_vision_client,
            self.test_vision_api_call
        ]
        
        for check in checks:
            try:
                success = check()
                if not success:
                    logger.warning(f"Check failed: {check.__name__}")
                    # Continue with remaining checks for complete diagnosis
            except Exception as e:
                logger.error(f"Unexpected error in {check.__name__}: {e}")
                return False
        
        # Print final report
        return self.print_final_report()


def main() -> int:
    """
    Main entry point for the setup verification script.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        verifier = VisionSetupVerifier()
        success = verifier.run_all_checks()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Setup verification interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error during setup verification: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)