#!/usr/bin/env python3
"""
Environment Setup and Validation Script

This script sets up and validates the complete environment for the AI backend
document processing pipeline, including .env variables, credentials, and services.

Steps:
1. Load and validate .env configuration
2. Set environment variables for the session
3. Validate Google Cloud credentials
4. Test DocAI connectivity
5. Verify PDF processing capabilities
6. Test complete pipeline readiness

Exit Codes:
- 0: Environment is ready for pipeline operation
- 1: Environment setup failed
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentSetup:
    """Handles complete environment setup and validation."""
    
    def __init__(self):
        """Initialize environment setup."""
        self.errors = []
        self.env_vars = {}
        self.project_root = Path(__file__).parent.parent
    
    def log_step(self, step_name: str, message: str, success: bool = True):
        """Log a step with clear success/failure indicator."""
        indicator = "✅" if success else "❌"
        logger.info(f"{indicator} {step_name}: {message}")
        if not success:
            self.errors.append(f"{step_name}: {message}")
    
    def load_env_file(self) -> bool:
        """Load and validate .env file configuration."""
        logger.info("="*60)
        logger.info("STEP 1: Environment File Loading")
        logger.info("="*60)
        
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            self.log_step("Env File", f"File not found: {env_file}", False)
            return False
        
        try:
            # Load .env file manually (compatible approach)
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self.env_vars[key] = value
                        os.environ[key] = value
            
            self.log_step("Env File", f"Loaded {len(self.env_vars)} environment variables")
            
            # Log key variables (without sensitive data)
            key_vars = [
                "GOOGLE_CLOUD_PROJECT_ID",
                "DOCAI_LOCATION", 
                "DOCAI_PROCESSOR_ID",
                "LANGUAGE_HINTS",
                "DATA_ROOT"
            ]
            
            for var in key_vars:
                if var in self.env_vars:
                    value = self.env_vars[var]
                    # Mask sensitive data
                    if "ID" in var and len(value) > 8:
                        masked_value = value[:4] + "..." + value[-4:]
                    else:
                        masked_value = value
                    logger.info(f"   {var}: {masked_value}")
            
            return True
            
        except Exception as e:
            self.log_step("Env File", f"Failed to load: {e}", False)
            return False
    
    def validate_credentials(self) -> bool:
        """Validate Google Cloud credentials."""
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Google Cloud Credentials")
        logger.info("="*60)
        
        credentials_path = self.env_vars.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            self.log_step("Credentials Path", "GOOGLE_APPLICATION_CREDENTIALS not set", False)
            return False
        
        # Resolve relative path
        if not os.path.isabs(credentials_path):
            credentials_path = str(self.project_root / credentials_path)
        
        credentials_file = Path(credentials_path)
        if not credentials_file.exists():
            self.log_step("Credentials File", f"File not found: {credentials_file}", False)
            return False
        
        try:
            with open(credentials_file, 'r') as f:
                cred_data = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'client_email']
            missing_fields = [field for field in required_fields if field not in cred_data]
            
            if missing_fields:
                self.log_step("Credentials Format", f"Missing fields: {missing_fields}", False)
                return False
            
            self.log_step("Credentials File", f"Valid service account: {cred_data['client_email']}")
            
            # Update environment variable with absolute path
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_file)
            
            return True
            
        except Exception as e:
            self.log_step("Credentials Format", f"Invalid JSON: {e}", False)
            return False
    
    def test_google_services(self) -> bool:
        """Test Google Cloud services connectivity."""
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Google Cloud Services")
        logger.info("="*60)
        
        # Test Vision API
        try:
            from google.cloud import vision
            vision_client = vision.ImageAnnotatorClient()
            
            # Test API call
            response = vision_client.batch_annotate_images(requests=[])
            self.log_step("Vision API", "Successfully connected")
            
        except Exception as e:
            self.log_step("Vision API", f"Connection failed: {e}", False)
            return False
        
        # Test Document AI
        try:
            from google.cloud import documentai
            
            processor_id = self.env_vars.get("DOCAI_PROCESSOR_ID")
            location = self.env_vars.get("DOCAI_LOCATION", "us")
            project_id = self.env_vars.get("GOOGLE_CLOUD_PROJECT_ID")
            
            if not all([processor_id, project_id]):
                self.log_step("DocAI Config", "Missing processor ID or project ID", False)
                return False
            
            client = documentai.DocumentProcessorServiceClient()
            processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
            
            self.log_step("DocAI", f"Client initialized for processor: {processor_id}")
            
        except Exception as e:
            self.log_step("DocAI", f"Initialization failed: {e}", False)
            return False
        
        return True
    
    def test_pdf_processing(self) -> bool:
        """Test PDF processing capabilities."""
        logger.info("\n" + "="*60)
        logger.info("STEP 4: PDF Processing Libraries")
        logger.info("="*60)
        
        # Test PyMuPDF
        try:
            import fitz
            self.log_step("PyMuPDF", f"Available - Version: {fitz.VersionBind}")
            self.pymupdf_available = True
        except Exception as e:
            self.log_step("PyMuPDF", f"Not available: {e}", False)
            self.pymupdf_available = False
        
        # Test fallback libraries
        fallbacks_available = 0
        fallback_libs = [
            ("pdfplumber", "pdfplumber"),
            ("PyPDF2", "PyPDF2"), 
            ("pypdf", "pypdf")
        ]
        
        for lib_name, import_name in fallback_libs:
            try:
                __import__(import_name)
                self.log_step("Fallback", f"{lib_name} available")
                fallbacks_available += 1
            except ImportError:
                self.log_step("Fallback", f"{lib_name} not available", False)
        
        if not self.pymupdf_available and fallbacks_available == 0:
            self.log_step("PDF Processing", "No PDF libraries available", False)
            return False
        elif not self.pymupdf_available:
            self.log_step("PDF Processing", f"Will use fallback libraries ({fallbacks_available} available)")
        
        return True
    
    def test_pipeline_structure(self) -> bool:
        """Test pipeline directory structure and components."""
        logger.info("\n" + "="*60)
        logger.info("STEP 5: Pipeline Structure")
        logger.info("="*60)
        
        # Check key directories
        key_dirs = [
            "data/uploads",
            "data/processed", 
            "data/test-files",
            "artifacts",
            "routers",
            "services"
        ]
        
        for dir_path in key_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                self.log_step("Directory", f"{dir_path} exists")
            else:
                # Create if it's a data directory
                if dir_path.startswith("data/") or dir_path == "artifacts":
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.log_step("Directory", f"Created {dir_path}")
                else:
                    self.log_step("Directory", f"{dir_path} missing", False)
                    return False
        
        # Check for test files
        test_files_dir = self.project_root / "data/test-files"
        pdf_files = list(test_files_dir.glob("*.pdf")) if test_files_dir.exists() else []
        
        if pdf_files:
            self.log_step("Test Files", f"Found {len(pdf_files)} PDF test files")
        else:
            self.log_step("Test Files", "No PDF test files found", False)
        
        return True
    
    def create_batch_test_script(self) -> bool:
        """Create a batch test script for processing all PDFs."""
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Batch Test Script Creation")
        logger.info("="*60)
        
        batch_script_content = '''#!/usr/bin/env python3
"""
Batch Document Processing Test

