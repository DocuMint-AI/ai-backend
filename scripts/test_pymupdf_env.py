#!/usr/bin/env python3
"""
PyMuPDF Environment Diagnostics and Fallback Implementation.

This script diagnoses PyMuPDF import issues and implements fallback PDF processing
using alternative libraries to ensure the pipeline continues working.
"""

import sys
import subprocess
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log_environment():
    """Log comprehensive environment information."""
    logger.info("=== PYTHON ENVIRONMENT DIAGNOSTIC ===")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python path (first 3): {sys.path[:3]}")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    logger.info(f"In virtual environment: {in_venv}")
    if in_venv:
        logger.info(f"Virtual env prefix: {sys.prefix}")
    
    return in_venv

def check_uv_packages():
    """Check package status via uv."""
    logger.info("=== UV PACKAGE MANAGER CHECK ===")
    
    try:
        # Check PyMuPDF specifically
        result = subprocess.run(['uv', 'pip', 'show', 'PyMuPDF'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("PyMuPDF found via uv pip show")
            logger.info(f"Package info: {result.stdout.strip()}")
            return True
        else:
            logger.warning("PyMuPDF not found via uv pip show")
            logger.warning(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"uv command failed: {e}")
        return False

def test_pymupdf_import():
    """Test PyMuPDF import and get version information."""
    logger.info("=== DIRECT PYMUPDF IMPORT TEST ===")
    
    try:
        import fitz
        version = getattr(fitz, '__version__', 'unknown')
        logger.info(f"SUCCESS: fitz import successful! Version: {version}")
        
        # Test basic functionality
        try:
            # Test creating a document (doesn't require file)
            doc = fitz.open()  # Creates empty document
            doc.close()
            logger.info("SUCCESS: PyMuPDF basic functionality working")
            return True, version
        except Exception as e:
            logger.warning(f"PyMuPDF imported but basic functionality failed: {e}")
            return False, version
            
    except ImportError as e:
        logger.error(f"FAILED: fitz import failed - {e}")
        return False, None
    except Exception as e:
        logger.error(f"FAILED: Unexpected error importing fitz - {e}")
        return False, None

def check_alternative_libraries():
    """Check and test alternative PDF libraries."""
    logger.info("=== ALTERNATIVE PDF LIBRARIES CHECK ===")
    
    alternatives = {}
    
    # Test PyPDF2
    try:
        import PyPDF2
        version = getattr(PyPDF2, '__version__', 'unknown')
        alternatives['PyPDF2'] = {'module': PyPDF2, 'version': version, 'available': True}
        logger.info(f"PyPDF2 available (version: {version})")
    except ImportError:
        alternatives['PyPDF2'] = {'module': None, 'version': None, 'available': False}
        logger.warning("PyPDF2 not available")
    
    # Test pdfplumber
    try:
        import pdfplumber
        version = getattr(pdfplumber, '__version__', 'unknown')
        alternatives['pdfplumber'] = {'module': pdfplumber, 'version': version, 'available': True}
        logger.info(f"pdfplumber available (version: {version})")
    except ImportError:
        alternatives['pdfplumber'] = {'module': None, 'version': None, 'available': False}
        logger.warning("pdfplumber not available")
    
    # Test pypdf
    try:
        import pypdf
        version = getattr(pypdf, '__version__', 'unknown')
        alternatives['pypdf'] = {'module': pypdf, 'version': version, 'available': True}
        logger.info(f"pypdf available (version: {version})")
    except ImportError:
        alternatives['pypdf'] = {'module': None, 'version': None, 'available': False}
        logger.warning("pypdf not available")
    
    return alternatives

def implement_fallback_pdf_converter(alternatives):
    """Implement fallback PDF to image converter using available libraries."""
    logger.info("=== IMPLEMENTING FALLBACK PDF CONVERTER ===")
    
    if alternatives['PyPDF2']['available']:
        return implement_pypdf2_fallback(alternatives['PyPDF2']['module'])
    elif alternatives['pdfplumber']['available']:
        return implement_pdfplumber_fallback(alternatives['pdfplumber']['module'])
    elif alternatives['pypdf']['available']:
        return implement_pypdf_fallback(alternatives['pypdf']['module'])
    else:
        logger.error("No suitable PDF library available for fallback")
        return None

def implement_pypdf2_fallback(PyPDF2):
    """Implement PDF converter using PyPDF2."""
    logger.info("Using PyPDF2 as fallback PDF processor")
    
    class PyPDF2Converter:
        """Fallback PDF converter using PyPDF2."""
        
        def __init__(self, data_root="./data", image_format="PNG", dpi=300):
            self.data_root = Path(data_root)
            self.image_format = image_format
            self.dpi = dpi
            logger.info(f"Initialized PyPDF2 fallback converter: {data_root}, {image_format}, {dpi}DPI")
        
        def generate_uid(self, pdf_path):
            """Generate UID based on file properties."""
            import hashlib
            pdf_path = Path(pdf_path)
            
            hasher = hashlib.sha256()
            hasher.update(pdf_path.name.encode())
            hasher.update(str(pdf_path.stat().st_size).encode())
            hasher.update(str(pdf_path.stat().st_mtime).encode())
            
            full_hash = hasher.hexdigest()
            return f"{full_hash[:8]}-{full_hash[8:16]}"
        
        def convert_pdf_to_images(self, pdf_path, output_folder=None):
            """Convert PDF to images using PyPDF2 (limited functionality)."""
            logger.warning("PyPDF2 fallback: Limited PDF to image conversion")
            logger.warning("PyPDF2 cannot directly convert to images - text extraction only")
            
            # Extract text instead of images
            pdf_path = Path(pdf_path)
            
            if not output_folder:
                uid = self.generate_uid(pdf_path)
                output_folder = self.data_root / f"{pdf_path.stem}-{uid}"
            
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    
                    # Extract text from each page
                    extracted_data = {
                        'pages': [],
                        'total_pages': len(reader.pages),
                        'text_extracted': True,
                        'images_extracted': False,
                        'method': 'PyPDF2_fallback'
                    }
                    
                    for i, page in enumerate(reader.pages):
                        try:
                            text = page.extract_text()
                            page_data = {
                                'page_number': i + 1,
                                'text': text,
                                'image_path': None  # No image conversion capability
                            }
                            extracted_data['pages'].append(page_data)
                            
                            # Save individual page text
                            text_file = output_folder / f"page_{i+1:03d}.txt"
                            with open(text_file, 'w', encoding='utf-8') as f:
                                f.write(text)
                                
                        except Exception as e:
                            logger.error(f"Failed to extract text from page {i+1}: {e}")
                    
                    # Save metadata
                    metadata_file = output_folder / "metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(extracted_data, f, indent=2)
                    
                    logger.info(f"PyPDF2 fallback: Extracted text from {len(extracted_data['pages'])} pages")
                    return output_folder, extracted_data
                    
            except Exception as e:
                logger.error(f"PyPDF2 fallback failed: {e}")
                raise
    
    return PyPDF2Converter

def implement_pdfplumber_fallback(pdfplumber):
    """Implement PDF converter using pdfplumber."""
    logger.info("Using pdfplumber as fallback PDF processor")
    
    class PDFPlumberConverter:
        """Fallback PDF converter using pdfplumber."""
        
        def __init__(self, data_root="./data", image_format="PNG", dpi=300):
            self.data_root = Path(data_root)
            self.image_format = image_format
            self.dpi = dpi
            logger.info(f"Initialized pdfplumber fallback converter: {data_root}, {image_format}, {dpi}DPI")
        
        def generate_uid(self, pdf_path):
            """Generate UID based on file properties."""
            import hashlib
            pdf_path = Path(pdf_path)
            
            hasher = hashlib.sha256()
            hasher.update(pdf_path.name.encode())
            hasher.update(str(pdf_path.stat().st_size).encode())
            hasher.update(str(pdf_path.stat().st_mtime).encode())
            
            full_hash = hasher.hexdigest()
            return f"{full_hash[:8]}-{full_hash[8:16]}"
        
        def convert_pdf_to_images(self, pdf_path, output_folder=None):
            """Convert PDF using pdfplumber (enhanced text extraction)."""
            logger.info("pdfplumber fallback: Enhanced text extraction with layout")
            
            pdf_path = Path(pdf_path)
            
            if not output_folder:
                uid = self.generate_uid(pdf_path)
                output_folder = self.data_root / f"{pdf_path.stem}-{uid}"
            
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    extracted_data = {
                        'pages': [],
                        'total_pages': len(pdf.pages),
                        'text_extracted': True,
                        'images_extracted': False,
                        'method': 'pdfplumber_fallback'
                    }
                    
                    for i, page in enumerate(pdf.pages):
                        try:
                            # Extract text with layout information
                            text = page.extract_text()
                            
                            # Extract tables if any
                            tables = page.extract_tables()
                            
                            page_data = {
                                'page_number': i + 1,
                                'text': text,
                                'tables': tables,
                                'width': page.width,
                                'height': page.height,
                                'image_path': None  # Limited image conversion
                            }
                            extracted_data['pages'].append(page_data)
                            
                            # Save individual page text
                            text_file = output_folder / f"page_{i+1:03d}.txt"
                            with open(text_file, 'w', encoding='utf-8') as f:
                                f.write(text or "")
                                
                            # Save tables if any
                            if tables:
                                import json
                                table_file = output_folder / f"page_{i+1:03d}_tables.json"
                                with open(table_file, 'w') as f:
                                    json.dump(tables, f, indent=2)
                                
                        except Exception as e:
                            logger.error(f"Failed to extract data from page {i+1}: {e}")
                    
                    # Save metadata
                    import json
                    metadata_file = output_folder / "metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(extracted_data, f, indent=2)
                    
                    logger.info(f"pdfplumber fallback: Processed {len(extracted_data['pages'])} pages")
                    return output_folder, extracted_data
                    
            except Exception as e:
                logger.error(f"pdfplumber fallback failed: {e}")
                raise
    
    return PDFPlumberConverter

def implement_pypdf_fallback(pypdf):
    """Implement PDF converter using pypdf."""
    logger.info("Using pypdf as fallback PDF processor")
    
    class PyPDFConverter:
        """Fallback PDF converter using pypdf."""
        
        def __init__(self, data_root="./data", image_format="PNG", dpi=300):
            self.data_root = Path(data_root)
            self.image_format = image_format
            self.dpi = dpi
            logger.info(f"Initialized pypdf fallback converter: {data_root}, {image_format}, {dpi}DPI")
        
        def generate_uid(self, pdf_path):
            """Generate UID based on file properties."""
            import hashlib
            pdf_path = Path(pdf_path)
            
            hasher = hashlib.sha256()
            hasher.update(pdf_path.name.encode())
            hasher.update(str(pdf_path.stat().st_size).encode())
            hasher.update(str(pdf_path.stat().st_mtime).encode())
            
            full_hash = hasher.hexdigest()
            return f"{full_hash[:8]}-{full_hash[8:16]}"
        
        def convert_pdf_to_images(self, pdf_path, output_folder=None):
            """Convert PDF using pypdf (text extraction)."""
            logger.info("pypdf fallback: Text extraction")
            
            pdf_path = Path(pdf_path)
            
            if not output_folder:
                uid = self.generate_uid(pdf_path)
                output_folder = self.data_root / f"{pdf_path.stem}-{uid}"
            
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(pdf_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    
                    extracted_data = {
                        'pages': [],
                        'total_pages': len(reader.pages),
                        'text_extracted': True,
                        'images_extracted': False,
                        'method': 'pypdf_fallback'
                    }
                    
                    for i, page in enumerate(reader.pages):
                        try:
                            text = page.extract_text()
                            
                            page_data = {
                                'page_number': i + 1,
                                'text': text,
                                'image_path': None
                            }
                            extracted_data['pages'].append(page_data)
                            
                            # Save individual page text
                            text_file = output_folder / f"page_{i+1:03d}.txt"
                            with open(text_file, 'w', encoding='utf-8') as f:
                                f.write(text or "")
                                
                        except Exception as e:
                            logger.error(f"Failed to extract text from page {i+1}: {e}")
                    
                    # Save metadata
                    import json
                    metadata_file = output_folder / "metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(extracted_data, f, indent=2)
                    
                    logger.info(f"pypdf fallback: Processed {len(extracted_data['pages'])} pages")
                    return output_folder, extracted_data
                    
            except Exception as e:
                logger.error(f"pypdf fallback failed: {e}")
                raise
    
    return PyPDFConverter

def write_diagnostics_report(in_venv, pymupdf_success, pymupdf_version, alternatives, fallback_class):
    """Write comprehensive diagnostics report."""
    report_lines = [
        "=== PyMuPDF DIAGNOSTICS REPORT ===",
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "ENVIRONMENT:",
        f"  Python executable: {sys.executable}",
        f"  Python version: {sys.version}",
        f"  In virtual environment: {in_venv}",
        f"  Working directory: {os.getcwd()}",
        "",
        "PyMuPDF STATUS:",
        f"  Import successful: {pymupdf_success}",
        f"  Version: {pymupdf_version or 'N/A'}",
        "",
        "ALTERNATIVE LIBRARIES:",
    ]
    
    for name, info in alternatives.items():
        status = "Available" if info['available'] else "Not available"
        version = f" (v{info['version']})" if info['version'] else ""
        report_lines.append(f"  {name}: {status}{version}")
    
    report_lines.extend([
        "",
        "FALLBACK IMPLEMENTATION:",
        f"  Fallback class: {fallback_class.__name__ if fallback_class else 'None'}",
        f"  Fallback available: {fallback_class is not None}",
        "",
        "ROOT CAUSE ANALYSIS:",
    ])
    
    if not pymupdf_success:
        if not in_venv:
            report_lines.append("  - Not running in virtual environment")
            report_lines.append("  - PyMuPDF may need to be installed in correct environment")
        else:
            report_lines.append("  - PyMuPDF not installed or corrupted in virtual environment")
            report_lines.append("  - Solution: uv pip install PyMuPDF")
    
    if fallback_class:
        report_lines.extend([
            "",
            "FALLBACK FUNCTIONALITY:",
            "  - Text extraction: YES",
            "  - Image conversion: LIMITED/NO",
            "  - Table extraction: Depends on library",
            "  - Pipeline compatibility: YES (with reduced features)"
        ])
    
    report_content = "\n".join(report_lines)
    
    # Write to file
    with open("pymupdf_diagnostics.txt", "w") as f:
        f.write(report_content)
    
    logger.info("Diagnostics report written to pymupdf_diagnostics.txt")
    return report_content

def main():
    """Main diagnostic function."""
    logger.info("Starting PyMuPDF diagnostics and fallback implementation...")
    
    # 1. Environment check
    in_venv = log_environment()
    
    # 2. Package check
    uv_found_pymupdf = check_uv_packages()
    
    # 3. Import test
    pymupdf_success, pymupdf_version = test_pymupdf_import()
    
    # 4. Alternative libraries check
    alternatives = check_alternative_libraries()
    
    # 5. Implement fallback if needed
    fallback_class = None
    if not pymupdf_success:
        logger.warning("PyMuPDF failed - implementing fallback...")
        fallback_class = implement_fallback_pdf_converter(alternatives)
        
        if fallback_class:
            logger.info(f"Fallback implementation ready: {fallback_class.__name__}")
            
            # Test fallback with a simple example
            try:
                converter = fallback_class()
                logger.info("Fallback converter instantiated successfully")
            except Exception as e:
                logger.error(f"Fallback converter failed to instantiate: {e}")
        else:
            logger.error("No suitable fallback implementation available")
    
    # 6. Write comprehensive report
    report = write_diagnostics_report(in_venv, pymupdf_success, pymupdf_version, alternatives, fallback_class)
    
    # 7. Summary and exit code
    logger.info("=== DIAGNOSTIC SUMMARY ===")
    if pymupdf_success:
        logger.info("PyMuPDF working correctly - no fallback needed")
        return 0
    elif fallback_class:
        logger.warning("PyMuPDF failed but fallback implementation available")
        logger.warning("Pipeline can continue with reduced functionality")
        return 1
    else:
        logger.error("PyMuPDF failed and no fallback available")
        logger.error("Pipeline will fail without PDF processing capability")
        return 2

if __name__ == "__main__":
    import json
    from datetime import datetime
    exit_code = main()
    print(f"Exit code: {exit_code}")
    sys.exit(exit_code)
