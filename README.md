# AI Backend OCR Pipeline# AI Backend OCR Pipeline# AI Backend OCR Pipeline



A production-ready OCR pipeline that integrates **Google Cloud Vision API** with **DocAI schema compliance**. This FastAPI-based service processes documents (PDFs, images) and returns structured OCR results in standardized DocAI format.



## 🎯 Project OverviewA production-ready OCR pipeline with **DocAI schema compliance** and **Google Vision API integration**.  A production-ready OCR pipeline with **DocAI schema compliance** and **Google Vision API integration**.  



This AI backend provides a complete document processing pipeline that:Built with **FastAPI**, **Google Cloud Vision**, and **virtual environment support**.Built with **FastAPI**, **Google Cloud Vision**, and **virtual environment support**.

- Extracts text from PDFs and images using Google Cloud Vision API

- Transforms OCR results into DocAI-compliant JSON format

- Offers RESTful API endpoints for upload, processing, and result retrieval

- Supports multi-language document processing (English, Spanish, French)## 🎯 Key Features## 🎯 Key Features

- Maintains stable document identifiers and structured output



## ✨ Key Features

- ✅ **DocAI Schema Compliance**: Output strictly follows DocAI format with stable identifiers- ✅ **DocAI Schema Compliance**: Output strictly follows DocAI format with stable identifiers

- **DocAI Schema Compliance**: Standardized output format with stable identifiers

- **Google Vision Integration**: High-accuracy OCR with confidence scores- ✅ **Google Vision API**: High-accuracy OCR with multi-language support (EN, ES, FR)- ✅ **Google Vision API**: High-accuracy OCR with multi-language support (EN, ES, FR)

- **FastAPI Framework**: Production-ready API with automatic documentation

- **Multi-language Support**: Process documents in EN, ES, FR- ✅ **Production Ready**: FastAPI with health monitoring and comprehensive error handling- ✅ **Production Ready**: FastAPI with health monitoring and comprehensive error handling

- **Virtual Environment**: Isolated Python dependencies

- **Health Monitoring**: Built-in health checks and error handling- ✅ **Virtual Environment**: Isolated Python environment with automated setup- ✅ **Virtual Environment**: Isolated Python environment with automated setup

- **Portable Architecture**: Relative paths work across different systems

- ✅ **Portable Architecture**: Relative paths work across different systems- ✅ **Portable Architecture**: Relative paths work across different systems

## 🚀 Quick Setup Instructions

- ✅ **Complete API**: Upload, process, and retrieve results via REST endpoints- ✅ **Complete API**: Upload, process, and retrieve results via REST endpoints

### Prerequisites



Before starting, ensure you have:

- **Python 3.8+** installed## 🚀 Quick Start Setup## 🚀 Quick Start

- **Google Cloud Project** with billing enabled

- **Service Account** with Vision API permissions



### Step 1: Environment SetupGet your DocAI-compliant OCR pipeline running in 5 minutes!### Option 1: Automated Setup (Recommended)



```bash```bash

# Clone the repository

git clone <your-repository-url>### Prerequisites ✅# Clone and run setup

cd ai-backend

git clone <repository-url>

# Run automated setup script

./setup.sh                    # Linux/macOS- **Python 3.8+** (check: `python3 --version`)cd ai-backend

# OR

setup.bat                     # Windows- **Google Cloud Project** with billing enabled./setup.sh                    # Linux/macOS



# This will:- **Service Account** with Vision API permissions# OR setup.bat                # Windows

# - Create virtual environment

# - Install all dependencies

# - Set up directory structure

