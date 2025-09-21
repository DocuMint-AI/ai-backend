#!/usr/bin/env python3
"""
PyMuPDF Verification Script

This script verifies that PyMuPDF (fitz) is properly installed and functional,
including DLL loading, basic functionality, and PDF processing capabilities.

Exit Codes:
- 0: PyMuPDF is working correctly
- 1: PyMuPDF import or functionality failed
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PyMuPDFVerifier:
    """Handles verification of PyMuPDF installation and functionality."""
    
    def __init__(self):
        """Initialize verifier."""
        self.errors = []
    
    def log_step(self, step_name: str, message: str, success: bool = True):
        """Log a step with clear success/failure indicator."""
        indicator = "✅" if success else "❌"
        logger.info(f"{indicator} {step_name}: {message}")
        if not success:
            self.errors.append(f"{step_name}: {message}")
    
    def test_fitz_import(self) -> bool:
        """Test basic fitz import functionality."""
        logger.info("="*60)
        logger.info("STEP 1: PyMuPDF Import Test")
        logger.info("="*60)
        
        try:
            import fitz
            self.log_step("Import", "Successfully imported fitz module")
            
            # Test version information
            version = fitz.VersionBind
            self.log_step("Version", f"PyMuPDF version: {version}")
            
            # Test basic functionality
            doc_count = fitz.fitz_library_version()
            self.log_step("Library", f"Library version: {doc_count}")
            
            # Store fitz module for later use
            self.fitz = fitz
            return True
            
        except ImportError as e:
            self.log_step("Import", f"Failed to import fitz: {e}", False)
            logger.info("   → Ensure PyMuPDF is installed: pip install PyMuPDF")
            return False
        except Exception as e:
            self.log_step("Import", f"Unexpected error: {e}", False)
            return False
    
    def test_pdf_creation(self) -> bool:
        """Test PDF creation capabilities."""
        logger.info("\n" + "="*60)
        logger.info("STEP 2: PDF Creation Test")
        logger.info("="*60)
        
        if not hasattr(self, 'fitz'):
            self.log_step("PDF Creation", "Fitz not available - skipping test", False)
            return False
        
        try:
            # Create a simple PDF document
            doc = self.fitz.open()  # Create empty PDF
            page = doc.new_page()   # Add a page
            
            # Insert some text
            text_rect = self.fitz.Rect(50, 50, 200, 100)
            page.insert_text(text_rect.tl, "PyMuPDF Test Document", fontsize=12)
            
            self.log_step("PDF Creation", "Successfully created test PDF document")
            
            # Test page count
            page_count = len(doc)
            self.log_step("Page Count", f"Document has {page_count} page(s)")
            
            # Clean up
            doc.close()
            return True
            
        except Exception as e:
            self.log_step("PDF Creation", f"Failed to create PDF: {e}", False)
            return False
    
    def test_pdf_processing(self) -> bool:
        """Test PDF processing with a real file if available."""
        logger.info("\n" + "="*60)
        logger.info("STEP 3: PDF Processing Test")
        logger.info("="*60)
        
        if not hasattr(self, 'fitz'):
            self.log_step("PDF Processing", "Fitz not available - skipping test", False)
            return False
        
        # Look for test PDFs
        test_pdf_paths = [
            Path("data/test-files/MCRC_46229_2018_FinalOrder_02-Jan-2019.pdf"),
            Path("data/test-files"),  # Check if directory exists
        ]
        
        test_pdf = None
        for path in test_pdf_paths:
            if path.exists():
                if path.is_file():
                    test_pdf = path
                    break
                elif path.is_dir():
                    # Find first PDF in directory
                    pdf_files = list(path.glob("*.pdf"))
                    if pdf_files:
                        test_pdf = pdf_files[0]
                        break
        
        if not test_pdf:
            self.log_step("PDF Processing", "No test PDF found - creating temporary test", True)
            return self._test_with_temp_pdf()
        
        try:
            # Open real PDF file
            doc = self.fitz.open(str(test_pdf))
            
            self.log_step("PDF Opening", f"Successfully opened: {test_pdf.name}")
            
            # Test basic operations
            page_count = len(doc)
            self.log_step("Page Count", f"PDF has {page_count} pages")
            
            if page_count > 0:
                # Test page access
                page = doc[0]
                self.log_step("Page Access", "Successfully accessed first page")
                
                # Test text extraction
                text = page.get_text()
                text_length = len(text.strip())
                self.log_step("Text Extraction", f"Extracted {text_length} characters")
                
                # Test image conversion (key functionality)
                try:
                    pix = page.get_pixmap(matrix=self.fitz.Matrix(2.0, 2.0))  # 2x scale
                    img_width = pix.width
                    img_height = pix.height
                    self.log_step("Image Conversion", f"Converted to image: {img_width}x{img_height}")
                    pix = None  # Clean up
                except Exception as e:
                    self.log_step("Image Conversion", f"Failed: {e}", False)
                    return False
            
            # Clean up
            doc.close()
            return True
            
        except Exception as e:
            self.log_step("PDF Processing", f"Failed to process PDF: {e}", False)
            return False
    
    def _test_with_temp_pdf(self) -> bool:
        """Test with a temporary PDF document."""
        try:
            # Create temporary PDF
            doc = self.fitz.open()
            page = doc.new_page(width=595, height=842)  # A4 size
            
            # Add content
            page.insert_text((50, 50), "Temporary Test Document", fontsize=14)
            page.insert_text((50, 80), "This is a test for PyMuPDF functionality.", fontsize=10)
            
            # Test image conversion
            pix = page.get_pixmap()
            img_width = pix.width
            img_height = pix.height
            
            self.log_step("Temp PDF Test", f"Created and converted temp PDF: {img_width}x{img_height}")
            
            # Clean up
            pix = None
            doc.close()
            return True
            
        except Exception as e:
            self.log_step("Temp PDF Test", f"Failed: {e}", False)
            return False
    
    def test_fallback_libraries(self) -> bool:
        """Test that fallback PDF libraries are available."""
        logger.info("\n" + "="*60)
        logger.info("STEP 4: Fallback Libraries Test")
        logger.info("="*60)
        
        fallback_libraries = [
            ("pdfplumber", "pdfplumber"),
            ("PyPDF2", "PyPDF2"),
            ("pypdf", "pypdf")
        ]
        
        all_available = True
        
        for lib_name, import_name in fallback_libraries:
            try:
                __import__(import_name)
                self.log_step("Fallback Library", f"{lib_name} is available")
            except ImportError:
                self.log_step("Fallback Library", f"{lib_name} is NOT available", False)
                all_available = False
        
        return all_available
    
    def print_final_report(self) -> bool:
        """Print final verification report."""
        logger.info("\n" + "="*60)
        logger.info("FINAL VERIFICATION REPORT")
        logger.info("="*60)
        
        if not self.errors:
            logger.info("🎉 ALL TESTS PASSED! PyMuPDF is ready for use.")
            logger.info("\nPyMuPDF capabilities confirmed:")
            logger.info("   • Module import successful")
            logger.info("   • PDF creation functional")
            logger.info("   • PDF processing operational")
            logger.info("   • Image conversion working")
            logger.info("   • Fallback libraries available")
            logger.info("\nYou can now use PyMuPDF for PDF-to-image conversion in the pipeline.")
            return True
        else:
            logger.error("❌ VERIFICATION FAILED! Issues found:")
            for error in self.errors:
                logger.info(f"   • {error}")
            
            logger.info("\nTroubleshooting suggestions:")
            logger.info("   • Reinstall PyMuPDF: pip install --no-cache-dir PyMuPDF")
            logger.info("   • Install Visual C++ Redistributable (2015-2022)")
            logger.info("   • Check Python version compatibility (3.8-3.11 recommended)")
            logger.info("   • Try alternative: pip install --force-reinstall PyMuPDF")
            
            return False
    
    def run_all_tests(self) -> bool:
        """Run all verification tests."""
        logger.info("🔧 PyMuPDF Verification Started")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        
        tests = [
            self.test_fitz_import,
            self.test_pdf_creation,
            self.test_pdf_processing,
            self.test_fallback_libraries
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                results.append(False)
        
        return self.print_final_report()


def main() -> int:
    """Main entry point for PyMuPDF verification."""
    try:
        verifier = PyMuPDFVerifier()
        success = verifier.run_all_tests()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Verification interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error during verification: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)