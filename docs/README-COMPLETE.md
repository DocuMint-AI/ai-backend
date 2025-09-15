# AI Backend OCR Pipeline - Complete Guide

## Overview

The AI Backend OCR Pipeline is a production-ready system that provides:
- **DocAI Schema Compliance**: Output strictly follows the required DocAI format
- **Google Vision API Integration**: High-accuracy OCR with multi-language support
- **FastAPI REST Endpoints**: Complete web API for document processing
- **Virtual Environment Support**: Isolated Python environment for dependencies
- **Relative Path Architecture**: Portable across different systems

## Features

### ✅ **DocAI Schema Compliance**
- Stable block and line identifiers (`block_001`, `line_001_001`)
- Ordered pages array structure
- Comprehensive bounding box coordinates
- File metadata and fingerprinting
- Language detection and confidence scores
- Extraction warnings and preprocessing details

### ✅ **Google Vision API Integration**
- High-accuracy text extraction
- Multi-language support (EN, ES, FR)
- Document structure analysis
- Confidence scoring

### ✅ **Production-Ready Features**
- FastAPI web framework with automatic API documentation
- Health monitoring endpoints
- Comprehensive error handling and logging
- Virtual environment isolation
- Cross-platform compatibility (Linux, Windows, macOS)

## Quick Start

### 1. Setup Environment

#### Option A: Automated Setup (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd ai-backend

# Run setup script (Linux/macOS)
./setup.sh

# Or for Windows
setup.bat
```

#### Option B: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\\Scripts\\activate.bat

# Install dependencies
pip install -r requirements.txt

# Create data directories
mkdir -p data/.cheetah/gcloud data/uploads data/processed
```

### 2. Configure Google Cloud

1. **Create Google Cloud Project**: Go to [Google Cloud Console](https://console.cloud.google.com/)

2. **Enable Vision API**: Enable the Cloud Vision API for your project

3. **Create Service Account**:
   ```bash
   # In Google Cloud Console, go to IAM & Admin > Service Accounts
   # Create new service account with Vision API permissions
   # Download the JSON credentials file
   ```

4. **Place Credentials**: Save the JSON file as:
   ```
   data/.cheetah/gcloud/vision-credentials.json
   ```

5. **Update Configuration**: Edit `.env` file:
   ```env
   # Google Cloud Configuration
   GOOGLE_CLOUD_PROJECT_ID=your-project-id-here
   GOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.json
   
   # OCR Configuration
   LANGUAGE_HINTS=en,es,fr
   MAX_FILE_SIZE_MB=50
   PDF_DPI=300
   PDF_FORMAT=PNG
   
   # Data Storage Configuration
   DATA_ROOT=./data
   
   # FastAPI Configuration
   API_HOST=0.0.0.0
   API_PORT=8000
   LOG_LEVEL=INFO
   ```

### 3. Test the Installation

```bash
# Activate virtual environment if not already active
source venv/bin/activate  # Linux/macOS
# venv\\Scripts\\activate.bat  # Windows

# Test Google Vision API connection
python test_vision_connection.py

# Start the FastAPI server
python services/processing-handler.py
```

### 4. Verify Health Status

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-09-15T14:16:50.492255",
  "services": {
    "data_directory": {"accessible": true, "path": "./data"},
    "ocr_service": {"available": true, "error": null},
    "pdf_converter": {"available": true, "format": "PNG", "dpi": 300}
  },
  "config": {
    "max_file_size_mb": 50,
    "language_hints": ["en", "es", "fr"]
  }
}
```

## API Usage

### Available Endpoints

#### 1. Health Check
```bash
GET /health
```

#### 2. Upload Document
```bash
curl -X POST "http://localhost:8000/upload" \\
     -H "Content-Type: multipart/form-data" \\
     -F "file=@document.pdf"

# Response:
{
  "uid": "doc_20250915_141650_abc123",
  "filename": "document.pdf",
  "size_mb": 2.5,
  "pages": 3,
  "status": "uploaded"
}
```

#### 3. Process OCR (DocAI Format)
```bash
curl -X POST "http://localhost:8000/ocr-process" \\
     -H "Content-Type: application/json" \\
     -d '{"uid": "doc_20250915_141650_abc123"}'

# Response:
{
  "uid": "doc_20250915_141650_abc123",
  "status": "completed",
  "processing_time_seconds": 12.34,
  "pages_processed": 3,
  "total_text_blocks": 45,
  "docai_format": true
}
```

#### 4. Get Results
```bash
curl -X GET "http://localhost:8000/results/doc_20250915_141650_abc123"

# Returns complete DocAI-compliant JSON structure
```

#### 5. API Documentation
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/redoc

## DocAI Schema Output

The pipeline produces output that strictly follows the DocAI schema:

```json
{
  "document_id": "doc_20250915_141650_abc123",
  "original_filename": "document.pdf",
  "file_fingerprint": "sha256:abc123...",
  "pdf_uri": "file://./data/uploads/document.pdf",
  "derived_images": [
    {
      "page": 1,
      "image_uri": "file://./data/processed/doc_123_page_1.png",
      "width": 2480,
      "height": 3508,
      "dpi": 300
    }
  ],
  "language_detection": {
    "primary": "en",
    "confidence": 0.98,
    "detected_languages": ["en"]
  },
  "ocr_result": {
    "pages": [
      {
        "page": 1,
        "width": 2480,
        "height": 3508,
        "page_confidence": 0.96,
        "text_blocks": [
          {
            "block_id": "block_001",
            "text": "Document Title",
            "confidence": 0.98,
            "bounding_box": [100, 200, 500, 250],
            "lines": [
              {
                "line_id": "line_001_001",
                "text": "Document Title",
                "confidence": 0.98,
                "bounding_box": [100, 200, 500, 250],
                "words": [...]
              }
            ]
          }
        ]
      }
    ]
  },
  "extracted_assets": {
    "tables": [],
    "images": [],
    "signatures": []
  },
  "preprocessing": {
    "pipeline_version": "2.0.0",
    "processing_timestamp": "2025-09-15T14:16:50.492255Z",
    "google_vision_version": "3.10.0",
    "pdf_conversion": {
      "format": "PNG",
      "dpi": 300,
      "pages_converted": 3
    }
  },
  "warnings": []
}
```

## Development

### Project Structure
```
ai-backend/
├── data/                          # Data directory (gitignored)
│   ├── .cheetah/gcloud/          # Google Cloud credentials
│   ├── uploads/                   # Uploaded files
│   └── processed/                 # Processed files
├── services/                      # Core services
│   ├── preprocessing/
│   │   ├── OCR-processing.py     # Google Vision OCR wrapper
│   │   └── parsing.py            # Text parsing utilities
│   ├── processing-handler.py     # FastAPI endpoints
│   ├── project_utils.py          # Path utilities
│   └── util-services.py          # Utility functions
├── tests/                         # Test files
├── docs/                          # Documentation
├── venv/                          # Virtual environment
├── requirements.txt               # Python dependencies
├── setup.sh                      # Linux/macOS setup script
├── setup.bat                     # Windows setup script
└── .env                          # Environment configuration
```

### Running Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python -m pytest tests/

# Run specific test
python test_vision_connection.py

# Run with coverage
python -m pytest tests/ --cov=services
```

### Code Quality
```bash
# Format code
black services/ tests/

# Lint code
flake8 services/ tests/

# Type checking
mypy services/
```

## Troubleshooting

### Common Issues

#### 1. Billing Not Enabled
```
Error: 403 This API method requires billing to be enabled
```
**Solution**: Enable billing in Google Cloud Console for your project.

#### 2. Credentials Not Found
```
Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is required
```
**Solution**: Ensure the credentials file exists and the path in `.env` is correct.

#### 3. Import Errors
```
ImportError: No module named 'google.cloud.vision'
```
**Solution**: Activate the virtual environment and install dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Permission Denied
```
Error: 403 Permission denied
```
**Solution**: Ensure your service account has the "Cloud Vision API User" role.

### Support

For issues and questions:
1. Check the health endpoint: `curl http://localhost:8000/health`
2. Review server logs for detailed error messages
3. Verify Google Cloud project configuration
4. Test with the connection script: `python test_vision_connection.py`

## Performance

### Optimization Tips

1. **Batch Processing**: Process multiple pages concurrently
2. **Image Quality**: Use 300 DPI for best OCR accuracy
3. **Language Hints**: Specify expected languages for better results
4. **Caching**: Results are automatically cached by document fingerprint

### Scaling

For production deployment:
1. Use containerization (Docker)
2. Set up load balancing
3. Implement result caching (Redis)
4. Monitor API quotas and costs
5. Use Google Cloud Run or Kubernetes for auto-scaling

## License

This project is proprietary software for DocuMint-AI.