# AI Backend Document Processing API - MVP Prototype

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![Google Cloud Vision](https://img.shields.io/badge/Google%20Cloud-Vision%20API-red)](https://cloud.google.com/vision)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A high-performance FastAPI service for PDF document processing, OCR (Optical Character Recognition), and text parsing using Google Cloud Vision API. **Prototype uses regex-based classification, no multi-document handling, Vertex embedding disabled, KAG handoff active.**

## 🎯 MVP Prototype Features

**This is a prototype version with the following characteristics:**
- ✅ **Single-document mode only** - No multi-document handling
- ✅ **Regex-based classification** - Template matching using legal keywords (no Vertex Matching Engine)
- ✅ **Vertex embedding disabled** - Embeddings set to null/placeholder values
- ✅ **KAG handoff active** - Unified KAG Writer component with automatic schema-compliant generation
- ✅ **Deterministic results** - Consistent outputs for the same test document
- ✅ **Complete artifact generation** - parsed_output.json, classification_verdict.json, kag_input.json

## 🚀 Features

- **📄 PDF Processing**: Convert PDF documents to high-quality images
- **🔍 OCR Integration**: Google Cloud Vision API for accurate text extraction  
- **🤖 Document AI**: Integration with Google Document AI for structured parsing
- **🔄 Pipeline Orchestration**: Unified workflow combining PDF → Images → OCR → DocAI → Classification → KAG
- **🏷️ Regex Classification**: Pattern-based document classification using legal keywords
- **🧠 KAG Integration**: Automatic `kag_input.json` generation with unified schema
- **📋 Schema Compliance**: Structured output pairing DocAI results with classifier verdicts
- **🌐 Multi-language Support**: Configurable language hints for better OCR accuracy
- **📁 File Management**: Upload, process, and manage document processing workflows
- **⚙️ Admin Tools**: Data purge operations and usage analytics
- **🏗️ Modular Architecture**: Router-based design for easy feature expansion
- **⚡ Background Processing**: Async processing for large documents
- **📊 Health Monitoring**: Comprehensive health checks and status endpoints
- **💾 DocAI Compatible**: Output format compatible with Google Document AI
- **🔧 KAG Writer**: Unified component for automatic knowledge input generation

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Vision API enabled
- Google Cloud Service Account with Vision API permissions

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/DocuMint-AI/ai-backend.git
cd ai-backend
```

### 2. Set Up Environment (Using uv - Recommended)

**Option A: Using uv (Recommended)**
```bash
# Run setup script (installs uv if needed and sets up environment)
./setup.sh          # Linux/Mac
# or
setup.bat           # Windows

# Or manually:
uv venv              # Create virtual environment  
uv pip install -r requirements.txt  # Install dependencies
```

**Option B: Using traditional Python venv**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json

# Application Configuration
DATA_ROOT=./data
IMAGE_FORMAT=PNG
IMAGE_DPI=300
LANGUAGE_HINTS=en,es,fr
MAX_FILE_SIZE_MB=50
```

### 5. Set Up Google Cloud Credentials
```bash
# Download your service account key file from Google Cloud Console
# Place it in a secure location and update GOOGLE_APPLICATION_CREDENTIALS
```

## 🚀 Quick Start

### Development Mode
```bash
# Start the development server
uv run main.py

# Or using uvicorn with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access the API
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📚 API Endpoints

### Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information and available endpoints |
| `GET` | `/health` | Health check and service status |
| `POST` | `/upload` | Upload PDF files for processing |
| `POST` | `/ocr-process` | Process uploaded PDFs with OCR |
| `GET` | `/results/{uid}` | Retrieve processing results |
| `GET` | `/folders` | List all processing folders |
| `DELETE` | `/cleanup/{uid}` | Clean up processing folders |

### Admin Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/purge` | Execute data cleanup operations |
| `GET` | `/admin/data-usage` | Get storage usage statistics |

### Document AI Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/docai/parse` | Parse document with Google Document AI |
| `POST` | `/api/docai/parse/batch` | Batch process multiple documents |
| `GET` | `/api/docai/processors` | List available DocAI processors |
| `GET` | `/api/docai/config` | Get DocAI configuration |

### 🔄 Pipeline Orchestration (NEW)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/process-document` | **Complete pipeline**: PDF → Images → OCR → DocAI |
| `GET` | `/api/v1/pipeline-status/{pipeline_id}` | Get real-time processing status |
| `GET` | `/api/v1/pipeline-results/{pipeline_id}` | Retrieve complete pipeline results |
| `GET` | `/api/v1/health` | Orchestration service health check |

## 🔧 Usage Examples

### 🔄 Complete Document Pipeline (MVP Prototype)

The orchestration API provides a single endpoint for the complete workflow with integrated classification and KAG handoff:

```bash
# Process a document through the complete MVP pipeline
curl -X POST "http://localhost:8000/api/v1/process-document" \
  -F "file=@contract.pdf" \
  -F "language_hints=en,hi" \
  -F "confidence_threshold=0.8"

# Response includes pipeline_id and processing artifacts
{
  "success": true,
  "pipeline_id": "abc123-def456",
  "message": "Document processing completed successfully in 45.2s",
  "total_processing_time": 45.2,
  "final_results_path": "data/processed/pipeline_result_abc123-def456.json",
  "stage_timings": {
    "upload": 2.1,
    "ocr": 15.4,
    "docai": 20.3,
    "classification": 1.2,
    "kag": 3.8,
    "saving": 2.4
  }
}
```

**MVP Pipeline Flow:**
1. 📄 **Upload PDF** - Secure file upload and validation
2. 🖼️ **PDF → Images** - Multi-library fallback conversion
3. 👁️ **Vision OCR** - Google Cloud Vision text extraction
4. 🧠 **Document AI** - Structured document parsing
5. 🏷️ **Regex Classification** - Pattern-based document categorization
6. 🤖 **KAG Processing** - Knowledge Augmented Generation preparation
7. 💾 **Artifact Generation** - Save classification_verdict.json, kag_input.json, feature_vector.json

**Generated Artifacts:**
- `classification_verdict.json` - Document classification results with matched patterns
- `kag_input.json` - Structured handoff payload for downstream processing
- `feature_vector.json` - ML-ready features with classifier verdict (embeddings disabled)

### Individual Step Processing

### 1. Upload a PDF File
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@document.pdf"
```

### 2. Process with OCR
```bash
curl -X POST "http://localhost:8000/ocr-process" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/data/uploads/document.pdf",
    "language_hints": ["en", "es"],
    "force_reprocess": false
  }'
