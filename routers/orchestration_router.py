"""
Orchestration Router for Document Processing Pipeline

This router provides a unified endpoint that orchestrates the complete document
processing flow: Upload PDF → Convert to Images → Vision AI → Document AI.
It uses existing router endpoints internally to maintain modularity.
"""

import json
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import internal router services to call existing endpoints
from .processing_handler import (
    upload_file,
    ocr_process,
    OCRRequest,
    FileUploadResponse,
    OCRResponse
)
from .doc_ai_router import (
    parse_document,
    ParseRequest,
    ParseResponse
)

# Import services for direct access
# from services.doc_ai.schema import ParseRequest as DocAIParseRequest
from services.project_utils import get_user_session_structure, resolve_user_session_paths

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1")

# Configuration
CONFIG = {
    "data_root": os.getenv("DATA_ROOT", "/data"),
    "temp_gcs_bucket": os.getenv("TEMP_GCS_BUCKET"),  # Optional for DocAI
    "google_project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
}


class ProcessingPipelineRequest(BaseModel):
    """Request model for complete document processing pipeline."""
    
    language_hints: Optional[List[str]] = Field(
        default=["en"], 
        description="Language hints for OCR processing"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for DocAI parsing"
    )
    processor_id: Optional[str] = Field(
        default=None,
        description="Optional DocAI processor ID override"
    )
    include_raw_response: bool = Field(
        default=False,
        description="Include raw DocAI response in results"
    )
    force_reprocess: bool = Field(
        default=False,
        description="Force reprocessing even if results exist"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata to include in processing"
    )


class ProcessingPipelineResponse(BaseModel):
    """Response model for complete document processing pipeline."""
    
    success: bool
    pipeline_id: str
    message: str
    
    # Stage results
    upload_result: Optional[Dict[str, Any]] = None
    ocr_result: Optional[Dict[str, Any]] = None
    docai_result: Optional[Dict[str, Any]] = None
    
    # Processing metadata
    total_processing_time: float
    stage_timings: Dict[str, float]
    
    # File paths and identifiers
    original_file_path: Optional[str] = None
    ocr_results_path: Optional[str] = None
    final_results_path: Optional[str] = None
    
    # Error information
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


class ProcessingStatus(BaseModel):
    """Model for tracking processing status."""
    
    pipeline_id: str
    current_stage: str
    progress_percentage: float
    total_stages: int
    completed_stages: int
    start_time: datetime
    current_stage_start: datetime
    estimated_completion: Optional[datetime] = None
    errors: List[str] = []
    warnings: List[str] = []


# Global state for tracking processing pipelines
PIPELINE_STATUS: Dict[str, ProcessingStatus] = {}


def update_pipeline_status(
    pipeline_id: str,
    stage: str,
    progress: float,
    error: Optional[str] = None,
    warning: Optional[str] = None
):
    """Update pipeline processing status."""
    if pipeline_id not in PIPELINE_STATUS:
        return
    
    status = PIPELINE_STATUS[pipeline_id]
    status.current_stage = stage
    status.progress_percentage = progress
    status.current_stage_start = datetime.now()
    
    if error:
        status.errors.append(error)
    if warning:
        status.warnings.append(warning)


