"""
Utility services for document processing.

This module provides utility functions for PDF processing, image conversion,
file management, and metadata handling for the AI backend system.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from PIL import Image
import io


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""
    pass


class PDFToImageConverter:
    """
    Utility class for converting PDF pages to images and managing file structure.
    
    Handles PDF to image conversion, creates organized folder structures,
    and maintains metadata for processed documents.
    """
    
    def __init__(self, data_root: str = "/data", image_format: str = "PNG", dpi: int = 300):
        """
        Initialize PDF converter with configuration.
        
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
        
        # Validate dependencies
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")
        
        logger.info(f"Initialized PDF converter: {data_root}, {image_format}, {dpi}DPI")
    
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
            
            # Open PDF document
            pdf_document = fitz.open(str(pdf_path))
            total_pages = len(pdf_document)
            
            logger.info(f"Processing PDF: {pdf_path.name} ({total_pages} pages)")
            
            # Convert each page to image
            image_paths = []
            processing_errors = []
            
            for page_num in range(total_pages):
                try:
                    page = pdf_document[page_num]
                    
                    # Convert page to image
                    mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # Scale factor for DPI
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
            
            logger.info(f"Successfully converted {len(image_paths)}/{total_pages} pages")
            
            if processing_errors:
                logger.warning(f"Encountered {len(processing_errors)} processing errors")
            
            return uid, image_paths, metadata
            
        except Exception as e:
            error_msg = f"Failed to process PDF {pdf_path}: {str(e)}"
            logger.error(error_msg)
            raise PDFProcessingError(error_msg) from e
    
    def create_metadata(
        self,
        pdf_path: str,
        uid: str,
        pdf_name: str,
        total_pages: int,
        processed_pages: int,
        image_paths: List[str],
        processing_errors: List[str],
        folder_path: str
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
                "processing_errors": processing_errors
            },
            "output_info": {
                "folder_path": folder_path,
                "folder_name": Path(folder_path).name,
                "image_paths": image_paths,
                "relative_image_paths": [
                    str(Path(p).relative_to(folder_path)) for p in image_paths
                ]
            },
            "status": {
                "conversion_complete": len(processing_errors) == 0,
                "has_errors": len(processing_errors) > 0,
                "ready_for_ocr": processed_pages > 0
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
        
    except Exception as e:
        print(f"Demo error: {e}")