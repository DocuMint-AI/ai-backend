# AI Backend Document Processing - Hackathon Prototype

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![Google Cloud Vision](https://img.shields.io/badge/Google%20Cloud-Vision%20API-red)](https://cloud.google.com/vision)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A self-contained 7-stage PDF document processing pipeline for hackathon submission featuring PDF → OCR → Classification → KAG → RAG integration.

## 🎯 Prototype Features

**This is a hackathon prototype with the following characteristics:**
- ✅ **Self-contained pipeline** - Complete 7-stage orchestration
- ✅ **Regex-based classification** - 784 patterns across 61 legal subcategories
- ✅ **Google Vision OCR** - High-quality text extraction with confidence scoring
- ✅ **KAG-RAG integration** - Knowledge Augmented Generation with RAG compatibility
- ✅ **Hybrid PDF processing** - Multi-library fallback system
- ✅ **Intelligent credentials** - 3-tier credential discovery system
- ✅ **Complete artifacts** - All intermediate and final outputs preserved

## 🚀 Features

- **📄 Hybrid PDF Processing**: PyMuPDF → pypdfium2 → pdfplumber fallback chain
- **🔍 Vision OCR Integration**: Google Cloud Vision API with intelligent credential discovery
- **🏷️ Weighted Classification**: 784 regex patterns for legal document categorization  
- **🧠 KAG Generation**: Structured knowledge input generation for downstream processing
- **🔗 RAG Adapter**: Seamless integration with RAG systems (97 chunks from 13-page document)
- **🌐 Multi-language Support**: Configurable language hints (en, es, fr)
- **📊 Confidence Scoring**: Per-page and document-level confidence metrics
- **⚡ Command-line Interface**: Simple argparse-based orchestration
- **💾 Artifact Preservation**: Complete processing history and intermediate results
- **🔧 Credential Management**: Local → Environment → ADC credential priority

## 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Vision API enabled
- Google Cloud Service Account with Vision API permissions

## 🛠 Installation

### 1. Navigate to Prototype Directory
```bash
cd prototype
```

### 2. Set Up Environment (Using uv - Recommended)

**Option A: Using uv (Recommended)**
```bash
# Install dependencies
uv pip install -r requirements.txt

# Or create virtual environment first
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

**Option B: Using traditional Python pip**
```bash
pip install -r requirements.txt
```

### 3. Configure Google Cloud Credentials

**Option 1: Local Credentials (Recommended for Hackathon)**
```bash
# Place your service account key in the prototype data directory
cp /path/to/your/credentials.json data/.cheetah/vision-credentials.json
```

**Option 2: Environment Variable**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
```

**Option 3: Application Default Credentials**
```bash
gcloud auth application-default login
```

## 🚀 Quick Start

### Single Document Processing
```bash
# Process a test document (Insurance document)
python orchestration/run_single_orchestration.py \
  --pdf data/test-files/testing-ocr-pdf-1.pdf \
  --out artifacts/run-001

# Process a legal judgment
python orchestration/run_single_orchestration.py \
  --pdf ../data/test-files/judgement_20142.pdf \
  --out artifacts/run-judgment
```

### Example Output
```
🚀 Starting AI Backend Prototype Pipeline
📄 Input PDF: /path/to/document.pdf
📁 Output Dir: /path/to/artifacts/run-001

Stage 1: Hybrid PDF Processing
✅ Successfully extracted text from 6/6 pages

Stage 2: Vision OCR Processing  
✅ Vision OCR processed 6 pages

Stage 3: Creating parsed_output.json
✅ Saved parsed_output.json

Stage 4: Document Classification
✅ Document classified as 'Financial_and_Security' (score=7.817, confidence=high)

Stage 5: KAG Input Generation
✅ KAG Input generated → /path/to/kag_input.json

Stage 6: Validation
✅ KAG input validation passed
✅ Non-zero document confidence detected: 0.817

Stage 7: KAG-RAG Integration Validation
✅ KAG-RAG integration successful: 41 chunks ready for embeddings
✅ Enhanced QA prompts validated with classifier and confidence metadata

====================== 📊 PIPELINE SUMMARY ======================
📄 Document ID     : test-1758455649
🏷️ Classification  : Financial_and_Security (score=7.817, confidence=high)
✍️ Text length      : 17479 chars
🧾 Clauses         : 0
👤 Named Entities  : 0
🔑 KV Pairs        : 0
🔧 Processing      : pypdfium2+pdfplumber
📊 Pages Processed : 6/6
🔗 RAG Integration : ✅ 41 chunks ready
🎯 Enhanced QA     : ✅ Classifier + confidence metadata included
===============================================================
```

## 📚 7-Stage Pipeline

### Stage 1: Hybrid PDF Processing
- **Purpose**: Extract text and render images from PDF
- **Libraries**: PyMuPDF → pypdfium2 → pdfplumber (fallback chain)
- **Output**: Page text files + high-resolution PNG images (300 DPI)

### Stage 2: Vision OCR Processing
- **Purpose**: Extract text using Google Cloud Vision API
- **Features**: Multi-language support, confidence scoring, credential auto-discovery
- **Output**: Per-page OCR text with confidence metrics

### Stage 3: Parsed Output Generation  
- **Purpose**: Create structured DocAI-compatible output
- **Format**: JSON with text content, page metadata, processing details
- **Output**: `parsed_output.json`

### Stage 4: Document Classification
- **Purpose**: Categorize document using weighted regex patterns
- **Database**: 784 patterns across 61 legal subcategories
- **Output**: `classification_verdict.json` with matched patterns and confidence

### Stage 5: KAG Input Generation
- **Purpose**: Structure document for Knowledge Augmented Generation
- **Features**: Metadata integration, classifier verdict inclusion
- **Output**: `kag_input.json` with complete document context

### Stage 6: Validation
- **Purpose**: Verify data integrity and confidence thresholds
- **Checks**: Document confidence > 0, classification structure validation
- **Output**: Validation status and warnings

### Stage 7: KAG-RAG Integration
- **Purpose**: Prepare document for RAG (Retrieval Augmented Generation)
- **Features**: Chunk generation, enhanced QA context with metadata
- **Output**: Ready-to-embed chunks with classifier and confidence data

## 🏗 Prototype Structure

```
prototype/
├── README.md                   # This file - setup and usage instructions
├── requirements.txt            # Python dependencies for prototype
├── orchestration/              # Pipeline orchestration
│   └── run_single_orchestration.py  # Main CLI entrypoint
├── services/                   # Core processing services
│   ├── util_services.py        # Hybrid PDF processing
│   ├── ocr_processing.py       # Google Vision OCR integration  
│   ├── kag_writer.py          # KAG input generation
│   ├── rag_adapter.py         # RAG system integration
│   ├── project_utils.py       # Utility functions
│   └── exceptions.py          # Custom exceptions
├── template_matching/          # Document classification
│   ├── regex_classifier.py    # Weighted regex classifier
│   ├── legal_keywords.py      # Legal keyword database
│   └── keywords_loader.py     # Keyword loading utilities
├── config/                     # Configuration management
│   └── config.py              # Application configuration
├── data/                       # Data and credentials
│   ├── .cheetah/              # Local credential storage
│   │   └── vision-credentials.json  # Google Cloud credentials
│   ├── test-files/            # Sample test documents
│   ├── processed/             # Processing cache
│   └── uploads/               # File upload area
├── artifacts/                  # Pipeline output storage
│   ├── run-001/               # Example processing run
│   ├── run-004/               # Insurance document test
│   └── run-judgement/         # Legal judgment test
└── tests/                      # Test suite
    └── test_hybrid_pipeline.py  # Pipeline integration tests
```

## 🧪 Testing

### Validate Installation
```bash
# Test the complete pipeline with provided sample
python orchestration/run_single_orchestration.py \
  --pdf data/test-files/testing-ocr-pdf-1.pdf \
  --out artifacts/test-installation

# Check for successful completion
ls artifacts/test-installation/
```

### Test Different Document Types
```bash
# Test with legal judgment (13 pages)
python orchestration/run_single_orchestration.py \
  --pdf ../data/test-files/judgement_20142.pdf \
  --out artifacts/test-judgment

# Expected: ~35K characters, Judicial_Documents classification, 97 RAG chunks
```

### Run Unit Tests
```bash
# Run prototype-specific tests
python -m pytest tests/test_hybrid_pipeline.py -v

# Run test directly
python tests/test_hybrid_pipeline.py
```

## 🔧 Configuration

### Credential Priority System
The prototype uses a 3-tier credential discovery system:

1. **Local Credentials** (Highest Priority)
   - `data/.cheetah/vision-credentials.json`
   - Perfect for hackathon demos and local development

2. **Environment Variable** (Medium Priority)
   - `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Standard Google Cloud authentication

3. **Application Default Credentials** (Lowest Priority)  
   - `gcloud auth application-default login`
   - Automatic for Google Cloud environments

### Language Configuration
```python
# Modify in config/config.py
LANGUAGE_HINTS = ['en', 'es', 'fr']  # OCR language hints
IMAGE_DPI = 300                      # Image resolution
IMAGE_FORMAT = 'PNG'                 # Output image format
```

## 📊 Performance Benchmarks

### Test Results Summary

| Document Type | Pages | Characters | Classification | Confidence | RAG Chunks | Processing Time |
|---------------|-------|------------|----------------|------------|------------|-----------------|
| Insurance Policy | 6 | 17,479 | Financial_and_Security | 0.817 | 41 | ~30s |
| Legal Judgment | 13 | 34,796 | Judicial_Documents | 0.842 | 97 | ~45s |

### Stage Performance
- **PDF Processing**: ~2s per page (text + images)
- **Vision OCR**: ~3s per page (API latency dependent)
- **Classification**: ~1s (784 pattern matching)
- **KAG Generation**: ~2-4s (content dependent)
- **RAG Integration**: ~2s (chunk preparation)

## 🚢 Deployment Notes

### Hackathon Demo Setup
```bash
# Quick demo script
cd prototype
export GOOGLE_APPLICATION_CREDENTIALS="data/.cheetah/vision-credentials.json"
python orchestration/run_single_orchestration.py \
  --pdf data/test-files/testing-ocr-pdf-1.pdf \
  --out artifacts/demo-run
```

### Production Considerations
- Implement async processing for multiple documents
- Add proper error handling and retry logic
- Scale credential management for multi-user environments
- Add monitoring and logging infrastructure
- Implement proper data persistence and cleanup

## 🤝 Development

### Adding New Document Types
1. Add patterns to `template_matching/legal_keywords.py`
2. Test with `template_matching/regex_classifier.py`
3. Validate end-to-end with orchestration

### Extending the Pipeline
1. Add new stage to `orchestration/run_single_orchestration.py`
2. Implement stage logic in appropriate service module
3. Update validation and artifact generation

## 📄 Generated Artifacts

Each pipeline run generates the following artifacts:

### Core Outputs
- **`{document_id}/parsed_output.json`** - DocAI-compatible structured output
- **`{document_id}/classification_verdict.json`** - Document classification results
- **`{document_id}/kag_input.json`** - KAG system input with metadata
- **`{pipeline_id}_pipeline_result.json`** - Complete pipeline summary

### Processing Artifacts
- **`{document_id}/text/page_*.txt`** - Per-page extracted text
- **`{document_id}/images/page_*.png`** - High-resolution page images
- **Processing logs and performance metrics**

## 🔄 Changelog

### Hackathon Prototype v1.0
- ✅ Self-contained 7-stage pipeline implementation
- ✅ Intelligent credential discovery system
- ✅ Hybrid PDF processing with multiple library fallbacks
- ✅ Weighted regex classification with 784 patterns
- ✅ KAG-RAG integration with chunk generation
- ✅ Complete artifact preservation and validation
- ✅ Command-line interface with argparse
- ✅ Comprehensive test coverage with real documents

## 🙏 Acknowledgments

- [Google Cloud Vision](https://cloud.google.com/vision) - OCR capabilities
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing
- [pypdfium2](https://pypdfium2.readthedocs.io/) - Alternative PDF processing
- [pdfplumber](https://github.com/jsvine/pdfplumber) - Fallback PDF processing

---

**🎯 Hackathon-Ready Prototype - Built for Speed and Demonstration**