This script processes all PDFs in data/test-files through the complete
orchestration pipeline and outputs results to artifacts/batch_test/.
"""

import sys
import os
import json
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from main import app

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

client = TestClient(app)

def process_all_pdfs():
    """Process all PDFs in test-files directory."""
    test_files_dir = Path("data/test-files")
    output_dir = Path("artifacts/batch_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not test_files_dir.exists():
        logger.error(f"Test files directory not found: {test_files_dir}")
        return False
    
    pdf_files = list(test_files_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found in test-files directory")
        return False
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    results = []
    successful = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\\n{'='*60}")
        logger.info(f"PROCESSING FILE {i}/{len(pdf_files)}: {pdf_path.name}")
        logger.info(f"{'='*60}")
        
        try:
            # Process through API
            with open(pdf_path, "rb") as f:
                files = {"file": (pdf_path.name, f, "application/pdf")}
                response = client.post("/api/v1/process-document", files=files)
            
            if response.status_code == 200:
                result = response.json()
                pipeline_id = result.get("pipeline_id", "unknown")
                
                # Save result
                result_file = output_dir / f"{pdf_path.stem}_result.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                
                # Check for kag_input.json
                processed_dir = Path("data/processed") / pipeline_id
                kag_file = processed_dir / "kag_input.json"
                
                if kag_file.exists():
                    logger.info(f"✅ SUCCESS: {pdf_path.name} → kag_input.json generated")
                    successful += 1
                else:
                    logger.warning(f"⚠️ PARTIAL: {pdf_path.name} → processed but no kag_input.json")
                
                results.append({
                    "file": pdf_path.name,
                    "status": "success",
                    "pipeline_id": pipeline_id,
                    "kag_generated": kag_file.exists()
                })
                
            else:
                logger.error(f"❌ FAILED: {pdf_path.name} → HTTP {response.status_code}")
                results.append({
                    "file": pdf_path.name,
                    "status": "failed",
                    "error": response.text
                })
                
        except Exception as e:
            logger.error(f"❌ ERROR: {pdf_path.name} → {e}")
            results.append({
                "file": pdf_path.name,
                "status": "error",
                "error": str(e)
            })
    
    # Save batch summary
    summary = {
        "total_files": len(pdf_files),
        "successful": successful,
        "success_rate": f"{successful/len(pdf_files)*100:.1f}%",
        "timestamp": "{{ timestamp }}",
        "results": results
    }
    
    summary_file = output_dir / "batch_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\\n{'='*60}")
    logger.info(f"BATCH PROCESSING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total files: {len(pdf_files)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Success rate: {successful/len(pdf_files)*100:.1f}%")
    logger.info(f"Results saved to: {output_dir}")
    
    return successful == len(pdf_files)

if __name__ == "__main__":
    import datetime
    # Replace timestamp placeholder
    script_content = Path(__file__).read_text()
    script_content = script_content.replace("{{ timestamp }}", datetime.datetime.now().isoformat())
    
    success = process_all_pdfs()
    sys.exit(0 if success else 1)
'''
        
        batch_script_path = self.project_root / "scripts" / "batch_test_orchestration.py"
        
        try:
            with open(batch_script_path, 'w', encoding='utf-8') as f:
                f.write(batch_script_content)
            
            self.log_step("Batch Script", f"Created: {batch_script_path}")
            return True
            
        except Exception as e:
            self.log_step("Batch Script", f"Failed to create: {e}", False)
            return False
    
    def print_final_report(self) -> bool:
        """Print final environment setup report."""
        logger.info("\n" + "="*60)
        logger.info("ENVIRONMENT SETUP REPORT")
        logger.info("="*60)
        
        if not self.errors:
            logger.info("🎉 ENVIRONMENT READY! Pipeline can be started.")
            logger.info("\\nConfiguration Summary:")
            logger.info(f"   • Project: {self.env_vars.get('GOOGLE_CLOUD_PROJECT_ID', 'Not set')}")
            logger.info(f"   • DocAI Processor: {self.env_vars.get('DOCAI_PROCESSOR_ID', 'Not set')}")
            logger.info(f"   • PDF Processing: {'PyMuPDF' if getattr(self, 'pymupdf_available', False) else 'Fallback libraries'}")
            logger.info("\\nNext Steps:")
            logger.info("   • Run single test: python scripts/test_single_orchestration.py")
            logger.info("   • Run batch test: python scripts/batch_test_orchestration.py")
            logger.info("   • Check outputs in: artifacts/ and data/processed/")
            
            return True
        else:
            logger.error("❌ ENVIRONMENT SETUP FAILED!")
            logger.info("\\nIssues found:")
            for error in self.errors:
                logger.info(f"   • {error}")
            
            logger.info("\\nRecommended actions:")
            logger.info("   • Verify .env file configuration")
            logger.info("   • Check Google Cloud credentials")
            logger.info("   • Install Visual C++ Redistributable for PyMuPDF")
            logger.info("   • Run: python scripts/setup_and_verify_vision.py")
            
            return False
    
    def run_full_setup(self) -> bool:
        """Run complete environment setup and validation."""
        logger.info("🔧 AI Backend Environment Setup")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Python version: {sys.version.split()[0]}")
        
        setup_steps = [
            self.load_env_file,
            self.validate_credentials,
            self.test_google_services,
            self.test_pdf_processing,
            self.test_pipeline_structure,
            self.create_batch_test_script
        ]
        
        for step in setup_steps:
            try:
                success = step()
                if not success:
                    logger.warning(f"Step failed: {step.__name__}")
            except Exception as e:
                logger.error(f"Step crashed: {step.__name__} - {e}")
                self.errors.append(f"{step.__name__}: Crashed with {e}")
        
        return self.print_final_report()


def main() -> int:
    """Main entry point for environment setup."""
    try:
        setup = EnvironmentSetup()
        success = setup.run_full_setup()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\\n\\n🛑 Environment setup interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error during environment setup: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)