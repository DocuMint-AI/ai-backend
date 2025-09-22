# DocAI Integration Setup Guide

This guide covers the setup and usage of the Google Document AI integration for the AI Backend Document Processing API.

## Overview

The DocAI integration provides advanced document parsing capabilities using Google Document AI, extracting structured information including:

- **Full text** with character offsets
- **Named entities** (persons, organizations, dates, money, etc.)
- **Clauses** (termination, payment, confidentiality, etc.)
- **Key-value pairs** from forms
- **Cross-references** between entities
- **Confidence scores** and metadata

## Prerequisites

### 1. Google Cloud Project Setup

1. **Create or select a Google Cloud Project**
   ```bash
   # Set your project ID
   export PROJECT_ID="your-project-id"
   gcloud config set project $PROJECT_ID
   ```

2. **Enable required APIs**
   ```bash
   # Enable Document AI API
   gcloud services enable documentai.googleapis.com
   
   # Enable Cloud Storage API (for document storage)
   gcloud services enable storage-component.googleapis.com
   ```

3. **Create a Document AI Processor**
   ```bash
   # List available processor types
   gcloud ai document-processors types list --location=us
   
   # Create a form parser processor (recommended for contracts)
   gcloud ai document-processors processors create \
     --display-name="Contract Parser" \
     --type="FORM_PARSER_PROCESSOR" \
     --location=us
   ```

### 2. Service Account Setup

1. **Create a service account**
   ```bash
   gcloud iam service-accounts create docai-service \
     --display-name="DocAI Service Account" \
     --description="Service account for Document AI processing"
   ```

2. **Grant required permissions**
   ```bash
   # Document AI User role
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:docai-service@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/documentai.apiUser"
   
   # Storage Object Viewer (to read documents from GCS)
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:docai-service@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/storage.objectViewer"
   ```

3. **Create and download service account key**
   ```bash
   gcloud iam service-accounts keys create credentials.json \
     --iam-account=docai-service@${PROJECT_ID}.iam.gserviceaccount.com
   ```

### 3. Google Cloud Storage Bucket

