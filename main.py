"""
Main FastAPI application entry point.

This module initializes the FastAPI application and registers all routers
for the AI Backend Document Processing API.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import routers directly to avoid circular imports
from routers.processing_handler import router as processing_router
from routers.doc_ai_router import router as docai_router
from routers.orchestration_router import router as orchestration_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting AI Backend Document Processing API")
    
    # Validate configuration
    required_env_vars = ["GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.warning("OCR functionality may not work properly")
    
    # Log configuration
    config = {
        "data_root": os.getenv("DATA_ROOT", "/data"),
        "image_format": os.getenv("IMAGE_FORMAT", "PNG"),
        "image_dpi": int(os.getenv("IMAGE_DPI", "300")),
        "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    }
    
    logger.info(f"Data root: {config['data_root']}")
    logger.info(f"Image format: {config['image_format']} @ {config['image_dpi']}DPI")
    logger.info(f"Max file size: {config['max_file_size_mb']}MB")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Backend Document Processing API")


# Initialize FastAPI app
app = FastAPI(
    title="AI Backend Document Processing API",
    description="FastAPI service for PDF processing, OCR, and text parsing with modular router architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(
    processing_router,
    tags=["Document Processing"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    docai_router,
    tags=["Document AI"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    orchestration_router,
    tags=["Pipeline Orchestration"],
    responses={404: {"description": "Not found"}},
)

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Backend Document Processing API",
        "version": "1.0.0",
        "description": "FastAPI service with modular router architecture",
        "endpoints": {
            "health": "/health",
            "upload": "/upload", 
            "ocr_process": "/ocr-process",
            "get_results": "/results/{uid}",
            "list_folders": "/folders",
            "cleanup": "/cleanup/{uid}",
            "admin_purge": "/admin/purge",
            "admin_data_usage": "/admin/data-usage",
            "docai_parse": "/api/docai/parse",
            "docai_batch": "/api/docai/parse/batch",
            "docai_config": "/api/docai/config",
            "docai_processors": "/api/docai/processors",
            "docai_health": "/health",
            "pipeline_process": "/api/v1/process-document",
            "pipeline_status": "/api/v1/pipeline-status/{pipeline_id}",
            "pipeline_results": "/api/v1/pipeline-results/{pipeline_id}",
            "orchestration_health": "/api/v1/health"
        },
        "routers": [
            "processing_handler",
            "doc_ai_router",
            "orchestration_router"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )