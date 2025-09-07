# OCR Processing Guide

This document provides comprehensive instructions for using the OCR processing services and FastAPI endpoints in the AI backend system.

## Overview

The OCR processing system provides:
- PDF to image conversion with organized file structure
- Google Cloud Vision API integration for text extraction
- FastAPI REST endpoints for document processing
- Comprehensive metadata tracking and result storage
- Environment-based configuration management

## Quick Start

### Prerequisites

1. **Install Dependencies**:
```bash
# Core dependencies
pip install fastapi uvicorn python-dotenv
pip install google-cloud-vision PyMuPDF Pillow
pip install pydantic pathlib

# Optional: For development
pip install pytest coverage black flake8
```

2. **Google Cloud Setup**:
   - Create a Google Cloud Project
   - Enable the Vision API
   - Create a service account and download credentials JSON
   - Set up billing (Vision API requires it)

3. **Environment Configuration**:
```bash
# Copy example environment file
cp .env.example .env

# Edit with your actual values
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_CREDENTIALS_PATH=/path/to/credentials.json
LANGUAGE_HINTS=en,es
DATA_ROOT=/data
```

### Basic Usage

#### Method 1: Direct OCR Module Usage
```python
from services.preprocessing.OCR_processing import GoogleVisionOCR

# Using environment variables (recommended)
ocr = GoogleVisionOCR.from_env()

# Process single image
result = ocr.extract_text("document.jpg")
print(f"Extracted: {result.text}")
print(f"Confidence: {result.confidence}")

# Process image bytes
with open("document.jpg", "rb") as f:
    image_data = f.read()
result = ocr.extract_from_bytes(image_data)
```

#### Method 2: FastAPI Service
```bash
# Start the service
cd services
python processing-handler.py

# Or using uvicorn directly
uvicorn processing-handler:app --host 0.0.0.0 --port 8000 --reload
```

## FastAPI Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-07T10:30:00",
  "services": {
    "data_directory": {"accessible": true, "path": "/data"},
    "ocr_service": {"available": true, "error": null},
    "pdf_converter": {"available": true, "format": "PNG", "dpi": 300}
  }
}
```

### 2. File Upload
```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

**Response**:
```json
{
  "success": true,
  "message": "File uploaded successfully: document.pdf",
  "file_path": "/data/uploads/document.pdf",
  "file_info": {
    "name": "document.pdf",
    "size_mb": 2.5,
    "created": "2025-09-07T10:30:00",
    "absolute_path": "/data/uploads/document.pdf"
  }
}
```

### 3. OCR Processing
```bash
curl -X POST "http://localhost:8000/ocr-process" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "pdf_path": "/data/uploads/document.pdf",
       "language_hints": ["en", "es"],
       "force_reprocess": false
     }'
```

**Response**:
```json
{
  "success": true,
  "uid": "abc12345-def67890",
  "message": "OCR processing completed: 5/5 pages processed",
  "processing_folder": "/data/document-abc12345-def67890",
  "total_pages": 5,
  "processed_pages": 5,
  "ocr_results_path": "/data/document-abc12345-def67890/document-abc12345-def67890.json",
  "metadata": {
    "uid": "abc12345-def67890",
    "pdf_info": {...},
    "processing_info": {...}
  }
}
```

### 4. Get Results
```bash
curl http://localhost:8000/results/abc12345-def67890
```

### 5. List Processing Folders
```bash
curl http://localhost:8000/folders
```

### 6. Cleanup
```bash
curl -X DELETE http://localhost:8000/cleanup/abc12345-def67890
```

## Complete Processing Workflow

### Step-by-Step Example

1. **Upload PDF**:
```python
import requests

# Upload file
with open("invoice.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/upload", files=files)
    upload_result = response.json()

file_path = upload_result["file_path"]
```

2. **Process with OCR**:
```python
# Start OCR processing
ocr_request = {
    "pdf_path": file_path,
    "language_hints": ["en"],
    "force_reprocess": False
}

response = requests.post("http://localhost:8000/ocr-process", json=ocr_request)
ocr_result = response.json()

uid = ocr_result["uid"]
```

3. **Retrieve Results**:
```python
# Get processed results
response = requests.get(f"http://localhost:8000/results/{uid}")
results = response.json()

# Access OCR data
for page_num, page_data in results["ocr_results"]["pages"].items():
    print(f"Page {page_num}: {page_data['text'][:100]}...")
    print(f"Confidence: {page_data['confidence']:.2f}")
```

### File Structure After Processing

```
/data/
├── uploads/
│   └── document.pdf
└── document-abc12345-def67890/
    ├── images/
    │   ├── page_001.png
    │   ├── page_002.png
    │   └── ...
    ├── ocr_results/
    ├── metadata.json
    └── document-abc12345-def67890.json
```

## Advanced Configuration

### Environment Variables

Create a comprehensive `.env` file:

```bash
# Required: Google Cloud Vision API
GOOGLE_CLOUD_PROJECT_ID=my-project-123
GOOGLE_CLOUD_CREDENTIALS_PATH=/app/credentials/service-account.json

# OCR Configuration
LANGUAGE_HINTS=en,es,fr,de
IMAGE_FORMAT=PNG
IMAGE_DPI=300

# Storage Configuration
DATA_ROOT=/app/data
MAX_FILE_SIZE_MB=100

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Performance Tuning
CONCURRENT_PAGES=3
TIMEOUT_SECONDS=300
```

### Custom OCR Configuration

```python
# Advanced OCR setup
from services.preprocessing.OCR_processing import GoogleVisionOCR

# Custom initialization
ocr = GoogleVisionOCR(
    project_id="my-project",
    credentials_path="/path/to/creds.json",
    language_hints=["en", "es", "fr"]
)

# Process with custom settings
result = ocr.extract_text("document.jpg")

# Access detailed block information
for i, block in enumerate(result.blocks):
    print(f"Block {i}: {block['text']}")
    print(f"Confidence: {block['confidence']:.2f}")
    print(f"Bounding box: {block['bounding_box']}")
```

### Custom PDF Processing

```python
from services.util_services import PDFToImageConverter

# Custom converter settings
converter = PDFToImageConverter(
    data_root="/custom/data/path",
    image_format="JPEG",
    dpi=200
)

# Process PDF
uid, image_paths, metadata = converter.convert_pdf_to_images("document.pdf")

print(f"Generated UID: {uid}")
print(f"Created {len(image_paths)} images")
```

## Production Deployment

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libfontconfig1 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "services.processing-handler:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  ai-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_CLOUD_PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID}
      - GOOGLE_CLOUD_CREDENTIALS_PATH=/app/credentials/service-account.json
      - DATA_ROOT=/data
      - LANGUAGE_HINTS=en,es
    volumes:
      - ./data:/data
      - ./credentials:/app/credentials:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-backend-ocr
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-backend-ocr
  template:
    metadata:
      labels:
        app: ai-backend-ocr
    spec:
      containers:
      - name: ai-backend
        image: ai-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_CLOUD_PROJECT_ID
          valueFrom:
            secretKeyRef:
              name: gcp-credentials
              key: project-id
        volumeMounts:
        - name: gcp-credentials
          mountPath: /app/credentials
          readOnly: true
        - name: data-storage
          mountPath: /data
      volumes:
      - name: gcp-credentials
        secret:
          secretName: gcp-credentials
      - name: data-storage
        persistentVolumeClaim:
          claimName: ai-backend-storage
```

## Performance Optimization

### 1. Concurrent Processing

```python
# Process multiple pages concurrently
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_multiple_images(image_paths: list) -> list:
    """Process multiple images concurrently."""
    
    def process_single_image(image_path: str):
        ocr = GoogleVisionOCR.from_env()
        return ocr.extract_text(image_path)
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=3) as executor:
        tasks = [
            loop.run_in_executor(executor, process_single_image, path)
            for path in image_paths
        ]
        results = await asyncio.gather(*tasks)
    
    return results

# Usage
results = asyncio.run(process_multiple_images(image_paths))
```

### 2. Caching Strategy

```python
import redis
import json
import hashlib

class CachedOCRService:
    """OCR service with Redis caching."""
    
    def __init__(self):
        self.ocr = GoogleVisionOCR.from_env()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.cache_ttl = 3600 * 24  # 24 hours
    
    def _get_cache_key(self, image_path: str) -> str:
        """Generate cache key for image."""
        with open(image_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return f"ocr_result:{file_hash}"
    
    def extract_text_cached(self, image_path: str):
        """Extract text with caching."""
        cache_key = self._get_cache_key(image_path)
        
        # Try cache first
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        # Process with OCR
        result = self.ocr.extract_text(image_path)
        
        # Cache result
        result_dict = {
            "text": result.text,
            "confidence": result.confidence,
            "blocks": result.blocks
        }
        self.redis_client.setex(
            cache_key, 
            self.cache_ttl, 
            json.dumps(result_dict)
        )
        
        return result
```

### 3. Batch Processing

```python
def batch_process_pdfs(pdf_paths: list, batch_size: int = 5) -> dict:
    """Process multiple PDFs in batches."""
    results = {}
    
    for i in range(0, len(pdf_paths), batch_size):
        batch = pdf_paths[i:i + batch_size]
        
        # Process batch
        batch_results = {}
        for pdf_path in batch:
            try:
                # Convert PDF to images
                converter = PDFToImageConverter()
                uid, images, metadata = converter.convert_pdf_to_images(pdf_path)
                
                # Process with OCR
                ocr = GoogleVisionOCR.from_env()
                page_results = {}
                
                for page_num, image_path in enumerate(images, 1):
                    ocr_result = ocr.extract_text(image_path)
                    page_results[page_num] = {
                        "text": ocr_result.text,
                        "confidence": ocr_result.confidence
                    }
                
                batch_results[pdf_path] = {
                    "uid": uid,
                    "pages": page_results,
                    "metadata": metadata
                }
                
            except Exception as e:
                batch_results[pdf_path] = {"error": str(e)}
        
        results.update(batch_results)
        
        # Optional: Add delay between batches to avoid rate limits
        time.sleep(1)
    
    return results
```

## Error Handling and Troubleshooting

### Common Issues

#### 1. Google Cloud Authentication
```python
# Debug authentication issues
import os
from google.auth import default

def check_gcp_auth():
    """Check Google Cloud authentication."""
    try:
        credentials, project = default()
        print(f"✓ Authentication successful")
        print(f"  Project: {project}")
        print(f"  Credentials type: {type(credentials)}")
        return True
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False

# Check environment
def check_environment():
    """Check environment configuration."""
    required_vars = [
        "GOOGLE_CLOUD_PROJECT_ID",
        "GOOGLE_CLOUD_CREDENTIALS_PATH"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: Not set")
```

#### 2. File Processing Issues
```python
def diagnose_file_issues(file_path: str):
    """Diagnose common file processing issues."""
    
    # Check file existence
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return
    
    # Check file size
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")
    
    # Check file type
    if file_path.lower().endswith('.pdf'):
        try:
            import fitz
            doc = fitz.open(file_path)
            print(f"✓ Valid PDF with {len(doc)} pages")
            doc.close()
        except Exception as e:
            print(f"✗ PDF validation failed: {e}")
    
    # Check permissions
    if os.access(file_path, os.R_OK):
        print("✓ File is readable")
    else:
        print("✗ File is not readable")
```

#### 3. API Error Handling
```python
from google.api_core import exceptions as gcp_exceptions

def robust_ocr_processing(image_path: str, max_retries: int = 3):
    """OCR processing with robust error handling."""
    
    for attempt in range(max_retries):
        try:
            ocr = GoogleVisionOCR.from_env()
            result = ocr.extract_text(image_path)
            return result
            
        except gcp_exceptions.ResourceExhausted:
            print(f"Rate limit exceeded. Waiting before retry {attempt + 1}")
            time.sleep(2 ** attempt)  # Exponential backoff
            
        except gcp_exceptions.ServiceUnavailable:
            print(f"Service unavailable. Retry {attempt + 1}")
            time.sleep(5)
            
        except gcp_exceptions.DeadlineExceeded:
            print(f"Request timeout. Retry {attempt + 1}")
            time.sleep(1)
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            if attempt == max_retries - 1:
                raise
    
    raise Exception("Max retries exceeded")
```

## Monitoring and Logging

### Structured Logging

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """Structured logging for OCR operations."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
        # Configure structured logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_ocr_start(self, file_path: str, uid: str):
        """Log OCR processing start."""
        self.logger.info(json.dumps({
            "event": "ocr_start",
            "file_path": file_path,
            "uid": uid,
            "timestamp": datetime.now().isoformat()
        }))
    
    def log_ocr_complete(self, uid: str, pages: int, duration: float):
        """Log OCR completion."""
        self.logger.info(json.dumps({
            "event": "ocr_complete",
            "uid": uid,
            "pages_processed": pages,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }))
    
    def log_error(self, uid: str, error: str, context: dict = None):
        """Log errors with context."""
        self.logger.error(json.dumps({
            "event": "error",
            "uid": uid,
            "error": error,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }))
```

### Performance Metrics

```python
import time
from functools import wraps

def measure_performance(func):
    """Decorator to measure function performance."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        print(f"{func.__name__} completed in {duration:.2f} seconds")
        return result
    
    return wrapper

# Usage
@measure_performance
def process_with_timing(pdf_path: str):
    """Process PDF with timing measurement."""
    # Your processing code here
    pass
```

## Testing

### Unit Tests
```bash
# Run OCR-specific tests
cd tests
python test_ocr_processing.py

# Run with coverage
coverage run test_ocr_processing.py
coverage report -m
```

### Integration Tests
```bash
# Test with real API (requires credentials)
python -m pytest tests/ -k "integration" --env-file=.env
```

### Load Testing
```python
import asyncio
import aiohttp
import time

async def load_test_api(concurrent_requests: int = 10):
    """Load test the OCR API."""
    
    async def single_request(session, request_id):
        start_time = time.time()
        async with session.post(
            "http://localhost:8000/ocr-process",
            json={"pdf_path": "/data/test.pdf"}
        ) as response:
            result = await response.json()
            duration = time.time() - start_time
            return {"request_id": request_id, "duration": duration, "success": response.status == 200}
    
    async with aiohttp.ClientSession() as session:
        tasks = [single_request(session, i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
    
    # Analyze results
    durations = [r["duration"] for r in results]
    success_rate = sum(1 for r in results if r["success"]) / len(results)
    
    print(f"Load test results:")
    print(f"  Requests: {concurrent_requests}")
    print(f"  Success rate: {success_rate:.2%}")
    print(f"  Average duration: {sum(durations) / len(durations):.2f}s")
    print(f"  Max duration: {max(durations):.2f}s")

# Run load test
asyncio.run(load_test_api(10))
```

## API Documentation

The FastAPI service automatically generates interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Best Practices

1. **Security**: Store credentials securely, use environment variables
2. **Error Handling**: Implement comprehensive error handling and logging
3. **Rate Limiting**: Respect Google Cloud Vision API rate limits
4. **Caching**: Cache results to avoid redundant processing
5. **Monitoring**: Monitor API usage and costs
6. **Validation**: Validate inputs before processing
7. **Cleanup**: Implement proper cleanup of temporary files
8. **Backup**: Backup processed results and metadata

For additional information, see:
- [Parsing Execution Guide](parsing-execution.md)
- [Test Documentation](../tests/README.md)
- [Google Cloud Vision API Documentation](https://cloud.google.com/vision/docs)