1. **Create a storage bucket** (if you don't have one)
   ```bash
   gsutil mb gs://${PROJECT_ID}-documents
   ```

2. **Upload test documents**
   ```bash
   gsutil cp /path/to/your/document.pdf gs://${PROJECT_ID}-documents/
   ```

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
# Google Cloud Project Configuration
GOOGLE_CLOUD_PROJECT_ID="your-project-id"
GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# Document AI Configuration
DOCAI_LOCATION="us"  # or your preferred location
DOCAI_PROCESSOR_ID="your-processor-id"  # from processor creation
DOCAI_CONFIDENCE_THRESHOLD="0.7"  # minimum confidence for entities

# Optional: Existing configuration
DATA_ROOT="/data"
IMAGE_FORMAT="PNG"
IMAGE_DPI="300"
MAX_FILE_SIZE_MB="50"
```

### Getting Your Processor ID

```bash
# List your processors to get the ID
gcloud ai document-processors processors list --location=us
```

The output will show your processor ID in the format:
```
projects/PROJECT_ID/locations/LOCATION/processors/PROCESSOR_ID
```

Use only the `PROCESSOR_ID` part (e.g., `1234567890abcdef`) for the `DOCAI_PROCESSOR_ID` variable.

## Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation**
   ```bash
   # Test Google Cloud authentication
   python -c "from google.cloud import documentai; print('DocAI SDK installed successfully')"
   ```

## API Endpoints

### 1. Document Parsing

**Endpoint:** `POST /api/docai/parse`

Parse a single document from Google Cloud Storage.

**Request:**
```json
{
  "gcs_uri": "gs://your-bucket/document.pdf",
  "processor_id": "optional-specific-processor",
  "confidence_threshold": 0.8,
  "enable_native_pdf_parsing": true,
  "include_raw_response": false,
  "metadata": {
    "customer_id": "12345",
    "document_type": "contract"
  }
}
```

**Response:**
```json
{
  "success": true,
  "document": {
    "metadata": {
      "document_id": "docai_1703123456_1234",
      "original_filename": "contract.pdf",
      "file_size": 1048576,
      "page_count": 5,
      "language": "en",
      "processing_timestamp": "2024-01-01T12:00:00.000Z",
      "processor_id": "1234567890abcdef",
      "confidence_threshold": 0.8
    },
    "full_text": "This agreement is between...",
    "named_entities": [
      {
        "id": "entity_0001",
        "type": "ORGANIZATION",
        "text_span": {
          "start_offset": 25,
          "end_offset": 35,
          "text": "Company A"
        },
        "confidence": 0.95,
        "normalized_value": "Company A",
        "page_number": 1
      }
    ],
    "clauses": [
      {
        "id": "clause_0001",
        "type": "TERMINATION",
        "text_span": {
          "start_offset": 1250,
          "end_offset": 1450,
          "text": "This agreement shall terminate..."
        },
        "confidence": 0.88,
        "page_number": 3
      }
    ],
    "key_value_pairs": [
      {
        "id": "kvp_0001",
        "key": {
          "start_offset": 100,
          "end_offset": 110,
          "text": "Start Date"
        },
        "value": {
          "start_offset": 115,
          "end_offset": 125,
          "text": "2024-01-01"
        },
        "confidence": 0.92,
        "page_number": 1
      }
    ],
    "cross_references": [],
    "processing_warnings": []
  },
  "processing_time_seconds": 3.45,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. Batch Processing

**Endpoint:** `POST /api/docai/parse/batch`

Process multiple documents in batch (up to 10 documents).

**Request:**
```json
[
  "gs://your-bucket/contract1.pdf",
  "gs://your-bucket/contract2.pdf",
  "gs://your-bucket/invoice.pdf"
]
```

### 3. Health Check

**Endpoint:** `GET /health`

Check service health and configuration.

### 4. Configuration

**Endpoint:** `GET /api/docai/config`

Get current DocAI configuration.

### 5. List Processors

**Endpoint:** `GET /api/docai/processors`

List available DocAI processors.

## Usage Examples

### Basic Usage with curl

```bash
# Parse a single document
curl -X POST "http://localhost:8000/api/docai/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "gcs_uri": "gs://my-bucket/documents/contract.pdf",
    "confidence_threshold": 0.8
  }'
```

### Python Client Example

```python
import httpx
import asyncio

async def parse_document():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/docai/parse",
            json={
                "gcs_uri": "gs://my-bucket/contract.pdf",
                "confidence_threshold": 0.8,
                "metadata": {"department": "legal"}
            }
        )
        
        result = response.json()
        if result["success"]:
            doc = result["document"]
            print(f"Processed {doc['metadata']['original_filename']}")
            print(f"Found {len(doc['named_entities'])} entities")
            print(f"Found {len(doc['clauses'])} clauses")
        else:
            print(f"Processing failed: {result['error_message']}")

# Run the example
asyncio.run(parse_document())
```

## Testing

### Running Tests

```bash
# Run all DocAI tests
pytest tests/test_doc_ai.py -v

# Run with coverage
pytest tests/test_doc_ai.py --cov=services.doc_ai --cov-report=html
```

### Manual Testing

1. **Upload a test document to GCS**
   ```bash
   gsutil cp sample_document.pdf gs://your-bucket/test/
   ```

2. **Test the health endpoint**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test document parsing**
   ```bash
   curl -X POST "http://localhost:8000/api/docai/parse" \
     -H "Content-Type: application/json" \
     -d '{"gcs_uri": "gs://your-bucket/test/sample_document.pdf"}'
   ```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```
   Error: DocAI client initialization failed: Failed to authenticate
   ```
   - Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid credentials file
   - Check service account has required permissions
   - Ensure project ID is correct

2. **Processor Not Found**
   ```
   Error: No processor ID provided
   ```
   - Set `DOCAI_PROCESSOR_ID` environment variable
   - Verify processor exists: `gcloud ai document-processors processors list --location=us`

3. **GCS Access Denied**
   ```
   Error: Failed to download from GCS: 403 Forbidden
   ```
   - Verify service account has `storage.objectViewer` role
   - Check bucket permissions
   - Ensure GCS URI is correct format: `gs://bucket/path/file.pdf`

4. **Document Processing Timeout**
   ```
   Error: DocAI processing failed: Deadline exceeded
   ```
   - Large documents may take time to process
   - Check document format is supported (PDF, TIFF, PNG, JPEG)
   - Consider using async processing for large files

### Debug Mode

Enable debug logging by setting:

```bash
export LOG_LEVEL=DEBUG
```

Or modify the logging configuration in your application.

### Performance Optimization

1. **Processor Selection**
   - Use specialized processors for specific document types
   - Form Parser: contracts, agreements, forms
   - OCR Processor: scanned documents, images

2. **Batch Processing**
   - Use batch endpoint for multiple documents
   - Process similar document types together

3. **Confidence Thresholds**
   - Lower thresholds (0.5-0.7) for higher recall
   - Higher thresholds (0.8-0.9) for higher precision

## Integration with Main Application

### Register Router

Update `main.py` to include the DocAI router:

```python
from routers import doc_ai_router

# Register DocAI router
app.include_router(
    doc_ai_router.router,
    tags=["Document AI"],
    responses={404: {"description": "Not found"}},
)
```

### Update Root Endpoint

Add DocAI endpoints to the root endpoint information:

```python
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "AI Backend Document Processing API",
        "version": "1.0.0",
        "endpoints": {
            # ... existing endpoints ...
            "docai_parse": "/api/docai/parse",
            "docai_batch": "/api/docai/parse/batch",
            "docai_config": "/api/docai/config",
            "docai_processors": "/api/docai/processors"
        }
    }
```

## Security Considerations

1. **Credential Management**
   - Never commit credentials to version control
   - Use environment variables or secret management
   - Rotate service account keys regularly

2. **Access Control**
   - Limit service account permissions to minimum required
   - Use IAM conditions for fine-grained access
   - Monitor API usage and costs

3. **Data Privacy**
   - Ensure documents comply with data protection regulations
   - Consider data residency requirements
   - Use appropriate GCS bucket policies

## Support and Resources

- [Google Document AI Documentation](https://cloud.google.com/document-ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)

For issues and questions, please refer to the project's issue tracker or documentation.