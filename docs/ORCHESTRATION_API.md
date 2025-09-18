# Document Processing Pipeline - Orchestration API

## Overview

The orchestration router provides a unified API endpoint that combines the entire document processing pipeline into a single, streamlined workflow. This implementation maintains the existing modular structure while providing an easy-to-use interface for complete document processing.

## Pipeline Flow

The orchestration endpoint (`/api/v1/process-document`) executes the following sequential steps:

1. **Upload PDF** - Securely upload and validate PDF files
2. **Convert PDF to Images** - Extract individual pages as high-quality images
3. **Vision AI Processing** - Extract text and bounding boxes using Google Cloud Vision
4. **Document AI Processing** - Parse structured data, entities, and legal references
5. **Save Results** - Store consolidated results in the `data/processed/` directory

## API Endpoints

### Process Document Pipeline

**POST** `/api/v1/process-document`

Process a complete document through the entire pipeline.

**Parameters:**
- `file` (required): PDF file to process
- `language_hints` (optional): Comma-separated language codes (default: "en")
- `confidence_threshold` (optional): DocAI confidence threshold 0.0-1.0 (default: 0.7)
- `processor_id` (optional): DocAI processor ID override
- `include_raw_response` (optional): Include raw DocAI response (default: false)
- `force_reprocess` (optional): Force reprocessing existing results (default: false)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/process-document" \
     -F "file=@contract.pdf" \
     -F "language_hints=en,hi" \
     -F "confidence_threshold=0.8"
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "abc123-def456-789",
  "message": "Document processing completed successfully in 45.2s",
  "upload_result": {
    "success": true,
    "file_path": "data/uploads/contract.pdf",
    "file_info": {...}
  },
  "ocr_result": {
    "uid": "ocr-abc123",
    "total_pages": 12,
    "processed_pages": 12,
    "ocr_results_path": "data/processed/ocr_results.json"
  },
  "docai_result": {
    "success": true,
    "document": {
      "text": "Complete extracted text...",
      "named_entities": [...],
      "clauses": [...],
      "key_value_pairs": [...]
    }
  },
  "total_processing_time": 45.2,
  "stage_timings": {
    "upload": 1.5,
    "ocr": 32.1,
    "docai": 11.6
  },
  "final_results_path": "data/processed/pipeline_result_abc123-def456-789.json"
}
```

### Pipeline Status

**GET** `/api/v1/pipeline-status/{pipeline_id}`

Get real-time status of a processing pipeline.

**Response:**
```json
{
  "pipeline_id": "abc123-def456-789",
  "current_stage": "ocr_processing",
  "progress_percentage": 65.0,
  "total_stages": 4,
  "completed_stages": 2,
  "start_time": "2025-09-19T10:30:00Z",
  "errors": [],
  "warnings": []
}
```

### Pipeline Results

**GET** `/api/v1/pipeline-results/{pipeline_id}`

Retrieve complete results for a finished pipeline.

### Health Check

**GET** `/api/v1/health`

Check orchestration service health and configuration.

## File Structure

The orchestration system preserves all data in organized directories:

```
data/
├── uploads/              # Original PDF files
├── processed/            # OCR results and pipeline outputs
│   ├── pipeline_result_*.json  # Complete pipeline results
│   └── api_test_result_*.json  # Individual processing results
└── [uid-folders]/        # Per-document processing folders
    ├── metadata.json     # Processing metadata
    ├── images/           # Extracted page images
    └── [filename].json   # OCR results
```

## Pipeline Results Format

Complete pipeline results are saved as JSON files in `data/processed/` with the following structure:

```json
{
  "pipeline_id": "unique-pipeline-id",
  "processing_timestamp": "2025-09-19T10:45:30Z",
  "pipeline_version": "1.0.0",
  
  "original_file": {
    "path": "data/uploads/document.pdf",
    "info": {
      "size": 2048576,
      "pages": 12,
      "created": "2025-09-19T10:30:00Z"
    }
  },
  
  "ocr_processing": {
    "uid": "ocr-unique-id",
    "total_pages": 12,
    "processed_pages": 12,
    "results_path": "path/to/ocr/results.json"
  },
  
  "docai_processing": {
    "document": {
      "text": "Complete extracted text content...",
      "named_entities": [
        {
          "text": "Mumbai High Court",
          "type": "COURT",
          "confidence": 0.95,
          "start_offset": 1234,
          "end_offset": 1249
        }
      ],
      "clauses": [
        {
          "text": "The parties agree to...",
          "type": "AGREEMENT_CLAUSE",
          "confidence": 0.88
        }
      ],
      "key_value_pairs": [
        {
          "key": "Contract Date",
          "value": "2025-09-15",
          "confidence": 0.92
        }
      ]
    }
  },
  
  "performance": {
    "total_processing_time": 45.2,
    "stage_timings": {
      "upload": 1.5,
      "ocr": 32.1,
      "docai": 11.6,
      "saving": 0.1
    }
  },
  
  "extracted_data": {
    "text_content": "Complete text for easy access...",
    "named_entities": [...],
    "clauses": [...],
    "key_value_pairs": [...]
  }
}
```

## Integration with Existing Endpoints

The orchestration router reuses existing endpoints internally:

- **Upload**: Uses `processing_handler.upload_file()`
- **OCR Processing**: Uses `processing_handler.ocr_process()`
- **Document AI**: Uses `doc_ai_router.parse_document()`

This approach:
- ✅ Maintains existing functionality
- ✅ Preserves modular architecture
- ✅ Enables individual endpoint usage
- ✅ Provides unified workflow option

## Error Handling

The pipeline includes comprehensive error handling:

1. **Stage-level errors**: Each stage can fail independently
2. **Graceful degradation**: Continue with available results if one stage fails
3. **Detailed logging**: Full error tracking and warnings
4. **Retry logic**: Built-in retry for transient failures
5. **Status tracking**: Real-time progress and error reporting

## Configuration

Environment variables for orchestration:

```bash
# Required for full functionality
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
DOCAI_PROCESSOR_ID=your-processor-id

# Optional configuration
DATA_ROOT=./data                    # Default: /data
TEMP_GCS_BUCKET=your-temp-bucket   # For DocAI file uploads
DOCAI_LOCATION=us                  # Default: us
DOCAI_CONFIDENCE_THRESHOLD=0.7     # Default: 0.7
```

## Usage Examples

### Simple Processing
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/process-document",
    files={"file": open("contract.pdf", "rb")}
)

result = response.json()
pipeline_id = result["pipeline_id"]
```

### Advanced Processing
```python
response = requests.post(
    "http://localhost:8000/api/v1/process-document",
    files={"file": open("multilingual_doc.pdf", "rb")},
    data={
        "language_hints": "en,hi,mr",
        "confidence_threshold": 0.85,
        "include_raw_response": True,
        "force_reprocess": False
    }
)
```

### Status Monitoring
```python
import time

# Start processing
response = requests.post(...)
pipeline_id = response.json()["pipeline_id"]

# Monitor progress
while True:
    status = requests.get(f"/api/v1/pipeline-status/{pipeline_id}").json()
    print(f"Stage: {status['current_stage']}, Progress: {status['progress_percentage']}%")
    
    if status["progress_percentage"] >= 100:
        break
    time.sleep(5)

# Get final results
results = requests.get(f"/api/v1/pipeline-results/{pipeline_id}").json()
```

## Testing

Run validation tests:
```bash
uv run python test_orchestration.py
```

Start the server:
```bash
uv run uvicorn main:app --reload
```

The orchestration API is now ready for production use with full error handling, progress tracking, and comprehensive result storage.