```

### 3. Get Processing Results
```bash
curl -X GET "http://localhost:8000/results/{uid}"
```

### 4. Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

> 📖 **For complete orchestration API documentation with examples, status monitoring, and result formats, see [ORCHESTRATION_API.md](docs/ORCHESTRATION_API.md)**

## 🏗 Project Structure

```
ai-backend/
├── main.py                     # FastAPI application entry point
├── routers/                    # Modular router architecture
│   ├── __init__.py            # Router package initialization
│   ├── processing_handler.py  # Document processing endpoints
│   ├── doc_ai_router.py       # Document AI integration
│   └── orchestration_router.py # MVP Pipeline orchestration
├── services/                   # Business logic and utilities
│   ├── doc_ai/               # Document AI services
│   ├── preprocessing/         # Document preprocessing
│   │   ├── OCR-processing.py  # OCR processing logic
│   │   └── parsing.py         # Text parsing utilities
│   ├── template_matching/     # MVP Classification (NEW)
│   │   ├── legal_keywords.py  # Legal keyword database
│   │   └── regex_classifier.py # Regex-based classifier
│   ├── kag_component.py       # KAG handoff component (NEW)
│   ├── feature_emitter.py     # Enhanced with classifier verdict
│   ├── util-services.py       # Utility functions
│   └── project_utils.py       # Project utilities
├── data/                      # Data storage directory
│   ├── uploads/              # Uploaded files
│   ├── processed/            # Pipeline results (NEW)
│   └── test-files/           # Test documents
├── docs/                      # Documentation
│   ├── ORCHESTRATION_API.md  # Pipeline API docs (NEW)
│   └── ...                   # Other documentation
├── tests/                     # Test suite
├── requirements.txt           # Python dependencies
├── test_orchestration.py      # Orchestration tests (NEW)
└── README.md                 # Project documentation
```

## 🧪 Testing

### Run MVP Test Suite
```bash
# Run the new MVP regex classification tests
python -m pytest tests/test_single_doc_regex.py -v

# Run quick validation
python tests/test_single_doc_regex.py

# Run migration tests
python test_orchestration.py
```

### Run Full Test Suite
```bash
# Install test dependencies
pip install -r tests/test_requirements.txt

# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_ocr_processing.py
pytest tests/test_api_endpoints.py
pytest tests/test_single_doc_regex.py  # MVP tests
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT_ID` | Google Cloud Project ID | Required |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | Required |
| `DATA_ROOT` | Data storage directory | `./data` |
| `IMAGE_FORMAT` | Output image format | `PNG` |
| `IMAGE_DPI` | Image resolution | `300` |
| `LANGUAGE_HINTS` | OCR language hints | `en` |
| `MAX_FILE_SIZE_MB` | Maximum upload size | `50` |

### Google Cloud Setup

1. Create a Google Cloud Project
2. Enable the Cloud Vision API
3. Create a service account with Vision API permissions
4. Download the service account key file
5. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable

## 🚢 Deployment

### Docker Deployment
```bash
# Build the container
docker build -t ai-backend .

# Run the container
docker run -p 8000:8000 \
  -e GOOGLE_CLOUD_PROJECT_ID=your-project \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  -v /path/to/credentials.json:/app/credentials.json:ro \
  ai-backend
```

### Docker Compose
```bash
docker-compose up -d
```

## 📊 Monitoring and Logging

The application provides comprehensive logging and monitoring:

- **Health Checks**: Service status and dependency checks
- **Processing Metrics**: OCR success rates and processing times
- **Storage Analytics**: Data usage and cleanup statistics
- **Error Tracking**: Detailed error logs with tracebacks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` directory for detailed guides
- **API Docs**: Interactive documentation at `/docs` endpoint
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join project discussions on GitHub

## 🔄 Changelog

### Version 1.1.0 (MVP Prototype)
- ✅ Regex-based document classification system
- ✅ KAG (Knowledge Augmented Generation) component integration
- ✅ Single-document mode enforcement
- ✅ Vertex embedding disabled for prototype
- ✅ Complete artifact generation (classification_verdict.json, kag_input.json, feature_vector.json)
- ✅ Enhanced pipeline orchestration with 6-stage processing
- ✅ Comprehensive MVP test suite

### Version 1.0.0
- ✅ Modular router architecture implementation
- ✅ Google Cloud Vision API integration
- ✅ DocAI-compatible output format
- ✅ Comprehensive test suite
- ✅ Admin tools and monitoring

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Google Cloud Vision](https://cloud.google.com/vision) - OCR capabilities
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing
- [Pillow](https://pillow.readthedocs.io/) - Image manipulation

---

**Built with ❤️ by the DocuMint-AI Team**