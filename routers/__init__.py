"""
Routers package for AI Backend Document Processing API.

This package contains all API routers organized by functionality.
Each router focuses on a specific domain (processing, admin, etc.).

Usage:
    from routers import processing_handler
    
    app.include_router(processing_handler.router)
"""

from . import processing_handler

__all__ = [
    "processing_handler"
]