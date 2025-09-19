"""
DocAI router for Google Document AI integration.

This router provides endpoints for document parsing using Google Document AI,
following the existing API naming conventions and patterns.
"""

import asyncio
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional
import structlog

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import our DocAI services
from services.doc_ai import (
    DocAIClient,
    DocumentParser,
    ParseRequest,
    ParseResponse,
    ParsedDocument,
    DocumentMetadata
)
from services.doc_ai.client import DocAIError, DocAIAuthenticationError, DocAIProcessingError
from services.gcs_staging import auto_stage_document, is_gcs_uri

# Load environment variables
load_dotenv()

# Configure logging
logger = structlog.get_logger(__name__)

# Create router
router = APIRouter()

# Global configuration from environment variables
CONFIG = {
    "google_project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
    "google_credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    "docai_location": os.getenv("DOCAI_LOCATION", "us"),
    "docai_processor_id": os.getenv("DOCAI_PROCESSOR_ID"),
    "docai_structured_processor_id": os.getenv("DOCAI_STRUCTURED_PROCESSOR_ID"),
    "default_confidence_threshold": float(os.getenv("DOCAI_CONFIDENCE_THRESHOLD", "0.7"))
}

# Processor selection logic - prefer structured processor if available
def get_active_processor_id() -> str:
    """Get the active processor ID, preferring structured processor when available."""
    structured_id = CONFIG["docai_structured_processor_id"]
    fallback_id = CONFIG["docai_processor_id"]
    
    if structured_id and structured_id.strip():
        logger.info(f"Using structured DocAI processor: {structured_id}")
        return structured_id
    else:
        logger.info(f"Using fallback DocAI processor: {fallback_id}")
        return fallback_id

# Initialize services (will be created when needed)
docai_client = None
document_parser = None


def get_docai_client() -> DocAIClient:
    """
    Get or initialize DocAI client with error handling.
    
    Returns:
        DocAIClient instance
        
    Raises:
        HTTPException: If DocAI client cannot be initialized
    """
    global docai_client
    
    if docai_client is None:
        try:
            if not CONFIG["google_project_id"]:
                raise ValueError("GOOGLE_CLOUD_PROJECT_ID environment variable is required")
            
            docai_client = DocAIClient(
                project_id=CONFIG["google_project_id"],
                location=CONFIG["docai_location"],
                processor_id=get_active_processor_id(),
                credentials_path=CONFIG["google_credentials_path"]
            )
            
            logger.info("DocAI client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize DocAI client", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"DocAI client initialization failed: {str(e)}"
            )
    
    return docai_client


def get_document_parser(confidence_threshold: float = None) -> DocumentParser:
    """
    Get or initialize document parser.
    
    Args:
        confidence_threshold: Optional confidence threshold override
        
    Returns:
        DocumentParser instance
    """
    global document_parser
    
    threshold = confidence_threshold or CONFIG["default_confidence_threshold"]
    
    if document_parser is None or document_parser.confidence_threshold != threshold:
        document_parser = DocumentParser(confidence_threshold=threshold)
        logger.info("Document parser initialized", confidence_threshold=threshold)
    
    return document_parser


