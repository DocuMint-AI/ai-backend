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
from services.template_matching.regex_classifier import create_classifier
from services.kag_component import create_kag_component
from services.feature_emitter import emit_feature_vector
from services.kag_input_enhanced import create_kag_input_generator, create_kag_input_validator
from services.kag.kag_writer import generate_kag_input
from services.util_services import process_pdf_hybrid
from services.preprocessing.ocr_processing import GoogleVisionOCR

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
    classification_result: Optional[Dict[str, Any]],
    kag_result: Optional[Dict[str, Any]],
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
            
            # Classification results (MVP regex-based)
            "classification_processing": classification_result,
            
            # KAG processing results
            "kag_processing": kag_result,
            
            # Performance metrics
            "performance": {
                "total_processing_time": sum(stage_timings.values()),
                "stage_timings": stage_timings,
                "pipeline_efficiency": {
                    "upload_time_ratio": stage_timings.get("upload", 0) / sum(stage_timings.values()),
                    "ocr_time_ratio": stage_timings.get("ocr", 0) / sum(stage_timings.values()),
                    "docai_time_ratio": stage_timings.get("docai", 0) / sum(stage_timings.values()),
                    "classification_time_ratio": stage_timings.get("classification", 0) / sum(stage_timings.values()),
                    "kag_input_time_ratio": stage_timings.get("kag_input", 0) / sum(stage_timings.values()),
                    "kag_time_ratio": stage_timings.get("kag", 0) / sum(stage_timings.values())
                }
            },
            
            # Final extracted data (for easy access)
            "extracted_data": {
                "text_content": docai_result.get("document", {}).get("text", ""),
                "named_entities": docai_result.get("document", {}).get("named_entities", []),
                "clauses": docai_result.get("document", {}).get("clauses", []),
                "key_value_pairs": docai_result.get("document", {}).get("key_value_pairs", []),
                "classification_verdict": classification_result.get("classification_verdict") if classification_result else None,
                "kag_input_path": kag_result.get("kag_input_path") if kag_result else None
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
    Complete document processing pipeline (MVP with regex classification).
    
    This endpoint orchestrates the full document processing flow:
    1. Upload PDF file securely
    2. Convert PDF to images
    3. Process with Vision AI (OCR)
    4. Parse with Document AI
    5. Classify document using regex-based template matcher
    6. Process with KAG (Knowledge Augmented Generation) component
    7. Save consolidated results and artifacts
    
    MVP Features:
    - Single-document mode only (no multi-document handling)
    - Regex-based classification (no Vertex Matching Engine)
    - Vertex embedding disabled
    - KAG handoff active for downstream processing
    
    Args:
        file: PDF file to process (SINGLE DOCUMENT ONLY)
        language_hints: Comma-separated language codes for OCR (e.g., "en,es")
        confidence_threshold: Confidence threshold for DocAI parsing (0.0-1.0)
        processor_id: Optional DocAI processor ID override
        include_raw_response: Include raw DocAI response in results
        force_reprocess: Force reprocessing even if results exist
        background_tasks: FastAPI background tasks
        
    Returns:
        ProcessingPipelineResponse with complete processing results including:
        - classification_verdict.json in artifacts folder
        - kag_input.json for downstream processing
        - feature_vector.json with classifier_verdict field
        
    Example:
        curl -X POST "http://localhost:8000/api/v1/process-document" \
             -F "file=@document.pdf" \
             -F "language_hints=en,hi" \
             -F "confidence_threshold=0.8"
    """
    # MVP: Enforce single-document mode
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="MVP prototype supports single-document mode only. Please provide exactly one PDF file."
        )
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="MVP prototype supports PDF files only. Please upload a single PDF document."
        )
    pipeline_id = str(uuid.uuid4())
    start_time = time.time()
    stage_timings = {}
    errors = []
    warnings = []
    
    # Initialize pipeline status (MVP: 6 stages - Upload, OCR, DocAI, Classification, KAG Input, Final Save)
    PIPELINE_STATUS[pipeline_id] = ProcessingStatus(
        pipeline_id=pipeline_id,
        current_stage="initializing",
        progress_percentage=0.0,
        total_stages=6,
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
        
        # Stage 2: Hybrid PDF Processing (Images + Text Extraction)
        update_pipeline_status(pipeline_id, "pdf_processing", 30.0)
        stage_start = time.time()
        
        # Create processing directory
        from pathlib import Path
        pdf_path = Path(upload_result.file_path)
        user_session = get_user_session_structure(file.filename)
        artifacts_folder = user_session["base_path"] / "artifacts" / pipeline_id
        artifacts_folder.mkdir(parents=True, exist_ok=True)
        
        # Process PDF with hybrid approach
        logger.info(f"Pipeline {pipeline_id}: Starting hybrid PDF processing")
        hybrid_result = process_pdf_hybrid(
            pdf_path=pdf_path,
            output_dir=artifacts_folder,
            dpi=300,
            prefer_pymupdf=True
        )
        
        if not hybrid_result["success"] or not hybrid_result["page_texts"]:
            error_msg = f"Hybrid PDF processing failed: {hybrid_result.get('errors', ['Unknown error'])}"
            errors.append(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        stage_timings["pdf_processing"] = time.time() - stage_start
        logger.info(f"Pipeline {pipeline_id}: PDF processing completed in {stage_timings['pdf_processing']:.2f}s")
        logger.info(f"Successfully extracted text from {hybrid_result['processed_pages']}/{hybrid_result['total_pages']} pages")
        
        # Stage 3: Vision OCR Processing (if images available)
        update_pipeline_status(pipeline_id, "ocr_processing", 45.0)
        stage_start = time.time()
        
        vision_results = []
        if hybrid_result["image_paths"]:
            try:
                # Initialize Vision OCR
                ocr_service = GoogleVisionOCR.from_env(language_hints=lang_hints)
                
                # Process images with Vision OCR
                vision_results = ocr_service.process_image_list(
                    image_paths=hybrid_result["image_paths"],
                    plumber_texts=hybrid_result["page_texts"]
                )
                
                stage_timings["ocr"] = time.time() - stage_start
                logger.info(f"Pipeline {pipeline_id}: OCR completed in {stage_timings['ocr']:.2f}s")
                
            except Exception as e:
                logger.warning(f"Vision OCR processing failed: {e}")
                warnings.append(f"Vision OCR failed: {str(e)}")
                # Create fallback vision results
                for i, text in enumerate(hybrid_result["page_texts"]):
                    vision_results.append({
                        "page": i + 1,
                        "image_path": hybrid_result["image_paths"][i] if i < len(hybrid_result["image_paths"]) else "",
                        "vision_text": "",
                        "vision_confidence": 0.0,
                        "plumber_text": text,
                        "has_vision": False,
                        "has_plumber": bool(text.strip()),
                        "processing_error": str(e)
                    })
                stage_timings["ocr"] = time.time() - stage_start
        else:
            # No images available, use text-only results
            logger.info(f"Pipeline {pipeline_id}: No images available, using text-only processing")
            for i, text in enumerate(hybrid_result["page_texts"]):
                vision_results.append({
                    "page": i + 1,
                    "image_path": "",
                    "vision_text": "",
                    "vision_confidence": 0.0,
                    "plumber_text": text,
                    "has_vision": False,
                    "has_plumber": bool(text.strip()),
                    "processing_error": None
                })
            stage_timings["ocr"] = 0.0
        
        update_pipeline_status(pipeline_id, "ocr_complete", 60.0)
        
        # Merge text sources to create full document text
        full_text_parts = []
        total_confidence = 0.0
        confidence_count = 0
        
        for result in vision_results:
            # Prefer plumber text, fallback to vision text
            page_text = result.get("plumber_text", "") or result.get("vision_text", "")
            if page_text.strip():
                full_text_parts.append(page_text.strip())
            
            # Aggregate confidence values
            vision_conf = result.get("vision_confidence", 0.0)
            if vision_conf > 0.0:
                total_confidence += vision_conf
                confidence_count += 1
        
        full_text = "\n\n".join(full_text_parts)
        document_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        logger.info(f"Pipeline {pipeline_id}: Document confidence aggregated: {document_confidence:.3f} (from {confidence_count} pages)")
        
        # Create parsed_output.json with hybrid results
        parsed_output = {
            "full_text": full_text,
            "pages": vision_results,
            "document_confidence": document_confidence,  # Add aggregated confidence
            "metadata": {
                "processor_id": processor_id or "hybrid-processor",
                "pipeline_id": pipeline_id,
                "gcs_uri": f"file://{upload_result.file_path}",
                "processing_method": hybrid_result["method"],
                "total_pages": hybrid_result["total_pages"],
                "processed_pages": hybrid_result["processed_pages"],
                "timestamp": datetime.now().isoformat(),
                "language_hints": lang_hints,
                "errors": hybrid_result.get("errors", []),
                "warnings": warnings,
                "confidence_pages_processed": confidence_count
            }
        }
        
        # Save parsed_output.json atomically
        parsed_output_path = artifacts_folder / "parsed_output.json"
        temp_path = parsed_output_path.with_suffix('.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_output, f, indent=2, ensure_ascii=False, default=str)
        temp_path.replace(parsed_output_path)
        
        logger.info(f"Pipeline {pipeline_id}: Saved parsed_output.json with {len(full_text)} characters")
        
        # Stage 4: Document AI Processing (optional, using full_text)
        update_pipeline_status(pipeline_id, "docai_processing", 65.0)
        stage_start = time.time()
        
        docai_result = None
        try:
            # Skip DocAI for MVP, use parsed_output as source of truth
            logger.info(f"Pipeline {pipeline_id}: Skipping DocAI in MVP mode, using hybrid text extraction")
            docai_result = {
                "success": True,
                "document": {
                    "text": full_text,
                    "clauses": [],
                    "named_entities": [],
                    "key_value_pairs": []
                },
                "request_id": pipeline_id,
                "processing_time_seconds": 0.0
            }
            warnings.append("DocAI processing skipped in MVP mode")
            
        except Exception as e:
            error_msg = f"DocAI processing failed: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)
            docai_result = {
                "success": False,
                "error_message": error_msg,
                "request_id": pipeline_id,
                "processing_time_seconds": 0.0
            }
        
        stage_timings["docai"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "docai_complete", 70.0)
        logger.info(f"Pipeline {pipeline_id}: DocAI completed in {stage_timings['docai']:.2f}s")
        
        # Stage 5: Document Classification (Regex-based)
        update_pipeline_status(pipeline_id, "classification_processing", 75.0)
        stage_start = time.time()
        
        classification_result = None
        try:
            # Create classifier and classify using full_text
            classifier = create_classifier()
            
            if full_text.strip():
                # Perform regex classification
                classification_verdict = classifier.classify_document(
                    parsed_text=full_text,
                    document_metadata={
                        "pipeline_id": pipeline_id,
                        "original_filename": file.filename,
                        "source": "hybrid_processing",
                        "processing_method": hybrid_result["method"],
                        "total_pages": hybrid_result["total_pages"],
                        "document_confidence": document_confidence
                    }
                )
                
                # Export classification verdict
                verdict_dict = classifier.export_classification_verdict(classification_verdict)
                
                # Save classification verdict to artifacts folder
                classification_verdict_path = artifacts_folder / "classification_verdict.json"
                temp_path = classification_verdict_path.with_suffix('.tmp')
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(verdict_dict, f, indent=2, ensure_ascii=False, default=str)
                temp_path.replace(classification_verdict_path)
                
                classification_result = {
                    "success": True,
                    "classification_verdict": verdict_dict,
                    "classification_verdict_path": str(classification_verdict_path),
                    "document_text_length": len(full_text),
                    "source": "hybrid_processing"
                }
                
                logger.info(f"Document classified as '{classification_verdict.label}' (score={classification_verdict.score:.3f}, confidence={classification_verdict.confidence})")
                
            else:
                raise ValueError("No document text available for classification")
                
        except Exception as e:
            error_msg = f"Classification processing failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            # Create minimal classification result
            classification_result = {
                "success": False,
                "error_message": error_msg,
                "classification_verdict": None,
                "classification_verdict_path": None
            }
        
        stage_timings["classification"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "classification_complete", 85.0)
        logger.info(f"Pipeline {pipeline_id}: Classification completed in {stage_timings['classification']:.2f}s")
        
        # Stage 6: Generate KAG Input (Unified Schema)
        update_pipeline_status(pipeline_id, "kag_input_generation", 87.0)
        stage_start = time.time()
        
        kag_input_result = None
        try:
            # Only proceed if we have classification results
            if classification_result and classification_result["success"]:
                # Generate KAG input using the new unified writer
                kag_input_path = generate_kag_input(
                    artifact_dir=artifacts_folder,
                    doc_id=pipeline_id,
                    processor_id=processor_id or "hybrid-processor",
                    gcs_uri=f"file://{upload_result.file_path}",
                    pipeline_version="v1",
                    metadata={
                        "processing_method": hybrid_result["method"],
                        "total_pages": hybrid_result["total_pages"],
                        "processed_pages": hybrid_result["processed_pages"],
                        "original_filename": file.filename,
                        "language_hints": lang_hints,
                        "confidence_threshold": confidence_threshold,
                        "pipeline_timestamp": datetime.now().isoformat()
                    }
                )
                
                kag_input_result = {
                    "success": True,
                    "kag_input_path": kag_input_path,
                    "message": "KAG input generated successfully"
                }
                
                logger.info(f"KAG Input generated -> {kag_input_path}")
                
            else:
                error_msg = "Classification failed - cannot proceed with KAG input generation"
                logger.error(error_msg)
                kag_input_result = {
                    "success": False,
                    "error_message": error_msg,
                    "kag_input_path": None
                }
                
        except Exception as e:
            error_msg = f"KAG input generation failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            kag_input_result = {
                "success": False,
                "error_message": error_msg,
                "kag_input_path": None
            }
        
        stage_timings["kag_input"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "kag_input_generation_complete", 90.0)
        logger.info(f"Pipeline {pipeline_id}: KAG input generation completed in {stage_timings['kag_input']:.2f}s")
                
                # Create parsed_output.json from DocAI results (required for KAG writer)
                parsed_output_path = artifacts_folder / "parsed_output.json"
                parsed_output_data = {
                    "text": document_text,
                    "clauses": docai_result.document.get("clauses", []) if docai_result.success else [],
                    "named_entities": docai_result.document.get("named_entities", []) if docai_result.success else [],
                    "key_value_pairs": docai_result.document.get("key_value_pairs", []) if docai_result.success else [],
                    "needs_review": False,
                    "extraction_method": "docai" if docai_result.success else "ocr_fallback",
                    "processor_id": docai_result.request_id if docai_result.success else "ocr_processor"
                }
                
                with open(parsed_output_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_output_data, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"Parsed output saved to: {parsed_output_path}")
                
                # Generate KAG input using the new writer
                classification_verdict_path = classification_result["classification_verdict_path"]
                
                kag_input_path = generate_kag_input(
                    artifact_dir=artifacts_folder,
                    doc_id=pipeline_id,
                    processor_id=parsed_output_data["processor_id"],
                    gcs_uri=gcs_uri,
                    pipeline_version="v1",
                    metadata={
                        "pipeline_id": pipeline_id,
                        "original_filename": file.filename,
                        "processing_timestamp": datetime.now().isoformat(),
                        "source_method": "docai" if docai_result.success else "ocr",
                        "mvp_mode": True,
                        "classification_method": "regex_pattern_matching"
                    }
                )
                
                # Generate feature vector with classifier verdict
                try:
                    feature_vector_path = artifacts_folder / "feature_vector.json"
                    
                    emit_feature_vector(
                        parsed_output=parsed_output_data,
                        out_path=str(feature_vector_path),
                        classifier_verdict=classification_result["classification_verdict"]
                    )
                    
                    logger.info(f"Feature vector with classifier verdict saved to: {feature_vector_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate feature vector: {e}")
                    warnings.append(f"Feature vector generation failed: {str(e)}")
                
                kag_input_result = {
                    "success": True,
                    "kag_input_path": kag_input_path,
                    "parsed_output_path": str(parsed_output_path),
                    "processing_summary": {
                        "unified_schema_used": True,
                        "atomic_write_performed": True,
                        "artifacts_generated": ["kag_input.json", "parsed_output.json", "feature_vector.json"]
                    }
                }
                
                logger.info(f"KAG input generated successfully: {kag_input_path}")
                
            else:
                raise ValueError("Classification failed - cannot proceed with KAG input generation")
                
        except Exception as e:
            error_msg = f"KAG input generation failed: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)
            
            kag_input_result = {
                "success": False,
                "error_message": error_msg,
                "kag_input_path": None,
                "processing_summary": {}
            }
        
        stage_timings["kag_input"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "kag_input_complete", 90.0)
        
        logger.info(f"Pipeline {pipeline_id}: KAG input generation completed in {stage_timings['kag_input']:.2f}s")
        
        # Stage 6: Enhanced KAG Processing (Legacy - Optional)
        update_pipeline_status(pipeline_id, "kag_processing", 92.0)
        stage_start = time.time()
        
        kag_result = None
        try:
            # Only proceed if we have classification results and the new KAG input was generated
            if classification_result and classification_result["success"] and kag_input_result and kag_input_result["success"]:
                # Use the enhanced KAG component for additional processing if needed
                kag_generator = create_kag_input_generator()
                kag_validator = create_kag_input_validator()
                
                # Validate the generated KAG input using enhanced validator
                is_valid, validation_errors, validation_warnings = kag_validator.validate_kag_input(
                    kag_input_path=kag_input_result["kag_input_path"],
                    parsed_output_path=kag_input_result["parsed_output_path"],
                    classification_verdict_path=classification_result["classification_verdict_path"]
                )
                
                if validation_errors:
                    error_msg = f"KAG input validation failed: {'; '.join(validation_errors)}"
                    logger.error(error_msg)
                    warnings.append(error_msg)
                else:
                    logger.info("KAG input validation passed successfully")
                
                if validation_warnings:
                    for warning in validation_warnings:
                        logger.warning(f"KAG validation warning: {warning}")
                        warnings.append(f"KAG validation: {warning}")
                
                kag_result = {
                    "success": True,
                    "kag_input_path": kag_input_result["kag_input_path"],
                    "parsed_output_path": kag_input_result["parsed_output_path"],
                    "validation_passed": is_valid,
                    "validation_errors": validation_errors,
                    "validation_warnings": validation_warnings,
                    "processing_summary": {
                        "unified_schema_compliant": True,
                        "enhanced_validation_performed": True,
                        "legacy_kag_component_used": False,  # Using new writer instead
                        "artifacts_generated": ["kag_input.json", "parsed_output.json", "feature_vector.json"]
                    }
                }
                
                logger.info(f"Enhanced KAG validation completed successfully")
                
            else:
                # Use the KAG input result as the main result
                kag_result = kag_input_result
                
        except Exception as e:
            error_msg = f"Enhanced KAG processing failed: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)
            
            # Fall back to the KAG input result
            kag_result = kag_input_result if kag_input_result else {
                "success": False,
                "error_message": error_msg,
                "kag_input_path": None,
                "processing_summary": {}
            }
        
        stage_timings["kag"] = time.time() - stage_start
        update_pipeline_status(pipeline_id, "kag_complete", 95.0)
        
        logger.info(f"Pipeline {pipeline_id}: Enhanced KAG completed in {stage_timings['kag']:.2f}s")
        
        # Stage 7: Save Final Results
        update_pipeline_status(pipeline_id, "saving_results", 95.0)
        stage_start = time.time()
        
        final_results_path = save_final_results(
            pipeline_id=pipeline_id,
            upload_result=upload_result.dict(),
            ocr_result=ocr_result.dict(),
            docai_result=docai_result.dict(),
            classification_result=classification_result,
            kag_result=kag_result,
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