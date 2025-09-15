# AI Backend OCR Pipeline

A production-ready OCR pipeline with **DocAI schema compliance** and **Google Vision API integration**.  
Built with **FastAPI**, **Google Cloud Vision**, and **virtual environment support**.

## 🎯 Key Features

- ✅ **DocAI Schema Compliance**: Output strictly follows DocAI format with stable identifiers
- ✅ **Google Vision API**: High-accuracy OCR with multi-language support (EN, ES, FR)
- ✅ **Production Ready**: FastAPI with health monitoring and comprehensive error handling
- ✅ **Virtual Environment**: Isolated Python environment with automated setup
- ✅ **Portable Architecture**: Relative paths work across different systems
- ✅ **Complete API**: Upload, process, and retrieve results via REST endpoints

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Clone and run setup
git clone <repository-url>
cd ai-backend
./setup.sh                    # Linux/macOS
# OR setup.bat                # Windows

# Configure Google Cloud (see QUICKSTART.md)
# Then test:
python test_vision_connection.py
python services/processing-handler.py
```

### Option 2: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\\Scripts\\activate.bat   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment (see docs/README-COMPLETE.md)
```

## 📚 Documentation

- **[🚀 QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[📖 Complete Guide](docs/README-COMPLETE.md)** - Full documentation
- **[🔧 API Docs](http://localhost:8000/docs)** - Interactive API documentation (when server is running)

## 🏗️ Architecture

### Project Structure
```
ai-backend/
├── 📁 data/                          # Data directory (gitignored)
│   ├── .cheetah/gcloud/             # Google Cloud credentials
│   ├── uploads/                      # Uploaded files
│   └── processed/                    # Processed files
├── 📁 services/                      # Core services
│   ├── preprocessing/
│   │   ├── OCR-processing.py        # Google Vision OCR wrapper
│   │   └── parsing.py               # Text parsing utilities
│   ├── processing-handler.py        # FastAPI endpoints
│   ├── project_utils.py             # Path utilities
│   └── util-services.py             # Utility functions
├── 📁 tests/                         # Test files
├── 📁 docs/                          # Documentation
├── 📁 venv/                          # Virtual environment
├── 📄 requirements.txt               # Python dependencies
├── 🔧 setup.sh / setup.bat          # Setup scripts
└── ⚙️ .env                          # Environment configuration
```

### API Endpoints
- `GET /health` - System health check
- `POST /upload` - Upload PDF/image files
- `POST /ocr-process` - Process documents with OCR
- `GET /results/{uid}` - Retrieve DocAI-formatted results
- `GET /docs` - Interactive API documentation

## 📋 Requirements

- **Python 3.8+**
- **Google Cloud Project** with Vision API enabled
- **Service Account** with Vision API permissions
- **Billing enabled** on Google Cloud project

## 🧪 Testing

```bash
# Activate environment
source venv/bin/activate

# Test Google Vision connection
python test_vision_connection.py

# Run unit tests
python -m pytest tests/

# Test health endpoint
curl http://localhost:8000/health
```

## 📊 DocAI Schema Output

The pipeline produces strictly compliant DocAI format:

```json
{
  "document_id": "doc_20250915_141650_abc123",
  "original_filename": "document.pdf", 
  "ocr_result": {
    "pages": [
      {
        "page": 1,
        "text_blocks": [
          {
            "block_id": "block_001",
            "text": "Extracted text...",
            "confidence": 0.98,
            "bounding_box": [100, 200, 500, 250],
            "lines": [...]
          }
        ]
      }
    ]
  },
  "language_detection": {"primary": "en", "confidence": 0.98},
  "preprocessing": {"pipeline_version": "2.0.0"},
  "warnings": []
}
```

## 🔧 Configuration

Environment variables in `.env`:
```env
# Google Cloud
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.json

# OCR Settings  
LANGUAGE_HINTS=en,es,fr
MAX_FILE_SIZE_MB=50
PDF_DPI=300

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## 🚀 Production Deployment

For production use:
1. **Containerization**: Use Docker for consistent deployment
2. **Scaling**: Deploy on Google Cloud Run or Kubernetes
3. **Monitoring**: Set up logging and health checks
4. **Security**: Implement authentication and rate limiting
5. **Caching**: Add Redis for result caching

## 📞 Support

- **Health Check**: `curl http://localhost:8000/health`
- **Connection Test**: `python test_vision_connection.py`
- **API Documentation**: http://localhost:8000/docs
- **Complete Guide**: [docs/README-COMPLETE.md](docs/README-COMPLETE.md)

## 📄 License

This project is proprietary software for DocuMint-AI.

---

**🎉 Ready to process documents with DocAI compliance!** Start with [QUICKSTART.md](QUICKSTART.md) for immediate setup.