@router.get("/health")
async def health_check():
    """Health check endpoint for DocAI service."""
    try:
        # Check if required environment variables are set
        env_status = {
            "google_project_id": bool(CONFIG["google_project_id"]),
            "docai_location": bool(CONFIG["docai_location"]),
            "google_credentials": bool(CONFIG["google_credentials_path"])
        }
        
        # Test DocAI client initialization (if credentials are available)
        docai_available = False
        docai_error = None
        
        if all(env_status.values()):
            try:
                client = get_docai_client()
                docai_available = True
            except Exception as e:
                docai_error = str(e)
        
        return {
            "status": "healthy" if docai_available else "degraded",
            "timestamp": time.time(),
            "services": {
                "docai_client": {
                    "available": docai_available,
                    "error": docai_error
                },
                "document_parser": {
                    "available": True,
                    "confidence_threshold": CONFIG["default_confidence_threshold"]
                }
            },
            "environment": env_status,
            "config": {
                "project_id": CONFIG["google_project_id"],
                "location": CONFIG["docai_location"],
                "processor_id": get_active_processor_id(),
                "confidence_threshold": CONFIG["default_confidence_threshold"]
            }
        }
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/api/docai/parse", response_model=ParseResponse)
async def parse_document(
    request: ParseRequest,
    background_tasks: BackgroundTasks
):
    """
    Parse document using Google Document AI.
    
    Processes a document from Google Cloud Storage using Document AI,
    extracting text, entities, clauses, and relationships in a normalized format.
    
    Args:
        request: Document parsing request with GCS URI and options
        background_tasks: FastAPI background tasks
        
    Returns:
        ParseResponse with parsed document data
        
    Example:
        POST /api/docai/parse
        {
            "gcs_uri": "gs://my-bucket/documents/contract.pdf",
            "confidence_threshold": 0.8,
            "include_raw_response": false,
            "metadata": {"customer_id": "12345"}
        }
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(
            "Starting document parsing",
            request_id=request_id,
            gcs_uri=request.gcs_uri,
            confidence_threshold=request.confidence_threshold
        )
        
        # Auto-stage document if it's a local path
        processed_gcs_uri = request.gcs_uri
        if not is_gcs_uri(request.gcs_uri):
            logger.info("Input appears to be local path, staging to GCS", input_path=request.gcs_uri)
            try:
                processed_gcs_uri = auto_stage_document(request.gcs_uri)
                logger.info("Successfully staged document", original_path=request.gcs_uri, gcs_uri=processed_gcs_uri)
            except Exception as staging_error:
                logger.error("Failed to stage document to GCS", error=str(staging_error))
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to stage document to GCS: {str(staging_error)}"
                )
        
        # Get services
        client = get_docai_client()
        parser = get_document_parser(request.confidence_threshold)
        
        # Process document with DocAI using the (potentially staged) GCS URI
        docai_document, metadata = await client.process_gcs_document_async(
            gcs_uri=processed_gcs_uri,
            processor_id=request.processor_id,
            enable_native_pdf_parsing=request.enable_native_pdf_parsing
        )
        
        # Update metadata with custom data
        if request.metadata:
            metadata.custom_metadata.update(request.metadata)
        
        # Parse document into normalized schema
        parsed_document = parser.parse_document(
            docai_document=docai_document,
            metadata=metadata,
            include_raw_response=request.include_raw_response
        )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "Document parsing completed successfully",
            request_id=request_id,
            document_id=parsed_document.metadata.document_id,
            processing_time=processing_time,
            entities=len(parsed_document.named_entities),
            clauses=len(parsed_document.clauses),
            key_value_pairs=len(parsed_document.key_value_pairs)
        )
        
        return ParseResponse(
            success=True,
            document=parsed_document,
            processing_time_seconds=processing_time,
            request_id=request_id
        )
    
    except DocAIAuthenticationError as e:
        processing_time = time.time() - start_time
        logger.error(
            "DocAI authentication error",
            request_id=request_id,
            error=str(e),
            processing_time=processing_time
        )
        
        return ParseResponse(
            success=False,
            error_message=f"Authentication failed: {str(e)}",
            processing_time_seconds=processing_time,
            request_id=request_id
        )
    
    except DocAIProcessingError as e:
        processing_time = time.time() - start_time
        logger.error(
            "DocAI processing error",
            request_id=request_id,
            error=str(e),
            processing_time=processing_time
        )
        
        return ParseResponse(
            success=False,
            error_message=f"Document processing failed: {str(e)}",
            processing_time_seconds=processing_time,
            request_id=request_id
        )
    
    except DocAIError as e:
        processing_time = time.time() - start_time
        logger.error(
            "DocAI error",
            request_id=request_id,
            error=str(e),
            processing_time=processing_time
        )
        
        return ParseResponse(
            success=False,
            error_message=f"DocAI error: {str(e)}",
            processing_time_seconds=processing_time,
            request_id=request_id
        )
    
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "Unexpected error during document parsing",
            request_id=request_id,
            error=str(e),
            processing_time=processing_time
        )
        
        return ParseResponse(
            success=False,
            error_message=f"Unexpected error: {str(e)}",
            processing_time_seconds=processing_time,
            request_id=request_id
        )


@router.get("/api/docai/processors")
async def list_processors():
    """
    List available DocAI processors.
    
    Returns information about available Document AI processors
    in the configured project and location.
    
    Returns:
        List of available processors with metadata
    """
    try:
        logger.info("Listing DocAI processors")
        
        client = get_docai_client()
        
        # List processors (simplified - real implementation would call DocAI API)
        processors = [
            {
                "id": get_active_processor_id(),
                "name": f"projects/{CONFIG['google_project_id']}/locations/{CONFIG['docai_location']}/processors/{get_active_processor_id()}",
                "type": "FORM_PARSER_PROCESSOR",
                "state": "ENABLED",
                "display_name": "Default Form Parser"
            }
        ] if get_active_processor_id() else []
        
        return {
            "processors": processors,
            "project_id": CONFIG["google_project_id"],
            "location": CONFIG["docai_location"],
            "total": len(processors)
        }
    
    except Exception as e:
        logger.error("Failed to list processors", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list processors: {str(e)}"
        )


@router.get("/api/docai/config")
async def get_configuration():
    """
    Get current DocAI configuration.
    
    Returns the current configuration settings for the DocAI service,
    including project settings, processor information, and defaults.
    
    Returns:
        Current configuration settings
    """
    try:
        return {
            "project_id": CONFIG["google_project_id"],
            "location": CONFIG["docai_location"],
            "default_processor_id": get_active_processor_id(),
            "default_confidence_threshold": CONFIG["default_confidence_threshold"],
            "credentials_configured": bool(CONFIG["google_credentials_path"]),
            "service_status": {
                "client_initialized": docai_client is not None,
                "parser_initialized": document_parser is not None
            }
        }
    
    except Exception as e:
        logger.error("Failed to get configuration", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get configuration: {str(e)}"
        )


@router.post("/api/docai/parse/batch")
async def parse_documents_batch(
    request: dict,
    background_tasks: BackgroundTasks = None
):
    """
    Parse multiple documents in batch with improved concurrency and error handling.
    
    Processes multiple documents from Google Cloud Storage with proper ordering,
    retry logic, and progress tracking.
    
    Args:
        request: Batch request with gcs_uris, max_concurrent, and options
        background_tasks: FastAPI background tasks
        
    Returns:
        Batch processing results with detailed status for each document
        
    Example:
        POST /api/docai/parse/batch
        {
            "gcs_uris": ["gs://bucket/doc1.pdf", "gs://bucket/doc2.pdf"],
            "max_concurrent": 3,
            "confidence_threshold": 0.8,
            "retry_attempts": 2
        }
    """
    batch_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Extract parameters with defaults
        gcs_uris = request.get("gcs_uris", [])
        max_concurrent = min(request.get("max_concurrent", 3), 5)  # Cap at 5
        confidence_threshold = request.get("confidence_threshold", 0.7)
        retry_attempts = min(request.get("retry_attempts", 2), 3)  # Cap at 3
        processor_id = request.get("processor_id")
        
        logger.info(
            "Starting batch document parsing",
            batch_id=batch_id,
            document_count=len(gcs_uris),
            max_concurrent=max_concurrent
        )
        
        if len(gcs_uris) > 20:  # Increased limit but still reasonable
            raise HTTPException(
                status_code=400,
                detail="Batch size limited to 20 documents"
            )
        
        if not gcs_uris:
            raise HTTPException(
                status_code=400,
                detail="No GCS URIs provided"
            )
        
        # Get services
        client = get_docai_client()
        parser = get_document_parser(confidence_threshold)
        
        # Process documents with controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def process_single_document(index: int, gcs_uri: str):
            """Process a single document with retry logic."""
            async with semaphore:
                for attempt in range(retry_attempts + 1):
                    try:
                        request_obj = ParseRequest(
                            gcs_uri=gcs_uri,
                            confidence_threshold=confidence_threshold,
                            processor_id=processor_id
                        )
                        
                        result = await parse_document(request_obj, background_tasks)
                        
                        return {
                            "index": index,
                            "gcs_uri": gcs_uri,
                            "success": result.success,
                            "document": result.document,
                            "error_message": result.error_message,
                            "processing_time_seconds": result.processing_time_seconds,
                            "attempts": attempt + 1
                        }
                        
                    except Exception as e:
                        if attempt == retry_attempts:
                            logger.error(
                                "Document processing failed after retries",
                                batch_id=batch_id,
                                gcs_uri=gcs_uri,
                                attempts=attempt + 1,
                                error=str(e)
                            )
                            
                            return {
                                "index": index,
                                "gcs_uri": gcs_uri,
                                "success": False,
                                "document": None,
                                "error_message": f"Failed after {attempt + 1} attempts: {str(e)}",
                                "processing_time_seconds": 0.0,
                                "attempts": attempt + 1
                            }
                        else:
                            logger.warning(
                                "Document processing attempt failed, retrying",
                                batch_id=batch_id,
                                gcs_uri=gcs_uri,
                                attempt=attempt + 1,
                                error=str(e)
                            )
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Process all documents concurrently while maintaining order
        tasks = [
            process_single_document(i, uri) 
            for i, uri in enumerate(gcs_uris)
        ]
        
        unordered_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sort results by original index to maintain order
        ordered_results = []
        for result in unordered_results:
            if isinstance(result, Exception):
                ordered_results.append({
                    "index": len(ordered_results),
                    "gcs_uri": "unknown",
                    "success": False,
                    "error_message": f"Unexpected error: {str(result)}",
                    "processing_time_seconds": 0.0,
                    "attempts": 1
                })
            else:
                ordered_results.append(result)
        
        # Sort by index to ensure order matches input
        ordered_results.sort(key=lambda x: x.get("index", 0))
        
        total_processing_time = time.time() - start_time
        successful_count = sum(1 for r in ordered_results if r.get("success", False))
        
        logger.info(
            "Batch document parsing completed",
            batch_id=batch_id,
            total_documents=len(gcs_uris),
            successful_documents=successful_count,
            total_processing_time=total_processing_time
        )
        
        return {
            "batch_id": batch_id,
            "total_documents": len(gcs_uris),
            "successful_documents": successful_count,
            "failed_documents": len(gcs_uris) - successful_count,
            "total_processing_time_seconds": total_processing_time,
            "average_processing_time_seconds": total_processing_time / len(gcs_uris),
            "max_concurrent": max_concurrent,
            "retry_attempts": retry_attempts,
            "results": ordered_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch processing failed", batch_id=batch_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )