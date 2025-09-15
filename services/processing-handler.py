"""
FastAPI processing handler for document OCR and parsing pipeline.

This module provides RESTful API endpoints for PDF processing, OCR,
and text parsing using the utility services and preprocessing modules.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Import our services - fix for util-services.py filename
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import from util-services.py file
import importlib.util
util_services_spec = importlib.util.spec_from_file_location("util_services", 
    os.path.join(os.path.dirname(__file__), "util-services.py"))
util_services = importlib.util.module_from_spec(util_services_spec)
util_services_spec.loader.exec_module(util_services)

PDFToImageConverter = util_services.PDFToImageConverter
validate_pdf_file = util_services.validate_pdf_file  
get_file_info = util_services.get_file_info

# Import from OCR-processing.py file
ocr_spec = importlib.util.spec_from_file_location("ocr_processing", 
    os.path.join(os.path.dirname(__file__), "preprocessing", "OCR-processing.py"))
ocr_module = importlib.util.module_from_spec(ocr_spec)
ocr_spec.loader.exec_module(ocr_module)

GoogleVisionOCR = ocr_module.GoogleVisionOCR
OCRResult = ocr_module.OCRResult

from preprocessing.parsing import LocalTextParser, ParsedDocument
import hashlib
from PIL import Image


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Backend Document Processing API",
    description="FastAPI service for PDF processing, OCR, and text parsing",
    version="1.0.0"
)

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


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Backend Document Processing API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "upload": "/upload",
            "ocr_process": "/ocr-process",
            "get_results": "/results/{uid}",
            "list_folders": "/folders",
            "status": "/status/{uid}"
        }
    }


@app.get("/health")
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


@app.post("/upload", response_model=FileUploadResponse)
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


@app.post("/ocr-process", response_model=OCRResponse)
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


@app.get("/results/{uid}")
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


@app.get("/folders")
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


@app.delete("/cleanup/{uid}")
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


if __name__ == "__main__":
    """
    Run the FastAPI application.
    """
    # Validate configuration
    required_env_vars = ["GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.warning("OCR functionality may not work properly")
    
    logger.info("Starting AI Backend Document Processing API")
    logger.info(f"Data root: {CONFIG['data_root']}")
    logger.info(f"Image format: {CONFIG['image_format']} @ {CONFIG['image_dpi']}DPI")
    
    uvicorn.run(
        "processing-handler:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )