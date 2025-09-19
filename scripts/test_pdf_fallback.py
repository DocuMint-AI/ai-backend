#!/usr/bin/env python3
"""
Test script for PDF fallback system validation.

This script tests the enhanced util_services.py with fallback PDF processing
to ensure the pipeline continues working even when PyMuPDF fails.
"""

import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.util_services import PDFToImageConverter
from services.exceptions import PDFProcessingError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_converter_initialization():
    """Test PDF converter initialization with fallback system."""
    logger.info("=== TESTING PDF CONVERTER INITIALIZATION ===")
    
    try:
        converter = PDFToImageConverter(data_root="./data/test_fallback", image_format="PNG", dpi=150)
        logger.info(f"✅ PDF converter initialized successfully using {converter.library_name}")
        logger.info(f"   Library: {converter.pdf_library}")
        logger.info(f"   Data root: {converter.data_root}")
        logger.info(f"   Image format: {converter.image_format}")
        logger.info(f"   DPI: {converter.dpi}")
        return converter
    except Exception as e:
        logger.error(f"❌ Failed to initialize PDF converter: {e}")
        return None

def test_pdf_processing(converter, test_pdf_path):
    """Test PDF processing with the fallback system."""
    logger.info("=== TESTING PDF PROCESSING ===")
    
    if not converter:
        logger.error("❌ No converter available for testing")
        return None
    
    test_pdf = Path(test_pdf_path)
    if not test_pdf.exists():
        logger.warning(f"⚠️  Test PDF not found: {test_pdf}")
        logger.info("Creating a minimal test scenario...")
        return None
    
    try:
        logger.info(f"Processing PDF: {test_pdf.name}")
        uid, output_paths, metadata = converter.convert_pdf_to_images(str(test_pdf))
        
        logger.info(f"✅ PDF processing successful!")
        logger.info(f"   UID: {uid}")
        logger.info(f"   Output paths: {len(output_paths)} files")
        logger.info(f"   Total pages: {metadata['processing_info']['total_pages']}")
        logger.info(f"   Processed pages: {metadata['processing_info']['processed_pages']}")
        logger.info(f"   Processing method: {metadata['processing_info']['processing_method']}")
        logger.info(f"   Library used: {metadata['processing_info']['pdf_library']}")
        logger.info(f"   Has images: {metadata['status']['has_images']}")
        logger.info(f"   Has text: {metadata['status']['has_text']}")
        logger.info(f"   Fallback mode: {metadata['status']['fallback_mode']}")
        
        return uid, output_paths, metadata
        
    except Exception as e:
        logger.error(f"❌ PDF processing failed: {e}")
        return None

def test_library_detection():
    """Test which PDF libraries are available."""
    logger.info("=== TESTING LIBRARY DETECTION ===")
    
    libraries = {
        'PyMuPDF (fitz)': None,
        'pdfplumber': None,
        'PyPDF2': None,
        'pypdf': None
    }
    
    # Test PyMuPDF
    try:
        import fitz
        # Test actual functionality
        test_doc = fitz.open()
        test_doc.close()
        libraries['PyMuPDF (fitz)'] = f"✅ Available (v{getattr(fitz, '__version__', 'unknown')})"
    except Exception as e:
        libraries['PyMuPDF (fitz)'] = f"❌ Failed: {e}"
    
    # Test pdfplumber
    try:
        import pdfplumber
        libraries['pdfplumber'] = f"✅ Available (v{getattr(pdfplumber, '__version__', 'unknown')})"
    except ImportError:
        libraries['pdfplumber'] = "❌ Not installed"
    except Exception as e:
        libraries['pdfplumber'] = f"❌ Failed: {e}"
    
    # Test PyPDF2
    try:
        import PyPDF2
        libraries['PyPDF2'] = f"✅ Available (v{getattr(PyPDF2, '__version__', 'unknown')})"
    except ImportError:
        libraries['PyPDF2'] = "❌ Not installed"
    except Exception as e:
        libraries['PyPDF2'] = f"❌ Failed: {e}"
    
    # Test pypdf
    try:
        import pypdf
        libraries['pypdf'] = f"✅ Available (v{getattr(pypdf, '__version__', 'unknown')})"
    except ImportError:
        libraries['pypdf'] = "❌ Not installed"
    except Exception as e:
        libraries['pypdf'] = f"❌ Failed: {e}"
    
    for lib, status in libraries.items():
        logger.info(f"   {lib}: {status}")
    
    return libraries

def create_test_summary(converter, libraries, processing_result):
    """Create a comprehensive test summary."""
    logger.info("=== TEST SUMMARY ===")
    
    # Overall status
    if converter and processing_result:
        overall_status = "✅ PASS - Fallback system working"
    elif converter:
        overall_status = "⚠️  PARTIAL - Converter works but no test PDF"
    else:
        overall_status = "❌ FAIL - No PDF library available"
    
    logger.info(f"Overall Status: {overall_status}")
    
    # Library availability
    available_libs = [lib for lib, status in libraries.items() if status.startswith("✅")]
    logger.info(f"Available libraries: {len(available_libs)} / {len(libraries)}")
    
    # Active library
    if converter:
        logger.info(f"Active library: {converter.library_name}")
    else:
        logger.info("Active library: None")
    
    # Processing capability
    if processing_result:
        _, _, metadata = processing_result
        if metadata['status']['has_images']:
            processing_capability = "Full (images + text)"
        else:
            processing_capability = "Limited (text only)"
    else:
        processing_capability = "Unknown"
    
    logger.info(f"Processing capability: {processing_capability}")
    
    # Recommendations
    logger.info("=== RECOMMENDATIONS ===")
    if not converter:
        logger.info("❌ Install at least one PDF library:")
        logger.info("   Recommended: uv pip install PyMuPDF pdfplumber PyPDF2 pypdf")
    elif converter.library_name != "PyMuPDF":
        logger.info("⚠️  Using fallback library - consider fixing PyMuPDF:")
        logger.info("   1. Try reinstalling: uv pip uninstall PyMuPDF && uv pip install PyMuPDF")
        logger.info("   2. Check Windows Visual C++ redistributables")
        logger.info("   3. Current fallback working - pipeline functional")
    else:
        logger.info("✅ Optimal setup - PyMuPDF working correctly")
    
    return overall_status

def main():
    """Main test function."""
    logger.info("Starting PDF fallback system validation...")
    
    # Test 1: Library detection
    libraries = test_library_detection()
    
    # Test 2: Converter initialization
    converter = test_pdf_converter_initialization()
    
    # Test 3: PDF processing (if test file available)
    test_pdf_paths = [
        "./data/test-files/testing-ocr-pdf-1.pdf",
        "./data/testing-ocr-pdf-1-1e08491e-28e026de/testing-ocr-pdf-1.pdf",
        "./data/uploads/testing-ocr-pdf-1.pdf"
    ]
    
    processing_result = None
    for test_path in test_pdf_paths:
        if Path(test_path).exists():
            processing_result = test_pdf_processing(converter, test_path)
            break
    
    if not processing_result and converter:
        logger.info("No test PDF found, testing converter capabilities only")
    
    # Test 4: Create summary
    overall_status = create_test_summary(converter, libraries, processing_result)
    
    # Exit code
    if overall_status.startswith("✅"):
        exit_code = 0
    elif overall_status.startswith("⚠️"):
        exit_code = 1
    else:
        exit_code = 2
    
    logger.info(f"Test completed with exit code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)