"""
Processing Handler Router

This router contains all endpoints related to document processing,
OCR operations, and file management. Migrated from services/processing-handler.py
to support modular router architecture.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback
import hashlib

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from PIL import Image

# Import our services - fix for util-services.py filename
import sys
import importlib.util

# Get the services directory path
services_dir = Path(__file__).parent.parent / "services"
sys.path.append(str(services_dir))

# Import from util-services.py file
util_services_spec = importlib.util.spec_from_file_location("util_services", 
    services_dir / "util-services.py")
util_services = importlib.util.module_from_spec(util_services_spec)
util_services_spec.loader.exec_module(util_services)

PDFToImageConverter = util_services.PDFToImageConverter
validate_pdf_file = util_services.validate_pdf_file  
get_file_info = util_services.get_file_info

# Import from OCR-processing.py file
ocr_spec = importlib.util.spec_from_file_location("ocr_processing", 
    services_dir / "preprocessing" / "OCR-processing.py")
ocr_module = importlib.util.module_from_spec(ocr_spec)
ocr_spec.loader.exec_module(ocr_module)

GoogleVisionOCR = ocr_module.GoogleVisionOCR
OCRResult = ocr_module.OCRResult

# Import parsing module
parsing_spec = importlib.util.spec_from_file_location("parsing",
    services_dir / "preprocessing" / "parsing.py")
parsing_module = importlib.util.module_from_spec(parsing_spec)
parsing_spec.loader.exec_module(parsing_module)

LocalTextParser = parsing_module.LocalTextParser
ParsedDocument = parsing_module.ParsedDocument

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Global configuration from environment variables
CONFIG = {
    "google_project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
    "google_credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    "data_root": os.getenv("DATA_ROOT", "/data"),
    "image_format": os.getenv("IMAGE_FORMAT", "PNG"),
    "image_dpi": int(os.getenv("IMAGE_DPI", "300")),
    "language_hints": os.getenv("LANGUAGE_HINTS", "en").split(","),
    "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "50"))
}

# Initialize services
pdf_converter = PDFToImageConverter(
    data_root=CONFIG["data_root"],
    image_format=CONFIG["image_format"],
    dpi=CONFIG["image_dpi"]
)

# Initialize OCR service (will be created when needed to handle auth errors gracefully)
ocr_service = None


# Pydantic models for API requests/responses
class OCRRequest(BaseModel):
    """Request model for OCR processing."""
    pdf_path: str = Field(..., description="Path to the PDF file to process")
    language_hints: Optional[List[str]] = Field(
        default=None, 
        description="Language hints for OCR (e.g., ['en', 'es'])"
    )
    force_reprocess: bool = Field(
        default=False, 
        description="Force reprocessing even if results exist"
    )


class OCRResponse(BaseModel):
    """Response model for OCR processing."""
    success: bool
    uid: str
    message: str
    processing_folder: str
    total_pages: int
    processed_pages: int
    ocr_results_path: str
    metadata: Dict[str, Any]
    errors: Optional[List[str]] = None


class ProcessingStatus(BaseModel):
    """Model for processing status."""
    uid: str
    status: str
    progress: float
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    errors: List[str] = []


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    message: str
    file_path: str
    file_info: Dict[str, Any]


class PurgeRequest(BaseModel):
    """Request model for purge operations."""
    operation: str = Field(..., description="Type of purge operation", 
                          pattern="^(quick|standard|full|nuclear)$")
    dry_run: bool = Field(default=True, description="Whether to perform a dry run")
    backup: bool = Field(default=False, description="Whether to create backup before deletion")


class PurgeResponse(BaseModel):
    """Response model for purge operations."""
    operation: str
    dry_run: bool
    success: bool
    preview: Dict[str, Any]
    deleted_items: Optional[List[str]] = None
    backup_dir: Optional[str] = None
    error: Optional[str] = None


class DataUsageResponse(BaseModel):
    """Response model for data usage information."""
    success: bool
    data_directory: str
    categories: Dict[str, Dict[str, Any]]
    total_size: int
    total_size_formatted: str
    total_files: int
    last_updated: str
    error: Optional[str] = None


def get_ocr_service() -> GoogleVisionOCR:
    """
    Get or initialize OCR service with error handling.
    
    Returns:
        GoogleVisionOCR instance
        
    Raises:
        HTTPException: If OCR service cannot be initialized
    """
    global ocr_service
    
    if ocr_service is None:
        try:
            if not CONFIG["google_project_id"] or not CONFIG["google_credentials_path"]:
                raise ValueError("Google Cloud credentials not configured")
            
            ocr_service = GoogleVisionOCR(
                project_id=CONFIG["google_project_id"],
                credentials_path=CONFIG["google_credentials_path"],
                language_hints=CONFIG["language_hints"]
            )
            logger.info("OCR service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OCR service: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"OCR service initialization failed: {str(e)}"
            )
    
    return ocr_service


def get_image_dimensions(image_path: str) -> tuple:
    """
    Get image dimensions (width, height).
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (width, height)
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.warning(f"Could not get dimensions for {image_path}: {e}")
        return (1240, 1754)  # Default dimensions


