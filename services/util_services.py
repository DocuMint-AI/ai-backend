"""
Utility services for document processing.

This module provides utility functions for PDF processing, image conversion,
file management, and metadata handling for the AI backend system.
"""

import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Fallback PDF libraries
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pypdf
except ImportError:
    pypdf = None

from PIL import Image
import io

from .exceptions import PDFProcessingError, FileValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFToImageConverter:
    """
    Utility class for converting PDF pages to images and managing file structure.
    
    Handles PDF to image conversion, creates organized folder structures,
    and maintains metadata for processed documents.
    """
    
    def __init__(self, data_root: str = "/data", image_format: str = "PNG", dpi: int = 300):
        """
        Initialize PDF converter with configuration and fallback support.
        
        Args:
            data_root: Root directory for storing processed data
            image_format: Output image format (PNG, JPEG)
            dpi: Resolution for image conversion
            
        Example:
            >>> converter = PDFToImageConverter("/app/data", "PNG", 300)
        """
        self.data_root = Path(data_root)
        self.image_format = image_format.upper()
        self.dpi = dpi
        
        # Ensure data directory exists
        self.data_root.mkdir(parents=True, exist_ok=True)
        
        # Determine PDF processing library with fallback hierarchy
        self.pdf_library = None
        self.library_name = None
        
        # Try PyMuPDF first
        if fitz:
            try:
                # Test PyMuPDF import with actual functionality
                test_doc = fitz.open()
                test_doc.close()
                self.pdf_library = fitz
                self.library_name = "PyMuPDF"
                logger.info("Using PyMuPDF for PDF processing")
            except Exception as e:
                logger.warning(f"PyMuPDF import failed: {e}")
        
        # Try pdfplumber fallback
        if not self.pdf_library and pdfplumber:
            try:
                # Test pdfplumber functionality
                self.pdf_library = pdfplumber
                self.library_name = "pdfplumber"
                logger.info("Using pdfplumber as fallback for PDF processing")
            except Exception as e:
                logger.warning(f"pdfplumber fallback failed: {e}")
        
        # Try PyPDF2 fallback
        if not self.pdf_library and PyPDF2:
            try:
                # Test PyPDF2 functionality
                self.pdf_library = PyPDF2
                self.library_name = "PyPDF2"
                logger.info("Using PyPDF2 as fallback for PDF processing")
            except Exception as e:
                logger.warning(f"PyPDF2 fallback failed: {e}")
        
        # Try pypdf fallback
        if not self.pdf_library and pypdf:
            try:
                # Test pypdf functionality
                self.pdf_library = pypdf
                self.library_name = "pypdf"
                logger.info("Using pypdf as fallback for PDF processing")
            except Exception as e:
                logger.warning(f"pypdf fallback failed: {e}")
        
        if not self.pdf_library:
            raise ImportError(
                "No suitable PDF library available. Install one of: PyMuPDF, pdfplumber, PyPDF2, or pypdf\n"
                "Recommended: uv pip install PyMuPDF pdfplumber PyPDF2 pypdf"
            )
        
        logger.info(f"Initialized PDF converter using {self.library_name}: {data_root}, {image_format}, {dpi}DPI")
    
    def generate_uid(self, pdf_path: str) -> str:
        """
        Generate unique identifier for PDF based on file content and metadata.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Unique identifier string
            
        Example:
            >>> converter = PDFToImageConverter()
            >>> uid = converter.generate_uid("document.pdf")
            >>> print(uid)  # "abc123def-456789"
        """
        pdf_path = Path(pdf_path)
        
        # Create hash based on file content and metadata
        hasher = hashlib.sha256()
        
        # Include file content hash
        with open(pdf_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        # Include file metadata
        stat = pdf_path.stat()
        metadata_string = f"{pdf_path.name}_{stat.st_size}_{stat.st_mtime}"
        hasher.update(metadata_string.encode())
        
        # Generate short UUID-like identifier
        file_hash = hasher.hexdigest()[:16]
        unique_id = f"{file_hash[:8]}-{file_hash[8:]}"
        
        logger.debug(f"Generated UID for {pdf_path.name}: {unique_id}")
        return unique_id
    
    def create_folder_structure(self, pdf_name: str, uid: str) -> Path:
        """
        Create organized folder structure for PDF processing.
        
        Args:
            pdf_name: Name of the PDF file (without extension)
            uid: Unique identifier for the PDF
            
        Returns:
            Path to the created folder
            
        Example:
            >>> converter = PDFToImageConverter()
            >>> folder = converter.create_folder_structure("invoice", "abc123-def456")
            >>> print(folder)  # /data/invoice-abc123-def456
        """
        folder_name = f"{pdf_name}-{uid}"
        folder_path = self.data_root / folder_name
        
        # Create folder structure
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (folder_path / "images").mkdir(exist_ok=True)
        (folder_path / "ocr_results").mkdir(exist_ok=True)
        
        logger.info(f"Created folder structure: {folder_path}")
        return folder_path
    
    def convert_pdf_to_images(
        self, 
        pdf_path: str, 
        output_folder: Optional[str] = None
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Convert PDF pages to images and create organized file structure.
        
        Args:
            pdf_path: Path to the input PDF file
            output_folder: Optional custom output folder path
            
        Returns:
            Tuple of (uid, image_paths, metadata)
            
        Raises:
            PDFProcessingError: If PDF processing fails
            FileNotFoundError: If PDF file doesn't exist
            
        Example:
            >>> converter = PDFToImageConverter()
            >>> uid, images, metadata = converter.convert_pdf_to_images("doc.pdf")
            >>> print(f"Processed {len(images)} pages with UID: {uid}")
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Generate UID and create folder structure
            uid = self.generate_uid(str(pdf_path))
            pdf_name = pdf_path.stem
            
            if output_folder:
                folder_path = Path(output_folder)
                folder_path.mkdir(parents=True, exist_ok=True)
            else:
                folder_path = self.create_folder_structure(pdf_name, uid)
            
            logger.info(f"Processing PDF: {pdf_path.name} using {self.library_name}")
            
            # Process PDF based on available library
            if self.library_name == "PyMuPDF":
                return self._convert_with_pymupdf(pdf_path, folder_path, uid, pdf_name)
            elif self.library_name == "pdfplumber":
                return self._convert_with_pdfplumber(pdf_path, folder_path, uid, pdf_name)
            elif self.library_name == "PyPDF2":
                return self._convert_with_pypdf2(pdf_path, folder_path, uid, pdf_name)
            elif self.library_name == "pypdf":
                return self._convert_with_pypdf(pdf_path, folder_path, uid, pdf_name)
            else:
                raise PDFProcessingError(f"Unsupported PDF library: {self.library_name}")
                
        except Exception as e:
            error_msg = f"Failed to process PDF {pdf_path}: {str(e)}"
            logger.error(error_msg)
            raise PDFProcessingError(error_msg) from e
    
    def _convert_with_pymupdf(self, pdf_path: Path, folder_path: Path, uid: str, pdf_name: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Convert PDF using PyMuPDF (optimal with image conversion)."""
        pdf_document = self.pdf_library.open(str(pdf_path))
        total_pages = len(pdf_document)
        
        image_paths = []
        processing_errors = []
        
        for page_num in range(total_pages):
            try:
                page = pdf_document[page_num]
                
                # Convert page to image
                mat = self.pdf_library.Matrix(self.dpi / 72, self.dpi / 72)  # Scale factor for DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Save image
                image_filename = f"page_{page_num + 1:03d}.{self.image_format.lower()}"
                image_path = folder_path / "images" / image_filename
                
                if self.image_format == "PNG":
                    pix.save(str(image_path))
                else:  # JPEG
                    # Convert to PIL Image for JPEG (better quality control)
                    img_data = pix.tobytes("ppm")
                    img = Image.open(io.BytesIO(img_data))
                    img.save(str(image_path), "JPEG", quality=95, optimize=True)
                
                image_paths.append(str(image_path))
                logger.debug(f"Converted page {page_num + 1} -> {image_path}")
                
            except Exception as e:
                error_msg = f"Error processing page {page_num + 1}: {str(e)}"
                logger.warning(error_msg)
                processing_errors.append(error_msg)
        
        pdf_document.close()
        
        # Create metadata
        metadata = self.create_metadata(
            pdf_path=str(pdf_path),
            uid=uid,
            pdf_name=pdf_name,
            total_pages=total_pages,
            processed_pages=len(image_paths),
            image_paths=image_paths,
            processing_errors=processing_errors,
            folder_path=str(folder_path)
        )
        
        # Save metadata
        self.save_metadata(folder_path, metadata)
        
        logger.info(f"Successfully converted {len(image_paths)}/{total_pages} pages with PyMuPDF")
        return uid, image_paths, metadata
    
    def _convert_with_pdfplumber(self, pdf_path: Path, folder_path: Path, uid: str, pdf_name: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Convert PDF using pdfplumber (text extraction focus, limited image conversion)."""
        with self.pdf_library.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            text_files = []
            processing_errors = []
            
            for i, page in enumerate(pdf.pages):
                try:
                    # Extract text with layout information
                    text = page.extract_text()
                    
                    # Extract tables if any
                    tables = page.extract_tables()
                    
                    # Save text file (no image conversion capability)
                    text_filename = f"page_{i + 1:03d}.txt"
                    text_path = folder_path / "text" / text_filename
                    text_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(text or "")
                    
                    text_files.append(str(text_path))
                    
                    # Save tables if any
                    if tables:
                        table_filename = f"page_{i + 1:03d}_tables.json"
                        table_path = folder_path / "tables" / table_filename
                        table_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(table_path, 'w') as f:
                            json.dump(tables, f, indent=2)
                    
                    logger.debug(f"Extracted text from page {i + 1}")
                    
                except Exception as e:
                    error_msg = f"Error processing page {i + 1}: {str(e)}"
                    logger.warning(error_msg)
                    processing_errors.append(error_msg)
            
            # Create metadata for text-based processing
            metadata = self.create_metadata(
                pdf_path=str(pdf_path),
                uid=uid,
                pdf_name=pdf_name,
                total_pages=total_pages,
                processed_pages=len(text_files),
                image_paths=[],  # No image conversion
                text_paths=text_files,
                processing_errors=processing_errors,
                folder_path=str(folder_path),
                processing_method="text_extraction_pdfplumber"
            )
            
            # Save metadata
            self.save_metadata(folder_path, metadata)
            
            logger.info(f"Successfully extracted text from {len(text_files)}/{total_pages} pages with pdfplumber")
            logger.warning("Note: pdfplumber fallback - no image conversion, text extraction only")
            
            return uid, text_files, metadata
    
    def _convert_with_pypdf2(self, pdf_path: Path, folder_path: Path, uid: str, pdf_name: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Convert PDF using PyPDF2 (text extraction only)."""
        with open(pdf_path, 'rb') as file:
            reader = self.pdf_library.PdfReader(file)
            total_pages = len(reader.pages)
            
            text_files = []
            processing_errors = []
            
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    
                    # Save text file
                    text_filename = f"page_{i + 1:03d}.txt"
                    text_path = folder_path / "text" / text_filename
                    text_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    text_files.append(str(text_path))
                    logger.debug(f"Extracted text from page {i + 1}")
                    
                except Exception as e:
                    error_msg = f"Error processing page {i + 1}: {str(e)}"
                    logger.warning(error_msg)
                    processing_errors.append(error_msg)
            
            # Create metadata for text-based processing
            metadata = self.create_metadata(
                pdf_path=str(pdf_path),
                uid=uid,
                pdf_name=pdf_name,
                total_pages=total_pages,
                processed_pages=len(text_files),
                image_paths=[],  # No image conversion
                text_paths=text_files,
                processing_errors=processing_errors,
                folder_path=str(folder_path),
                processing_method="text_extraction_pypdf2"
            )
            
            # Save metadata
            self.save_metadata(folder_path, metadata)
            
            logger.info(f"Successfully extracted text from {len(text_files)}/{total_pages} pages with PyPDF2")
            logger.warning("Note: PyPDF2 fallback - no image conversion, text extraction only")
            
            return uid, text_files, metadata
    
    def _convert_with_pypdf(self, pdf_path: Path, folder_path: Path, uid: str, pdf_name: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Convert PDF using pypdf (text extraction only)."""
        with open(pdf_path, 'rb') as file:
            reader = self.pdf_library.PdfReader(file)
            total_pages = len(reader.pages)
            
            text_files = []
            processing_errors = []
            
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    
                    # Save text file
                    text_filename = f"page_{i + 1:03d}.txt"
                    text_path = folder_path / "text" / text_filename
                    text_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(text or "")
                    
                    text_files.append(str(text_path))
                    logger.debug(f"Extracted text from page {i + 1}")
                    
                except Exception as e:
                    error_msg = f"Error processing page {i + 1}: {str(e)}"
                    logger.warning(error_msg)
                    processing_errors.append(error_msg)
            
            # Create metadata for text-based processing
            metadata = self.create_metadata(
                pdf_path=str(pdf_path),
                uid=uid,
                pdf_name=pdf_name,
                total_pages=total_pages,
                processed_pages=len(text_files),
                image_paths=[],  # No image conversion
                text_paths=text_files,
                processing_errors=processing_errors,
                folder_path=str(folder_path),
                processing_method="text_extraction_pypdf"
            )
            
            # Save metadata
            self.save_metadata(folder_path, metadata)
            
            logger.info(f"Successfully extracted text from {len(text_files)}/{total_pages} pages with pypdf")
            logger.warning("Note: pypdf fallback - no image conversion, text extraction only")
            
            return uid, text_files, metadata
    
    def create_metadata(
        self,
        pdf_path: str,
        uid: str,
        pdf_name: str,
        total_pages: int,
        processed_pages: int,
        image_paths: List[str],
        processing_errors: List[str],
        folder_path: str,
        text_paths: Optional[List[str]] = None,
        processing_method: str = "image_conversion_pymupdf"
    ) -> Dict[str, Any]:
        """
        Create comprehensive metadata for processed PDF.
        
        Args:
            pdf_path: Original PDF file path
            uid: Unique identifier
            pdf_name: PDF filename without extension
            total_pages: Total number of pages in PDF
            processed_pages: Number of successfully processed pages
            image_paths: List of generated image file paths
            processing_errors: List of any processing errors
            folder_path: Output folder path
            text_paths: Optional list of text file paths (for fallback processing)
            processing_method: Method used for processing (e.g., image_conversion_pymupdf, text_extraction_pypdf2)
            
        Returns:
            Dictionary containing metadata
        """
        pdf_file = Path(pdf_path)
        stat = pdf_file.stat()
        
        metadata = {
            "uid": uid,
            "pdf_info": {
                "name": pdf_name,
                "original_path": str(pdf_path),
                "filename": pdf_file.name,
                "file_size_bytes": stat.st_size,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat()
            },
            "processing_info": {
                "processed_date": datetime.now().isoformat(),
                "total_pages": total_pages,
                "processed_pages": processed_pages,
                "success_rate": round((processed_pages / total_pages) * 100, 2),
                "image_format": self.image_format,
                "dpi": self.dpi,
                "processing_errors": processing_errors,
                "processing_method": processing_method,
                "pdf_library": self.library_name
            },
            "output_info": {
                "folder_path": folder_path,
                "folder_name": Path(folder_path).name,
                "image_paths": image_paths,
                "relative_image_paths": [
                    str(Path(p).relative_to(folder_path)) for p in image_paths
                ] if image_paths else [],
                "text_paths": text_paths or [],
                "relative_text_paths": [
                    str(Path(p).relative_to(folder_path)) for p in (text_paths or [])
                ]
            },
            "status": {
                "conversion_complete": len(processing_errors) == 0,
                "has_errors": len(processing_errors) > 0,
                "ready_for_ocr": processed_pages > 0,
                "has_images": len(image_paths) > 0 if image_paths else False,
                "has_text": len(text_paths) > 0 if text_paths else False,
                "fallback_mode": processing_method.startswith("text_extraction")
            }
        }
        
        return metadata
    
    def save_metadata(self, folder_path: Path, metadata: Dict[str, Any]) -> str:
        """
        Save metadata to JSON file in the processing folder.
        
        Args:
            folder_path: Path to the processing folder
            metadata: Metadata dictionary to save
            
        Returns:
            Path to the saved metadata file
        """
        metadata_path = folder_path / "metadata.json"
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved metadata: {metadata_path}")
        return str(metadata_path)
    
    def load_metadata(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """
        Load metadata from processing folder.
        
        Args:
            folder_path: Path to the processing folder
            
        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = Path(folder_path) / "metadata.json"
        
        if not metadata_path.exists():
            logger.warning(f"Metadata file not found: {metadata_path}")
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.debug(f"Loaded metadata from: {metadata_path}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error loading metadata from {metadata_path}: {e}")
            return None
    
    def get_processing_folders(self) -> List[Dict[str, Any]]:
        """
        Get list of all processing folders with their metadata.
        
        Returns:
            List of dictionaries containing folder info and metadata
        """
        folders = []
        
        for item in self.data_root.iterdir():
            if item.is_dir():
                metadata = self.load_metadata(str(item))
                if metadata:
                    folders.append({
                        "folder_path": str(item),
                        "folder_name": item.name,
                        "metadata": metadata
                    })
        
        logger.info(f"Found {len(folders)} processing folders")
        return folders
    
    def cleanup_folder(self, uid: str) -> bool:
        """
        Clean up processing folder for given UID.
        
        Args:
            uid: Unique identifier of the processing folder
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # Find folder with this UID
            for folder in self.data_root.iterdir():
                if folder.is_dir() and uid in folder.name:
                    import shutil
                    shutil.rmtree(folder)
                    logger.info(f"Cleaned up folder: {folder}")
                    return True
            
            logger.warning(f"No folder found for UID: {uid}")
            return False
            
        except Exception as e:
            logger.error(f"Error cleaning up folder for UID {uid}: {e}")
            return False


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file information
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    stat = file_path.stat()
    
    return {
        "name": file_path.name,
        "stem": file_path.stem,
        "suffix": file_path.suffix,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "is_file": file_path.is_file(),
        "absolute_path": str(file_path.absolute())
    }


def validate_pdf_file(file_path: str) -> bool:
    """
    Validate if file is a valid PDF.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        file_path = Path(file_path)
        
        # Check file extension
        if file_path.suffix.lower() != '.pdf':
            return False
        
        # Check if file exists and is readable
        if not file_path.exists() or not file_path.is_file():
            return False
        
        # Try to open with PyMuPDF
        if fitz:
            try:
                doc = fitz.open(str(file_path))
                page_count = len(doc)
                doc.close()
                return page_count > 0
            except Exception:
                return False
        
        # Fallback: check file header
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
            
    except Exception:
        return False


def execute_data_purge(
    operation: str = "quick",
    dry_run: bool = True,
    backup: bool = False
) -> Dict[str, Any]:
    """
    Execute data purge operation using the purge.py script.
    
    Args:
        operation: Type of purge operation ('quick', 'standard', 'full', 'nuclear')
        dry_run: Whether to perform a dry run (preview only)
        backup: Whether to create backup before deletion
        
    Returns:
        Dictionary containing purge results
        
    Example:
        >>> result = execute_data_purge("quick", dry_run=True)
        >>> print(f"Would delete {result['preview']['total_files']} files")
    """
    try:
        # Get project root directory
        current_dir = Path(__file__).parent.parent.absolute()
        script_path = current_dir / "scripts" / "purge.py"
        
        if not script_path.exists():
            return {
                "error": f"Purge script not found: {script_path}",
                "success": False
            }
        
        # Build command
        cmd = [sys.executable, str(script_path)]
        
        # Add operation flag
        if operation == "quick":
            cmd.append("--quick")
        elif operation == "standard":
            cmd.append("--standard")
        elif operation == "full":
            cmd.append("--full")
        elif operation == "nuclear":
            cmd.append("--nuclear")
        else:
            return {
                "error": f"Invalid operation: {operation}",
                "success": False
            }
        
        # Add options
        if dry_run:
            cmd.append("--dry-run")
        if backup:
            cmd.append("--backup")
        
        # Always use JSON output for API
        cmd.append("--json")
        cmd.append("--yes")  # Skip confirmation prompts
        
        logger.info(f"Executing purge command: {' '.join(cmd)}")
        
        # Execute command
        result = subprocess.run(
            cmd,
            cwd=str(current_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            try:
                # Parse JSON output from script
                output_data = json.loads(result.stdout)
                output_data["success"] = True
                logger.info(f"Purge operation '{operation}' completed successfully")
                return output_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse purge script output: {e}")
                return {
                    "error": "Failed to parse purge script output",
                    "raw_output": result.stdout,
                    "success": False
                }
        else:
            logger.error(f"Purge script failed with return code {result.returncode}")
            return {
                "error": f"Purge script failed: {result.stderr}",
                "return_code": result.returncode,
                "success": False
            }
            
    except subprocess.TimeoutExpired:
        logger.error("Purge operation timed out")
        return {
            "error": "Purge operation timed out (>5 minutes)",
            "success": False
        }
    except Exception as e:
        logger.error(f"Error executing purge operation: {e}")
        return {
            "error": f"Purge execution error: {str(e)}",
            "success": False
        }


def get_data_usage_summary() -> Dict[str, Any]:
    """
    Get summary of data directory usage and file counts.
    
    Returns:
        Dictionary containing usage statistics
        
    Example:
        >>> usage = get_data_usage_summary()
        >>> print(f"Total size: {usage['total_size_formatted']}")
    """
    try:
        # Get project root directory
        current_dir = Path(__file__).parent.parent.absolute()
        data_dir = current_dir / "data"
        
        if not data_dir.exists():
            return {
                "error": "Data directory not found",
                "success": False
            }
        
        def calculate_dir_size(directory: Path) -> Tuple[int, int]:
            """Calculate total size and file count for directory."""
            total_size = 0
            file_count = 0
            
            try:
                for item in directory.rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                        file_count += 1
            except (PermissionError, OSError):
                pass
            
            return total_size, file_count
        
        def format_size(size_bytes: int) -> str:
            """Format bytes as human readable string."""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        
        # Calculate usage for different categories
        categories = {
            "uploads": data_dir / "uploads",
            "processed": data_dir.glob("*-*/"),  # Processing result folders
            "temp": data_dir / "temp",
            "test_files": data_dir / "test-files",
            "logs": data_dir / "logs",
            "credentials": data_dir / ".cheetah"
        }
        
        usage_summary = {
            "data_directory": str(data_dir),
            "categories": {},
            "total_size": 0,
            "total_files": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        for category, path_pattern in categories.items():
            category_size = 0
            category_files = 0
            
            if isinstance(path_pattern, Path) and path_pattern.exists():
                category_size, category_files = calculate_dir_size(path_pattern)
            elif hasattr(path_pattern, '__iter__'):  # glob pattern
                for folder in path_pattern:
                    if folder.is_dir():
                        size, files = calculate_dir_size(folder)
                        category_size += size
                        category_files += files
            
            usage_summary["categories"][category] = {
                "size_bytes": category_size,
                "size_formatted": format_size(category_size),
                "file_count": category_files
            }
            
            usage_summary["total_size"] += category_size
            usage_summary["total_files"] += category_files
        
        usage_summary["total_size_formatted"] = format_size(usage_summary["total_size"])
        usage_summary["success"] = True
        
        logger.info(f"Data usage calculated: {usage_summary['total_size_formatted']}")
        return usage_summary
        
    except Exception as e:
        logger.error(f"Error calculating data usage: {e}")
        return {
            "error": f"Failed to calculate data usage: {str(e)}",
            "success": False
        }


if __name__ == "__main__":
    """
    Demo usage of PDF processing utilities.
    """
    # Example usage
    try:
        converter = PDFToImageConverter(data_root="./test_data", dpi=200)
        
        # Note: This would require an actual PDF file for testing
        # uid, images, metadata = converter.convert_pdf_to_images("sample.pdf")
        # print(f"Processed PDF with UID: {uid}")
        # print(f"Generated {len(images)} images")
        
        print("PDFToImageConverter initialized successfully!")
        print("Place a PDF file and uncomment the demo code to test conversion.")
        
        # Test file validation
        print(f"PDF validation test (non-existent): {validate_pdf_file('test.pdf')}")
        
        # Get processing folders
        folders = converter.get_processing_folders()
        print(f"Found {len(folders)} existing processing folders")
        
        # Test data usage summary
        usage = get_data_usage_summary()
        if usage.get("success"):
            print(f"Data usage: {usage['total_size_formatted']} ({usage['total_files']} files)")
        
        # Test purge operation (dry run)
        purge_result = execute_data_purge("quick", dry_run=True)
        if purge_result.get("success"):
            preview = purge_result.get("preview", {})
            print(f"Quick purge preview: {preview.get('total_files', 0)} files")
        
    except Exception as e:
        print(f"Demo error: {e}")