```### Step 1: Clone & Setup ⚡# Configure Google Cloud (see QUICKSTART.md)



### Step 2: Google Cloud Configuration# Then test:



1. **Create Service Account**:```bashpython test_vision_connection.py

   - Go to [Google Cloud Console](https://console.cloud.google.com/)

   - Enable Cloud Vision API# Clone the repositorypython services/processing-handler.py

   - Create Service Account with Vision API permissions

   - Download JSON credentials filegit clone <repository-url>```



2. **Configure Credentials**:cd ai-backend

   ```bash

   # Place your credentials file here:### Option 2: Manual Setup

   cp your-service-account.json data/.cheetah/gcloud/vision-credentials.json

   ```# Run automated setup```bash



3. **Update Environment Variables**:./setup.sh                    # Linux/macOS# Create virtual environment

   Edit `.env` file with your project details:

   ```env# ORpython3 -m venv venv

   GOOGLE_CLOUD_PROJECT_ID=your-project-id

   GOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.jsonsetup.bat                     # Windowssource venv/bin/activate       # Linux/macOS

   ```

# venv\\Scripts\\activate.bat   # Windows

### Step 3: Verify Installation

# This creates virtual environment and installs all dependencies

```bash

# Activate virtual environment```# Install dependencies

source venv/bin/activate       # Linux/macOS

# venv\Scripts\activate.bat    # Windowspip install -r requirements.txt



# Test Google Vision connection### Step 2: Google Cloud Configuration 🔧

python test_vision_connection.py

# Configure environment (see docs/README-COMPLETE.md)

# Expected output:

# ✓ OCR instance created successfully#### 2.1 Get Your Credentials```

# ✓ OCR processing completed successfully

# ✓ DocAI document created successfully1. Go to [Google Cloud Console](https://console.cloud.google.com/)

# 🎉 SUCCESS: Google Vision API is working correctly!

```2. Create/select your project## 📚 Documentation



### Step 4: Start the Server3. Enable **Cloud Vision API**



```bash4. Create **Service Account** → Download JSON credentials- **[🚀 QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes

# Start FastAPI server

python services/processing-handler.py- **[📖 Complete Guide](docs/README-COMPLETE.md)** - Full documentation



# Server will start on: http://localhost:8000#### 2.2 Place Credentials- **[🔧 API Docs](http://localhost:8000/docs)** - Interactive API documentation (when server is running)

# API documentation: http://localhost:8000/docs

``````bash



### Step 5: Test the API# Save your credentials file as:## 🏗️ Architecture



```bashcp your-downloaded-file.json data/.cheetah/gcloud/vision-credentials.json

# Health check

curl http://localhost:8000/health```### Project Structure



# Upload a document```

curl -X POST "http://localhost:8000/upload" \

     -F "file=@your-document.pdf"#### 2.3 Update Project IDai-backend/



# Process with OCR (use UID from upload response)Edit `.env` file:├── 📁 data/                          # Data directory (gitignored)

curl -X POST "http://localhost:8000/ocr-process" \

     -H "Content-Type: application/json" \```env│   ├── .cheetah/gcloud/             # Google Cloud credentials

     -d '{"uid": "your-document-uid"}'

GOOGLE_CLOUD_PROJECT_ID=your-actual-project-id│   ├── uploads/                      # Uploaded files

# Get results in DocAI format

curl http://localhost:8000/results/your-document-uid```│   └── processed/                    # Processed files

```

├── 📁 services/                      # Core services

## 📁 Project Structure

### Step 3: Test Everything 🧪│   ├── preprocessing/

```

ai-backend/│   │   ├── OCR-processing.py        # Google Vision OCR wrapper

├── services/                     # Core application services

│   ├── preprocessing/```bash│   │   └── parsing.py               # Text parsing utilities

│   │   ├── OCR-processing.py    # Google Vision OCR wrapper

│   │   └── parsing.py           # Text processing utilities# Activate environment│   ├── processing-handler.py        # FastAPI endpoints

│   ├── processing-handler.py    # FastAPI main application

│   ├── project_utils.py         # Path and utility functionssource venv/bin/activate       # Linux/macOS│   ├── project_utils.py             # Path utilities

│   └── util-services.py         # Helper services

├── data/                         # Data storage (gitignored)# venv\\Scripts\\activate.bat   # Windows│   └── util-services.py             # Utility functions

│   ├── .cheetah/gcloud/         # Google Cloud credentials

│   ├── uploads/                 # Uploaded documents├── 📁 tests/                         # Test files

│   └── test-files/              # Test data

├── tests/                        # Test suite# Test connection├── 📁 docs/                          # Documentation

├── docs/                         # Documentation

├── models/                       # Configuration filespython test_vision_connection.py├── 📁 venv/                          # Virtual environment

├── venv/                         # Virtual environment

├── requirements.txt              # Python dependencies├── 📄 requirements.txt               # Python dependencies

├── setup.sh / setup.bat          # Setup scripts

└── .env                          # Environment configuration# Expected output:├── 🔧 setup.sh / setup.bat          # Setup scripts

```

# ✓ OCR instance created successfully└── ⚙️ .env                          # Environment configuration

## 🔌 API Endpoints

# ✓ OCR processing completed successfully  ```

| Method | Endpoint | Description |

|--------|----------|-------------|# ✓ DocAI document created successfully

| `GET` | `/health` | System health check |

| `POST` | `/upload` | Upload PDF/image files |# 🎉 SUCCESS: Google Vision API is working correctly!### API Endpoints

| `POST` | `/ocr-process` | Process documents with OCR |

| `GET` | `/results/{uid}` | Retrieve DocAI-formatted results |```- `GET /health` - System health check

| `GET` | `/docs` | Interactive API documentation |

- `POST /upload` - Upload PDF/image files

## 📊 DocAI Output Format

### Step 4: Start the Server 🌐- `POST /ocr-process` - Process documents with OCR

The pipeline produces standardized DocAI-compliant JSON:

- `GET /results/{uid}` - Retrieve DocAI-formatted results

```json

{```bash- `GET /docs` - Interactive API documentation

  "document_id": "doc_20250915_141650_abc123",

  "original_filename": "document.pdf",# Start FastAPI server

  "ocr_result": {

    "pages": [python services/processing-handler.py## 📋 Requirements

      {

        "page": 1,

        "text_blocks": [

          {# Server starts on: http://localhost:8000- **Python 3.8+**

            "block_id": "block_001",

            "text": "Extracted text content...",```- **Google Cloud Project** with Vision API enabled

            "confidence": 0.98,

            "bounding_box": [100, 200, 500, 250],- **Service Account** with Vision API permissions

            "lines": [...]

          }### Step 5: Test the API 📡- **Billing enabled** on Google Cloud project

        ]

      }

    ]

  },#### Health Check## 🧪 Testing

  "language_detection": {

    "primary": "en",```bash

    "confidence": 0.98

  },curl http://localhost:8000/health```bash

  "preprocessing": {

    "pipeline_version": "2.0.0"```# Activate environment

  },

  "warnings": []source venv/bin/activate

}

```#### Upload a Document



## ⚙️ Configuration```bash# Test Google Vision connection



Key environment variables in `.env`:curl -X POST "http://localhost:8000/upload" \python test_vision_connection.py



```env     -F "file=@your-document.pdf"

# Google Cloud Configuration

GOOGLE_CLOUD_PROJECT_ID=your-project-id# Run unit tests

GOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.json

# Returns: {"uid": "doc_20250915_...", "status": "uploaded"}python -m pytest tests/

# OCR Processing Settings

LANGUAGE_HINTS=en,es,fr```

MAX_FILE_SIZE_MB=50

PDF_DPI=300# Test health endpoint



# Server Configuration#### Process with OCRcurl http://localhost:8000/health

API_HOST=0.0.0.0

API_PORT=8000```bash```

```

curl -X POST "http://localhost:8000/ocr-process" \

## 🧪 Testing

     -H "Content-Type: application/json" \## 📊 DocAI Schema Output

```bash

# Activate environment     -d '{"uid": "your-uid-from-upload"}'

source venv/bin/activate

The pipeline produces strictly compliant DocAI format:

# Run all tests

python -m pytest tests/# Returns: {"status": "completed", "docai_format": true}



# Test specific components``````json

python test_vision_connection.py

python tests/test_ocr_processing.py{



# Test API endpoints#### Get Results (DocAI Format)  "document_id": "doc_20250915_141650_abc123",

curl http://localhost:8000/health

``````bash  "original_filename": "document.pdf", 



## 🛠️ Troubleshootingcurl http://localhost:8000/results/your-uid  "ocr_result": {



| Issue | Solution |    "pages": [

|-------|----------|

| `403 Billing disabled` | Enable billing in Google Cloud Console |# Returns complete DocAI-compliant JSON      {

| `Credentials not found` | Verify `.env` file and credentials path |

| `Import errors` | Ensure virtual environment is activated |```        "page": 1,

| `Permission denied` | Check service account has Vision API role |

| `Connection timeout` | Verify internet connection and GCP quotas |        "text_blocks": [



## 🔧 Development Commands## 🎯 That's It! Your Pipeline is Ready          {



```bash            "block_id": "block_001",

# Activate virtual environment

source venv/bin/activate### What You Get:            "text": "Extracted text...",



# Start development server- ✅ **DocAI-compliant output** with stable identifiers            "confidence": 0.98,

python services/processing-handler.py

- ✅ **Multi-language OCR** (EN, ES, FR)            "bounding_box": [100, 200, 500, 250],

# Run tests

python -m pytest tests/ -v- ✅ **Production-ready API** with health monitoring            "lines": [...]



# Test Google Vision connection- ✅ **Automatic documentation** at http://localhost:8000/docs          }

python test_vision_connection.py

        ]

# Check API health

curl http://localhost:8000/health## 🏗️ Architecture      }

```

    ]

## 🚀 Production Deployment

### Project Structure  },

For production environments:

```  "language_detection": {"primary": "en", "confidence": 0.98},

1. **Container Deployment**: Use Docker for consistent environments

2. **Cloud Deployment**: Deploy on Google Cloud Run or Kubernetesai-backend/  "preprocessing": {"pipeline_version": "2.0.0"},

3. **Monitoring**: Implement logging and health monitoring

4. **Security**: Add authentication and rate limiting├── 📁 data/                          # Data directory (gitignored)  "warnings": []

5. **Scaling**: Configure auto-scaling based on load

│   ├── .cheetah/gcloud/             # Google Cloud credentials}

## 📚 Documentation

│   ├── uploads/                      # Uploaded files```

- **[Complete Documentation](docs/README-COMPLETE.md)** - Comprehensive guide

- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs│   └── processed/                    # Processed files

- **[OCR Processing Details](docs/OCR-processing.md)** - Technical details

- **[Service Configuration](docs/service-wise-execution.md)** - Setup guide├── 📁 services/                      # Core services## 🔧 Configuration



## 🤝 Support│   ├── preprocessing/



- **Health Monitoring**: `curl http://localhost:8000/health`│   │   ├── OCR-processing.py        # Google Vision OCR wrapperEnvironment variables in `.env`:

- **Connection Testing**: `python test_vision_connection.py`

- **API Documentation**: Visit http://localhost:8000/docs│   │   └── parsing.py               # Text parsing utilities```env

- **Logs**: Check terminal output for detailed error messages

│   ├── processing-handler.py        # FastAPI endpoints# Google Cloud

## 📝 License

│   ├── project_utils.py             # Path utilitiesGOOGLE_CLOUD_PROJECT_ID=your-project-id

This project is proprietary software developed for DocuMint-AI.

│   └── util-services.py             # Utility functionsGOOGLE_APPLICATION_CREDENTIALS=./data/.cheetah/gcloud/vision-credentials.json

---

├── 📁 tests/                         # Test files

**Ready to process documents with DocAI compliance!** 🎉

├── 📁 docs/                          # Documentation# OCR Settings  

Start by following the Quick Setup Instructions above to get your OCR pipeline running in minutes.
├── 📁 venv/                          # Virtual environmentLANGUAGE_HINTS=en,es,fr

├── 📄 requirements.txt               # Python dependenciesMAX_FILE_SIZE_MB=50

├── 🔧 setup.sh / setup.bat          # Setup scriptsPDF_DPI=300

└── ⚙️ .env                          # Environment configuration

```# Server

API_HOST=0.0.0.0

### API EndpointsAPI_PORT=8000

- `GET /health` - System health check```

- `POST /upload` - Upload PDF/image files

- `POST /ocr-process` - Process documents with OCR## 🚀 Production Deployment

- `GET /results/{uid}` - Retrieve DocAI-formatted results

- `GET /docs` - Interactive API documentationFor production use:

1. **Containerization**: Use Docker for consistent deployment

## 📊 DocAI Schema Output2. **Scaling**: Deploy on Google Cloud Run or Kubernetes

3. **Monitoring**: Set up logging and health checks

The pipeline produces strictly compliant DocAI format:4. **Security**: Implement authentication and rate limiting

5. **Caching**: Add Redis for result caching

```json

{## 📞 Support

  "document_id": "doc_20250915_141650_abc123",

  "original_filename": "document.pdf", - **Health Check**: `curl http://localhost:8000/health`

  "ocr_result": {- **Connection Test**: `python test_vision_connection.py`

    "pages": [- **API Documentation**: http://localhost:8000/docs

      {- **Complete Guide**: [docs/README-COMPLETE.md](docs/README-COMPLETE.md)

        "page": 1,

        "text_blocks": [## 📄 License

          {

            "block_id": "block_001",This project is proprietary software for DocuMint-AI.

            "text": "Extracted text...",

            "confidence": 0.98,---

            "bounding_box": [100, 200, 500, 250],

            "lines": [...]**🎉 Ready to process documents with DocAI compliance!** Start with [QUICKSTART.md](QUICKSTART.md) for immediate setup.

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

## Quick Commands Reference 📚

```bash
# Activate environment
source venv/bin/activate

# Start server
python services/processing-handler.py

# Test connection
python test_vision_connection.py

# Run tests
python -m pytest tests/

# Check health
curl http://localhost:8000/health
```

## Troubleshooting 🔧

| Issue | Solution |
|-------|----------|
| `403 Billing disabled` | Enable billing in Google Cloud Console |
| `Credentials not found` | Check `.env` file and credentials path |
| `Import errors` | Activate venv: `source venv/bin/activate` |
| `Permission denied` | Ensure service account has Vision API role |

## 🚀 Production Deployment

For production use:
1. **Containerization**: Use Docker for consistent deployment
2. **Scaling**: Deploy on Google Cloud Run or Kubernetes
3. **Monitoring**: Set up logging and health checks
4. **Security**: Implement authentication and rate limiting
5. **Caching**: Add Redis for result caching

## 📚 Documentation

- **[📖 Complete Guide](docs/README-COMPLETE.md)** - Full documentation
- **[🔧 API Docs](http://localhost:8000/docs)** - Interactive API documentation (when server is running)
- **[📄 OCR Processing](docs/OCR-processing.md)** - OCR processing details
- **[⚙️ Service Execution](docs/service-wise-execution.md)** - Service configuration

## 📞 Support

- **Health Check**: `curl http://localhost:8000/health`
- **Connection Test**: `python test_vision_connection.py`
- **API Documentation**: http://localhost:8000/docs
- **Complete Guide**: [docs/README-COMPLETE.md](docs/README-COMPLETE.md)

## 📄 License

This project is proprietary software for DocuMint-AI.

---

**🎉 Congratulations!** Your DocAI-compliant OCR pipeline is now ready for production use!