"""
Routers package for AI Backend Document Processing API.

This package contains all API routers organized by functionality.
Each router focuses on a specific domain (processing, admin, etc.).

Usage:
    from routers.processing_handler import router as processing_router
    from routers.doc_ai_router import router as docai_router
    
    app.include_router(processing_router)
    app.include_router(docai_router)
"""

# Remove direct imports to avoid circular dependencies
# Import routers individually in main.py instead

__all__ = [
    "processing_handler",
    "doc_ai_router"
]