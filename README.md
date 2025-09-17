# AI Backend Document Processing API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![Google Cloud Vision](https://img.shields.io/badge/Google%20Cloud-Vision%20API-red)](https://cloud.google.com/vision)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A high-performance FastAPI service for PDF document processing, OCR (Optical Character Recognition), and text parsing using Google Cloud Vision API. Features DocAI-compatible output format and modular router architecture for scalability.

## 🚀 Features

- **PDF Processing**: Convert PDF documents to high-quality images
- **OCR Integration**: Google Cloud Vision API for accurate text extraction
- **DocAI Compatible**: Output format compatible with Google Document AI
- **Multi-language Support**: Configurable language hints for better OCR accuracy
- **File Management**: Upload, process, and manage document processing workflows
- **Admin Tools**: Data purge operations and usage analytics
- **Modular Architecture**: Router-based design for easy feature expansion
- **Background Processing**: Async processing for large documents
- **Health Monitoring**: Comprehensive health checks and status endpoints

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

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
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
python main.py

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

## 🔧 Usage Examples

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

## 🏗 Project Structure

```
ai-backend/
├── main.py                     # FastAPI application entry point
├── routers/                    # Modular router architecture
│   ├── __init__.py            # Router package initialization
│   └── processing_handler.py  # Document processing endpoints
├── services/                   # Business logic and utilities
│   ├── agents.py              # AI agent services
│   ├── classification.py      # Document classification
│   ├── processing-handler.py  # Legacy monolithic handler
│   ├── util-services.py       # Utility functions
│   └── preprocessing/         # Document preprocessing
│       ├── OCR-processing.py  # OCR processing logic
│       └── parsing.py         # Text parsing utilities
├── data/                      # Data storage directory
│   ├── uploads/              # Uploaded files
│   └── test-files/           # Test documents
├── tests/                     # Test suite
├── docs/                      # Documentation
├── requirements.txt           # Python dependencies
└── README.md                 # Project documentation
```

## 🧪 Testing

### Run Migration Tests
```bash
python test_migration.py
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