# Router Migration Documentation

## Overview

The FastAPI application has been successfully migrated from a monolithic structure to a modular router-based architecture. This enables better code organization, easier maintenance, and scalability for future endpoint additions.

## Project Structure

```
ai-backend/
├── main.py                     # Main FastAPI application entry point
├── routers/                    # Router modules organized by functionality
│   ├── __init__.py            # Router package initialization
│   └── processing_handler.py  # Document processing endpoints
└── services/                   # Legacy services (preserved)
    └── processing-handler.py   # Original monolithic file (legacy)
```

## New Architecture

### main.py
- Initializes the FastAPI application
- Configures middleware (CORS, etc.)
- Registers all routers
- Handles application lifecycle events
- Provides the root endpoint

### routers/processing_handler.py
- Contains all document processing endpoints
- Uses FastAPI APIRouter for modular organization
- Maintains all original functionality:
  - Health check (`/health`)
  - File upload (`/upload`)
  - OCR processing (`/ocr-process`)
  - Result retrieval (`/results/{uid}`)
  - Folder listing (`/folders`)
  - Cleanup operations (`/cleanup/{uid}`)
  - Admin operations (`/admin/purge`, `/admin/data-usage`)

### routers/__init__.py
- Central import point for all routers
- Simplifies router registration in main.py
- Prepared for future router additions

## Key Changes

1. **Modular Structure**: Endpoints are now organized in separate router modules
2. **Scalable Architecture**: Easy to add new routers for different functionalities
3. **Improved Imports**: Better organization of service imports and dependencies
4. **Lifecycle Management**: Proper startup/shutdown handling in main.py
5. **CORS Configuration**: Added CORS middleware for API accessibility

## Migration Benefits

1. **Maintainability**: Easier to maintain and update specific endpoint groups
2. **Scalability**: Simple to add new routers for different features
3. **Testing**: Individual routers can be tested in isolation
4. **Documentation**: Better API documentation organization by tags
5. **Team Development**: Multiple developers can work on different routers simultaneously

## Running the Application

### Development Mode
```bash
# Using the main.py directly
python main.py

# Using uvicorn with reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Available Endpoints

All original endpoints are preserved and functional:

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `POST /upload` - Upload PDF files
- `POST /ocr-process` - Process PDFs with OCR
- `GET /results/{uid}` - Get processing results
- `GET /folders` - List processing folders
- `DELETE /cleanup/{uid}` - Clean up processing folders
- `POST /admin/purge` - Execute data purge operations
- `GET /admin/data-usage` - Get data usage statistics

## Future Router Additions

To add new routers (e.g., authentication, analytics, etc.):

1. Create a new router file in `routers/` directory
2. Import and expose it in `routers/__init__.py`
3. Register it in `main.py` using `app.include_router()`

Example:
```python
# routers/analytics.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/analytics/stats")
async def get_stats():
    return {"stats": "data"}

# routers/__init__.py
from . import processing_handler, analytics

# main.py
from routers import processing_handler, analytics

app.include_router(processing_handler.router, tags=["Document Processing"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
```

## Testing

Run the migration test script to verify everything is working:

```bash
python test_migration.py
```

This will validate:
- Import functionality
- Endpoint registration
- Router structure
- Configuration loading

## Legacy Code

The original `services/processing-handler.py` file has been preserved for reference but is no longer used. It can be removed once the migration is fully validated in production.

## Environment Variables

All environment variables remain the same:
- `GOOGLE_CLOUD_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `DATA_ROOT`
- `IMAGE_FORMAT`
- `IMAGE_DPI`
- `LANGUAGE_HINTS`
- `MAX_FILE_SIZE_MB`