def generate_document_id(pdf_path: str) -> str:
    """
    Generate a unique document ID.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Unique document ID
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    pdf_name = Path(pdf_path).stem
    
    # Create a short hash from the file path and current time
    hasher = hashlib.md5()
    hasher.update(f"{pdf_path}_{datetime.now().isoformat()}".encode())
    short_hash = hasher.hexdigest()[:8]
    
    return f"upload_{timestamp}_{short_hash}"


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if data directory is accessible
        data_path = Path(CONFIG["data_root"])
        data_accessible = data_path.exists() and os.access(data_path, os.W_OK)
        
        # Check OCR service (if credentials are configured)
        ocr_available = False
        ocr_error = None
        
        if CONFIG["google_project_id"] and CONFIG["google_credentials_path"]:
            try:
                get_ocr_service()
                ocr_available = True
            except Exception as e:
                ocr_error = str(e)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "data_directory": {
                    "accessible": data_accessible,
                    "path": CONFIG["data_root"]
                },
                "ocr_service": {
                    "available": ocr_available,
                    "error": ocr_error
                },
                "pdf_converter": {
                    "available": True,
                    "format": CONFIG["image_format"],
                    "dpi": CONFIG["image_dpi"]
                }
            },
            "config": {
                "max_file_size_mb": CONFIG["max_file_size_mb"],
                "language_hints": CONFIG["language_hints"]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a PDF file for processing.
    
    Args:
        file: PDF file to upload
        
    Returns:
        FileUploadResponse with file information
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Check file size
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        
        if file_size_mb > CONFIG["max_file_size_mb"]:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size_mb:.1f}MB) exceeds limit ({CONFIG['max_file_size_mb']}MB)"
            )
        
        # Create uploads directory
        uploads_dir = Path(CONFIG["data_root"]) / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Validate uploaded PDF
        if not validate_pdf_file(str(file_path)):
            os.remove(file_path)  # Clean up invalid file
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file"
            )
        
        # Get file information
        file_info = get_file_info(str(file_path))
        
        logger.info(f"Uploaded file: {file.filename} ({file_size_mb:.1f}MB)")
        
        return FileUploadResponse(
            success=True,
            message=f"File uploaded successfully: {file.filename}",
            file_path=str(file_path),
            file_info=file_info
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )


@router.post("/ocr-process", response_model=OCRResponse)
async def ocr_process(
    request: OCRRequest,
    background_tasks: BackgroundTasks
):
    """
    Process PDF with OCR pipeline using DocAI-compatible format.
    
    Converts PDF to images, runs OCR on each page, and stores results
    in the new DocAI schema format.
    
    Args:
        request: OCR processing request
        background_tasks: FastAPI background tasks
        
    Returns:
        OCRResponse with processing results
    """
    try:
        # Validate PDF file
        if not validate_pdf_file(request.pdf_path):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid PDF file: {request.pdf_path}"
            )
        
        # Get OCR service
        ocr = get_ocr_service()
        
        # Override language hints if provided
        if request.language_hints:
            ocr.language_hints = request.language_hints
        
        logger.info(f"Starting OCR processing for: {request.pdf_path}")
        
        # Convert PDF to images
        uid, image_paths, conversion_metadata = pdf_converter.convert_pdf_to_images(
            request.pdf_path
        )
        
        processing_folder = Path(conversion_metadata["output_info"]["folder_path"])
        total_pages = conversion_metadata["processing_info"]["total_pages"]
        
        # Generate document ID
        document_id = generate_document_id(request.pdf_path)
        original_filename = Path(request.pdf_path).name
        
        # Check if OCR results already exist and not forcing reprocess
        ocr_results_path = processing_folder / f"{Path(request.pdf_path).stem}-{uid}.json"
        
        if ocr_results_path.exists() and not request.force_reprocess:
            logger.info(f"OCR results already exist for UID {uid}, skipping processing")
            
            # Load existing results
            with open(ocr_results_path, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
            
            return OCRResponse(
                success=True,
                uid=uid,
                message="OCR results already available (use force_reprocess=true to reprocess)",
                processing_folder=str(processing_folder),
                total_pages=total_pages,
                processed_pages=len(existing_results.get("ocr_result", {}).get("pages", [])),
                ocr_results_path=str(ocr_results_path),
                metadata=conversion_metadata
            )
        
        # Process each page with OCR
        pages_data = []
        processing_errors = []
        processed_count = 0
        
        # Create derived images metadata
        derived_images = []
        
        for i, image_path in enumerate(image_paths, 1):
            try:
                logger.info(f"Processing page {i}/{total_pages}: {image_path}")
                
                # Get image dimensions
                width, height = get_image_dimensions(image_path)
                
                # Create image metadata
                image_metadata = {
                    "width": width,
                    "height": height,
                    "dpi": CONFIG["image_dpi"]
                }
                
                # Add to derived images list
                derived_images.append({
                    "page": i,
                    "image_uri": f"file://{image_path}",  # Local file URI
                    "width": width,
                    "height": height,
                    "dpi": CONFIG["image_dpi"]
                })
                
                # Run OCR on image
                page_result = ocr.extract_text(image_path, i, image_metadata)
                pages_data.append(page_result)
                
                processed_count += 1
                logger.debug(f"Page {i} OCR completed")
                
            except Exception as e:
                error_msg = f"OCR failed for page {i}: {str(e)}"
                logger.error(error_msg)
                processing_errors.append(error_msg)
                
                # Create error page data
                width, height = get_image_dimensions(image_path)
                error_page = {
                    "page_data": {
                        "page": i,
                        "width": width,
                        "height": height,
                        "page_confidence": 0.0,
                        "text_blocks": []
                    },
                    "warnings": [{
                        "page": i,
                        "block_id": None,
                        "code": "PROCESSING_ERROR",
                        "message": error_msg
                    }],
                    "full_text": ""
                }
                pages_data.append(error_page)
        
        # Create complete DocAI document
        try:
            docai_result = ocr.create_docai_document(
                document_id=document_id,
                original_filename=original_filename,
                pdf_path=request.pdf_path,
                pages_data=pages_data,
                derived_images=derived_images,
                pdf_uri=None  # Could be set if using GCS
            )
            
            # Convert to dictionary for JSON serialization
            ocr_results = {
                "document_id": docai_result.document_id,
                "original_filename": docai_result.original_filename,
                "file_fingerprint": docai_result.file_fingerprint,
                "pdf_uri": docai_result.pdf_uri,
                "derived_images": docai_result.derived_images,
                "language_detection": docai_result.language_detection,
                "ocr_result": docai_result.ocr_result,
                "extracted_assets": docai_result.extracted_assets,
                "preprocessing": docai_result.preprocessing,
                "warnings": docai_result.warnings
            }
            
        except Exception as e:
            logger.error(f"Error creating DocAI document: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create DocAI document: {str(e)}"
            )
        
        # Save OCR results
        with open(ocr_results_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OCR processing completed for UID {uid}: {processed_count}/{total_pages} pages")
        
        return OCRResponse(
            success=True,
            uid=uid,
            message=f"OCR processing completed: {processed_count}/{total_pages} pages processed",
            processing_folder=str(processing_folder),
            total_pages=total_pages,
            processed_pages=processed_count,
            ocr_results_path=str(ocr_results_path),
            metadata=conversion_metadata,
            errors=processing_errors if processing_errors else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.get("/results/{uid}")
async def get_results(uid: str):
    """
    Get OCR results for a specific UID.
    
    Args:
        uid: Unique identifier for the processing job
        
    Returns:
        OCR results and metadata
    """
    try:
        # Find processing folder
        folders = pdf_converter.get_processing_folders()
        target_folder = None
        
        for folder in folders:
            if uid in folder["folder_name"]:
                target_folder = folder
                break
        
        if not target_folder:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for UID: {uid}"
            )
        
        folder_path = Path(target_folder["folder_path"])
        
        # Find OCR results file
        ocr_files = list(folder_path.glob("*.json"))
        ocr_files = [f for f in ocr_files if f.name != "metadata.json"]
        
        if not ocr_files:
            raise HTTPException(
                status_code=404,
                detail=f"No OCR results found for UID: {uid}"
            )
        
        # Load OCR results
        ocr_results_path = ocr_files[0]
        with open(ocr_results_path, 'r', encoding='utf-8') as f:
            ocr_results = json.load(f)
        
        # Load metadata
        metadata = target_folder["metadata"]
        
        return {
            "uid": uid,
            "folder_path": str(folder_path),
            "ocr_results": ocr_results,
            "metadata": metadata,
            "docai_format": True,  # Indicate new format
            "files": {
                "ocr_results": str(ocr_results_path),
                "metadata": str(folder_path / "metadata.json"),
                "images": [
                    str(folder_path / path) 
                    for path in metadata["output_info"]["relative_image_paths"]
                ]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results for UID {uid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve results: {str(e)}"
        )


@router.get("/folders")
async def list_processing_folders():
    """
    List all processing folders with their metadata.
    
    Returns:
        List of processing folders and their status
    """
    try:
        folders = pdf_converter.get_processing_folders()
        
        # Enhance with OCR status
        for folder in folders:
            folder_path = Path(folder["folder_path"])
            
            # Check for OCR results
            ocr_files = list(folder_path.glob("*.json"))
            ocr_files = [f for f in ocr_files if f.name != "metadata.json"]
            
            # Check if it's DocAI format
            docai_format = False
            if ocr_files:
                try:
                    with open(ocr_files[0], 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                        docai_format = "document_id" in result_data and "ocr_result" in result_data
                except:
                    pass
            
            folder["ocr_status"] = {
                "has_results": len(ocr_files) > 0,
                "results_files": [str(f) for f in ocr_files],
                "docai_format": docai_format
            }
        
        return {
            "total_folders": len(folders),
            "folders": folders
        }
    
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list folders: {str(e)}"
        )


@router.delete("/cleanup/{uid}")
async def cleanup_processing_folder(uid: str):
    """
    Clean up processing folder for given UID.
    
    Args:
        uid: Unique identifier for the processing folder
        
    Returns:
        Cleanup status
    """
    try:
        success = pdf_converter.cleanup_folder(uid)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully cleaned up folder for UID: {uid}"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No folder found for UID: {uid}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup error for UID {uid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.post("/admin/purge", response_model=PurgeResponse)
async def execute_purge_operation(request: PurgeRequest):
    """
    Execute data purge operation.
    
    This endpoint allows cleaning up various categories of data files:
    - quick: Remove uploads and temp files
    - standard: Remove processing results, logs, temp files
    - full: Remove all generated data (safe categories)
    - nuclear: Remove EVERYTHING including test files and credentials
    
    Args:
        request: Purge operation parameters
        
    Returns:
        Purge operation results
        
    Example:
        POST /admin/purge
        {
            "operation": "quick",
            "dry_run": true,
            "backup": false
        }
    """
    try:
        logger.info(f"Executing purge operation: {request.operation}, dry_run={request.dry_run}")
        
        result = util_services.execute_data_purge(
            operation=request.operation,
            dry_run=request.dry_run,
            backup=request.backup
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Purge operation failed")
            )
        
        return PurgeResponse(**result)
        
    except Exception as e:
        logger.error(f"Purge operation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Purge operation failed: {str(e)}"
        )


@router.get("/admin/data-usage", response_model=DataUsageResponse)
async def get_data_usage():
    """
    Get data directory usage summary.
    
    Returns information about data directory usage including:
    - File counts and sizes by category
    - Total usage statistics
    - Last updated timestamp
    
    Returns:
        Data usage statistics
        
    Example:
        GET /admin/data-usage
        
        Response:
        {
            "success": true,
            "total_size_formatted": "25.3 MB",
            "total_files": 142,
            "categories": {
                "uploads": {"size_formatted": "5.2 MB", "file_count": 3},
                "processed": {"size_formatted": "18.1 MB", "file_count": 125}
            }
        }
    """
    try:
        logger.info("Calculating data usage summary")
        
        result = util_services.get_data_usage_summary()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to calculate data usage")
            )
        
        return DataUsageResponse(**result)
        
    except Exception as e:
        logger.error(f"Data usage calculation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data usage: {str(e)}"
        )