def save_final_results(
    pipeline_id: str,
    upload_result: Dict[str, Any],
    ocr_result: Dict[str, Any],
    docai_result: Dict[str, Any],
    stage_timings: Dict[str, float],
    pdf_filename: str,
    username: Optional[str] = None
) -> str:
    """
    Save complete pipeline results to the user session folder structure.
    
    Args:
        pipeline_id: Unique pipeline identifier
        upload_result: Upload stage results
        ocr_result: OCR processing results
        docai_result: DocAI parsing results
        stage_timings: Processing time for each stage
        pdf_filename: Original PDF filename for UID generation
        username: Username (defaults to environment variable)
        
    Returns:
        Path to saved results file
    """
    try:
        # Get user session structure
        session_structure = get_user_session_structure(pdf_filename, username)
        pipeline_dir = session_structure["pipeline"]
        
        # Create comprehensive results document
        final_results = {
            "pipeline_id": pipeline_id,
            "user_session_id": session_structure["user_session_id"],
            "processing_timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.0.0",
            
            # Original file information
            "original_file": {
                "path": upload_result.get("file_path"),
                "info": upload_result.get("file_info", {})
            },
            
            # OCR processing results
            "ocr_processing": {
                "uid": ocr_result.get("uid"),
                "processing_folder": ocr_result.get("processing_folder"),
                "total_pages": ocr_result.get("total_pages"),
                "processed_pages": ocr_result.get("processed_pages"),
                "results_path": ocr_result.get("ocr_results_path"),
                "metadata": ocr_result.get("metadata", {})
            },
            
            # DocAI processing results
            "docai_processing": {
                "document": docai_result.get("document"),
                "request_id": docai_result.get("request_id"),
                "processing_time": docai_result.get("processing_time_seconds")
            },
            
            # Performance metrics
            "performance": {
                "total_processing_time": sum(stage_timings.values()),
                "stage_timings": stage_timings,
                "pipeline_efficiency": {
                    "upload_time_ratio": stage_timings.get("upload", 0) / sum(stage_timings.values()),
                    "ocr_time_ratio": stage_timings.get("ocr", 0) / sum(stage_timings.values()),
                    "docai_time_ratio": stage_timings.get("docai", 0) / sum(stage_timings.values())
                }
            },
            
            # Final extracted data (for easy access)
            "extracted_data": {
                "text_content": docai_result.get("document", {}).get("text", ""),
                "named_entities": docai_result.get("document", {}).get("named_entities", []),
                "clauses": docai_result.get("document", {}).get("clauses", []),
                "key_value_pairs": docai_result.get("document", {}).get("key_value_pairs", [])
            },
            
            # Session information
            "session_info": {
                "user_session_id": session_structure["user_session_id"],
                "base_path": str(session_structure["base_path"]),
                "pipeline_path": str(pipeline_dir)
            }
        }
        
        # Save to user session pipeline directory
        results_filename = f"pipeline_result_{pipeline_id}.json"
        results_path = pipeline_dir / results_filename
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Final pipeline results saved: {results_path}")
        return str(results_path)
        
    except Exception as e:
        logger.error(f"Failed to save final results for pipeline {pipeline_id}: {e}")
        raise


async def upload_pdf_to_gcs(file_path: str) -> Optional[str]:
    """
    Upload PDF to Google Cloud Storage for DocAI processing.
    
    Args:
        file_path: Local path to the PDF file
        
    Returns:
        GCS URI if upload successful, None if no bucket configured
    """
    if not CONFIG["temp_gcs_bucket"]:
        logger.info("No GCS bucket configured, DocAI will receive local file path")
        return None
    
    try:
        # TODO: Implement GCS upload if needed
        # For now, we'll work with local files
        logger.info("GCS upload not implemented, using local file path")
        return None
        
    except Exception as e:
        logger.warning(f"Failed to upload to GCS: {e}")
        return None


@router.post("/process-document", response_model=ProcessingPipelineResponse)
async def process_document_pipeline(
    file: UploadFile = File(...),
    language_hints: Optional[str] = "en",
    confidence_threshold: float = 0.7,
    processor_id: Optional[str] = None,
    include_raw_response: bool = False,
    force_reprocess: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Complete document processing pipeline.
    
    This endpoint orchestrates the full document processing flow:
    1. Upload PDF file securely
    2. Convert PDF to images
    3. Process with Vision AI (OCR)
    4. Parse with Document AI
    5. Save consolidated results
    
    Args:
        file: PDF file to process
        language_hints: Comma-separated language codes for OCR (e.g., "en,es")
        confidence_threshold: Confidence threshold for DocAI parsing (0.0-1.0)
        processor_id: Optional DocAI processor ID override
        include_raw_response: Include raw DocAI response in results
        force_reprocess: Force reprocessing even if results exist
        background_tasks: FastAPI background tasks
        
    Returns:
        ProcessingPipelineResponse with complete processing results
        
    Example:
        curl -X POST "http://localhost:8000/api/v1/process-document" \
             -F "file=@document.pdf" \
             -F "language_hints=en,hi" \
             -F "confidence_threshold=0.8"
    """
    pipeline_id = str(uuid.uuid4())
    start_time = time.time()
    stage_timings = {}
    errors = []
    warnings = []
    
    # Initialize pipeline status
    PIPELINE_STATUS[pipeline_id] = ProcessingStatus(
        pipeline_id=pipeline_id,
        current_stage="initializing",
        progress_percentage=0.0,
        total_stages=4,
        completed_stages=0,
        start_time=datetime.now(),
        current_stage_start=datetime.now()
    )
    
    try:
        logger.info(f"Starting document processing pipeline {pipeline_id} for file: {file.filename}")
        
        # Parse language hints
        lang_hints = [lang.strip() for lang in language_hints.split(",")] if language_hints else ["en"]
        
        # Stage 1: Upload PDF
        update_pipeline_status(pipeline_id, "uploading", 5.0)
        stage_start = time.time()
        
        upload_result = await upload_file(file)
        
        if not upload_result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Upload failed: {upload_result.message}"
            )
        
        stage_timings["upload"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "upload_complete", 25.0)
        
        logger.info(f"Pipeline {pipeline_id}: Upload completed in {stage_timings['upload']:.2f}s")
        
        # Stage 2: OCR Processing (PDF → Images → Vision AI)
        update_pipeline_status(pipeline_id, "ocr_processing", 30.0)
        stage_start = time.time()
        
        ocr_request = OCRRequest(
            pdf_path=upload_result.file_path,
            language_hints=lang_hints,
            force_reprocess=force_reprocess
        )
        
        ocr_result = await ocr_process(ocr_request, background_tasks)
        
        if not ocr_result.success:
            error_msg = f"OCR processing failed: {ocr_result.message}"
            errors.append(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        stage_timings["ocr"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "ocr_complete", 65.0)
        
        logger.info(f"Pipeline {pipeline_id}: OCR completed in {stage_timings['ocr']:.2f}s")
        
        # Stage 3: Document AI Processing
        update_pipeline_status(pipeline_id, "docai_processing", 70.0)
        stage_start = time.time()
        
        # Try to upload to GCS for DocAI (optional)
        gcs_uri = await upload_pdf_to_gcs(upload_result.file_path)
        
        if not gcs_uri:
            # Use local file path - DocAI may need different approach for local files
            # For now, we'll create a file:// URI
            gcs_uri = f"file://{upload_result.file_path}"
            warnings.append("Using local file path for DocAI - consider configuring GCS for better performance")
        
        # Create DocAI parse request
        docai_request = ParseRequest(
            gcs_uri=gcs_uri,
            confidence_threshold=confidence_threshold,
            processor_id=processor_id,
            include_raw_response=include_raw_response,
            metadata={
                "pipeline_id": pipeline_id,
                "original_filename": file.filename,
                "ocr_uid": ocr_result.uid,
                "processing_timestamp": datetime.now().isoformat()
            }
        )
        
        try:
            docai_result = await parse_document(docai_request, background_tasks)
            
            if not docai_result.success:
                error_msg = f"DocAI processing failed: {docai_result.error_message}"
                errors.append(error_msg)
                
                # Continue without DocAI results
                docai_result = ParseResponse(
                    success=False,
                    error_message=error_msg,
                    processing_time_seconds=0.0,
                    request_id=pipeline_id
                )
                warnings.append("Document AI processing failed, continuing with OCR results only")
            
        except Exception as e:
            error_msg = f"DocAI processing error: {str(e)}"
            errors.append(error_msg)
            warnings.append("Document AI processing failed, continuing with OCR results only")
            
            # Create minimal response
            docai_result = ParseResponse(
                success=False,
                error_message=error_msg,
                processing_time_seconds=0.0,
                request_id=pipeline_id
            )
        
        stage_timings["docai"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "docai_complete", 90.0)
        
        logger.info(f"Pipeline {pipeline_id}: DocAI completed in {stage_timings['docai']:.2f}s")
        
        # Stage 4: Save Final Results
        update_pipeline_status(pipeline_id, "saving_results", 95.0)
        stage_start = time.time()
        
        final_results_path = save_final_results(
            pipeline_id=pipeline_id,
            upload_result=upload_result.dict(),
            ocr_result=ocr_result.dict(),
            docai_result=docai_result.dict(),
            stage_timings=stage_timings,
            pdf_filename=file.filename
        )
        
        stage_timings["saving"] = time.time() - stage_start
        total_processing_time = time.time() - start_time
        
        update_pipeline_status(pipeline_id, "completed", 100.0)
        
        # Clean up pipeline status
        if pipeline_id in PIPELINE_STATUS:
            del PIPELINE_STATUS[pipeline_id]
        
        logger.info(f"Pipeline {pipeline_id}: Processing completed in {total_processing_time:.2f}s")
        
        return ProcessingPipelineResponse(
            success=True,
            pipeline_id=pipeline_id,
            message=f"Document processing completed successfully in {total_processing_time:.2f}s",
            upload_result=upload_result.dict(),
            ocr_result=ocr_result.dict(),
            docai_result=docai_result.dict(),
            total_processing_time=total_processing_time,
            stage_timings=stage_timings,
            original_file_path=upload_result.file_path,
            ocr_results_path=ocr_result.ocr_results_path,
            final_results_path=final_results_path,
            errors=errors if errors else None,
            warnings=warnings if warnings else None
        )
    
    except HTTPException:
        # Clean up pipeline status
        if pipeline_id in PIPELINE_STATUS:
            del PIPELINE_STATUS[pipeline_id]
        raise
        
    except Exception as e:
        # Clean up pipeline status
        if pipeline_id in PIPELINE_STATUS:
            del PIPELINE_STATUS[pipeline_id]
            
        total_processing_time = time.time() - start_time
        error_msg = f"Pipeline processing failed: {str(e)}"
        logger.error(f"Pipeline {pipeline_id}: {error_msg}")
        
        return ProcessingPipelineResponse(
            success=False,
            pipeline_id=pipeline_id,
            message=error_msg,
            total_processing_time=total_processing_time,
            stage_timings=stage_timings,
            errors=[error_msg] + errors,
            warnings=warnings
        )


@router.get("/pipeline-status/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """
    Get the current status of a processing pipeline.
    
    Args:
        pipeline_id: Unique pipeline identifier
        
    Returns:
        Current processing status
    """
    if pipeline_id not in PIPELINE_STATUS:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline {pipeline_id} not found or already completed"
        )
    
    return PIPELINE_STATUS[pipeline_id]


@router.get("/pipeline-results/{pipeline_id}")
async def get_pipeline_results(pipeline_id: str, pdf_filename: Optional[str] = None, username: Optional[str] = None):
    """
    Get the final results of a completed pipeline.
    
    Args:
        pipeline_id: Unique pipeline identifier
        pdf_filename: Optional PDF filename to resolve user session (if known)
        username: Optional username to resolve user session
        
    Returns:
        Complete pipeline results
    """
    try:
        # If we have session info, use new structure
        if pdf_filename:
            session_structure = get_user_session_structure(pdf_filename, username)
            results_file = session_structure["pipeline"] / f"pipeline_result_{pipeline_id}.json"
        else:
            # Fallback: search in old structure
            processed_dir = Path(CONFIG["data_root"]) / "processed"
            results_file = processed_dir / f"pipeline_result_{pipeline_id}.json"
            
            # If not found in old structure, try searching in user session directories
            if not results_file.exists():
                # Search all user session directories
                for user_dir in processed_dir.iterdir():
                    if user_dir.is_dir() and "-" in user_dir.name:  # username-UID format
                        potential_file = user_dir / "pipeline" / f"pipeline_result_{pipeline_id}.json"
                        if potential_file.exists():
                            results_file = potential_file
                            break
        
        if not results_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Results for pipeline {pipeline_id} not found"
            )
        
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to retrieve results for pipeline {pipeline_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pipeline results: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for orchestration service."""
    try:
        data_path = Path(CONFIG["data_root"])
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "document_processing_orchestration",
            "version": "1.0.0",
            "active_pipelines": len(PIPELINE_STATUS),
            "data_directory": {
                "accessible": data_path.exists() and os.access(data_path, os.W_OK),
                "path": str(data_path)
            },
            "configuration": {
                "gcs_bucket_configured": bool(CONFIG.get("temp_gcs_bucket")),
                "google_project_configured": bool(CONFIG.get("google_project_id"))
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )