# Google Vision API Setup and Verification

This script (`scripts/setup_and_verify_vision.py`) provides comprehensive setup and verification for Google Vision API integration in the document processing pipeline.

## Usage

```bash
# Run the setup and verification script
python scripts/setup_and_verify_vision.py

# Or from project root
cd ai-backend
python scripts/setup_and_verify_vision.py
```

## What it does

The script performs the following checks in sequence:

### 1. Environment Validation ✅
- Checks if a virtual environment is active
- Validates that Python can install packages
- Provides recommendations for virtual environment usage

### 2. Dependencies Installation ✅
- Verifies required packages:
  - `google-cloud-vision` (Google Cloud Vision API)
  - `google-cloud-storage` (Google Cloud Storage)
  - `PyMuPDF` (PDF processing)
  - `pdfplumber` (PDF text extraction)
  - `pypdf` (PDF manipulation)
- Automatically installs missing packages
- Verifies successful installation

### 3. Credentials Check ✅
- Confirms `data/.cheetah/gcloud/vision-credentials.json` exists
- Validates service account key format
- Sets `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Provides clear error messages for missing credentials

### 4. Vision Client Initialization ✅
- Tests Google Cloud Vision client creation
- Validates authentication setup
- Confirms API client is ready for use

### 5. API Connectivity Test ✅
- Performs minimal Vision API call
- Verifies authentication and network connectivity
- Tests actual Google Cloud service interaction

### 6. Final Report ✅
- Provides clear summary of all checks
- Shows success/failure status for each component
- Gives actionable next steps

## Exit Codes

- **0**: All checks passed successfully - Vision API ready to use
- **1**: One or more checks failed - review error messages

## Expected Output (Success)

```
🔧 Google Vision API Setup and Verification
============================================================
STEP 1: Environment Validation
============================================================
✅ Environment: Virtual environment active: ai-backend-env

============================================================
STEP 2: Dependencies Installation
============================================================
✅ Package Check: google-cloud-vision - already installed
✅ Package Check: google-cloud-storage - already installed
✅ Package Check: PyMuPDF - already installed
✅ Package Check: pdfplumber - already installed
✅ Package Check: pypdf - already installed
✅ Dependencies: All required packages available

============================================================
STEP 3: Credentials Check
============================================================
✅ Credentials File: Found at data/.cheetah/gcloud/vision-credentials.json
✅ Credentials Format: Valid service account key format
✅ Environment Variable: GOOGLE_APPLICATION_CREDENTIALS correctly set

============================================================
STEP 4: Vision Client Initialization
============================================================
✅ Vision Client: Successfully initialized

============================================================
STEP 5: Sanity Test Call
============================================================
✅ Test Call: Successfully connected to Vision API

============================================================
FINAL REPORT
============================================================
✅ Environment: OK
✅ Dependencies: OK
✅ Credentials: OK
✅ Vision Client: OK
✅ Test Call: OK
============================================================
🎉 ALL CHECKS PASSED! Google Vision API is ready to use.

You can now:
   • Run OCR processing scripts
   • Use the document processing pipeline
   • Process PDFs with Vision API
```

## Troubleshooting

### Common Issues

1. **Missing Credentials**
   ```
   ❌ Credentials File: File not found: data/.cheetah/gcloud/vision-credentials.json
   ```
   **Solution**: Place your Google Cloud service account key at the specified path.

2. **Authentication Errors**
   ```
   ❌ Test Call: API call failed: 403 Forbidden
   ```
   **Solution**: 
   - Ensure Vision API is enabled in your Google Cloud project
   - Verify service account has Vision API permissions
   - Check that billing is enabled

3. **Network Connectivity**
   ```
   ❌ Test Call: API call failed: Network connection error
   ```
   **Solution**:
   - Check internet connection
   - Verify firewall settings allow Google Cloud API access

4. **Package Installation Issues**
   ```
   ❌ Installation: Failed to install missing packages
   ```
   **Solution**:
   - Ensure you have write permissions to Python's site-packages
   - Consider using a virtual environment
   - Try manual installation: `pip install google-cloud-vision`

### Prerequisites

Before running this script, ensure you have:

1. **Google Cloud Project** with Vision API enabled
2. **Service Account Key** with Vision API permissions
3. **Internet Connection** for API testing
4. **Python 3.8+** with pip installed

### Manual Setup (Alternative)

If the automated script fails, you can set up manually:

```bash
# Install dependencies
pip install google-cloud-vision google-cloud-storage PyMuPDF pdfplumber pypdf

# Set environment variable (Windows)
set GOOGLE_APPLICATION_CREDENTIALS=data\.cheetah\gcloud\vision-credentials.json

# Set environment variable (Linux/Mac)
export GOOGLE_APPLICATION_CREDENTIALS=data/.cheetah/gcloud/vision-credentials.json

# Test import
python -c "from google.cloud import vision; print('Vision API ready!')"
```

## Integration with Pipeline

Once all checks pass, you can use the Vision API with:

- **OCR Processing**: `services/preprocessing/ocr_processing.py`
- **Document Pipeline**: `routers/orchestration_router.py`
- **Test Scripts**: `scripts/test_single_orchestration.py`

The script ensures all dependencies and credentials are properly configured for seamless integration with the document processing pipeline.