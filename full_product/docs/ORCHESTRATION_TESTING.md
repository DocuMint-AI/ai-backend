# Orchestration Testing Guide

This document provides comprehensive testing commands to validate the entire AI backend orchestration system with the new user session structure.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Validation](#quick-validation)
3. [Comprehensive Testing](#comprehensive-testing)
4. [User Session Structure Validation](#user-session-structure-validation)
5. [API Endpoint Testing](#api-endpoint-testing)
6. [File Processing Validation](#file-processing-validation)
7. [Integration Testing](#integration-testing)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Environment Setup
```powershell
# Ensure you're in the project root
cd C:\Users\meher\Documents\Projects\ai-backend

# Verify virtual environment is active
uv --version

# Check required files exist
Test-Path "data\uploads\testing-ocr-pdf-1.pdf"
Test-Path "tests\test_complete_orchestration.py"
Test-Path "tests\validate_orchestration.py"
Test-Path "scripts\quick_test_commands.ps1"
```

### Environment Variables
```powershell
# Verify required environment variables
echo "USERNAME: $env:USERNAME"
echo "GOOGLE_CLOUD_PROJECT_ID: $env:GOOGLE_CLOUD_PROJECT_ID"
echo "GOOGLE_APPLICATION_CREDENTIALS: $env:GOOGLE_APPLICATION_CREDENTIALS"
```

## Quick Validation

### 1. Run Basic Orchestration Test
```powershell
# Run the comprehensive test suite
uv run python tests/test_complete_orchestration.py

# Expected: 14+ tests passed, user session folders created
```

### 2. Verify User Session Structure
```powershell
# Check created folders follow {username-UID} format
Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer } | Sort-Object CreationTime -Descending | Select-Object Name, CreationTime -First 5
```

### 3. Quick Health Check
```powershell
# Test API endpoints
uv run python -c "
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
response = client.get('/api/v1/health')
print(f'Health Check: {response.status_code} - {response.json()}')"
```

## Comprehensive Testing

### 1. Full Test Suite with Integration
```powershell
# Run all tests including integration mode
uv run python tests/test_complete_orchestration.py --integration

# Expected: Core functionality 93%+ success rate
# Note: DocAI may fail due to configuration, but core structure works
```

### 2. Manual PDF Processing Test
```powershell
# Test direct PDF processing
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from services.util_services import PDFToImageConverter
from services.project_utils import get_username_from_env

# Initialize converter
username = get_username_from_env()
converter = PDFToImageConverter(data_root='./data', username=username)

# Process PDF
pdf_path = 'data/uploads/testing-ocr-pdf-1.pdf'
uid, images, metadata = converter.convert_pdf_to_images(pdf_path)

print(f'✅ Processed PDF:')
print(f'   Username: {username}')
print(f'   UID: {uid}')
print(f'   Images: {len(images)}')
print(f'   User Session Path: {metadata[\"output_info\"][\"folder_path\"]}')
"
```

### 3. User Session Utilities Test
```powershell
# Test session utility functions
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from services.project_utils import (
    get_username_from_env,
    generate_user_uid,
    get_user_session_structure,
    get_gcs_paths
)

# Test utilities
username = get_username_from_env()
uid = generate_user_uid('test_document.pdf')
session = get_user_session_structure('test_document.pdf', username, uid)
gcs_paths = get_gcs_paths('test-bucket', session['user_session_id'])

print(f'✅ User Session Utilities:')
print(f'   Username: {username}')
print(f'   Generated UID: {uid}')
print(f'   Session ID: {session[\"user_session_id\"]}')
print(f'   Base Path: {session[\"base_path\"]}')
print(f'   GCS Base: {gcs_paths[\"base_uri\"]}')
"
```

## User Session Structure Validation

### 1. Verify Folder Structure
```powershell
# Get the newest user session folder
$newest_folder = Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer -and $_.Name -match "^.*-.*$" } | Sort-Object CreationTime -Descending | Select-Object -First 1

if ($newest_folder) {
    echo "📁 Newest User Session Folder: $($newest_folder.Name)"
    echo "📊 Structure:"
    Get-ChildItem $newest_folder.FullName | Select-Object Name, PSIsContainer | Format-Table
    
    echo "📋 Contents Summary:"
    Get-ChildItem $newest_folder.FullName -Recurse | Group-Object Extension | Select-Object Name, Count | Sort-Object Count -Descending
} else {
    echo "❌ No user session folders found"
}
```

### 2. Validate Naming Convention
```powershell
# Check folder naming follows {username-UID} pattern
$folders = Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer }
foreach ($folder in $folders) {
    $name = $folder.Name
    if ($name -match "^[a-zA-Z0-9_]+-[a-zA-Z0-9_-]+$") {
        echo "✅ Valid format: $name"
    } else {
        echo "⚠️  Invalid format: $name"
    }
}
```

### 3. Check Subdirectory Structure
```powershell
# Verify required subdirectories exist
$expected_dirs = @("artifacts", "uploads", "pipeline", "metadata", "diagnostics")
$user_folders = Get-ChildItem "data\processed" | Where-Object { $_.PSIsContainer -and $_.Name -match "^.*-.*$" }

foreach ($folder in $user_folders) {
    echo "📁 Checking: $($folder.Name)"
    foreach ($dir in $expected_dirs) {
        $dir_path = Join-Path $folder.FullName $dir
        if (Test-Path $dir_path) {
            echo "  ✅ $dir"
        } else {
            echo "  ❌ $dir (missing)"
        }
    }
    echo ""
}
```

## API Endpoint Testing

### 1. Health Endpoint
```powershell
# Test health endpoint
uv run python -c "
from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)
response = client.get('/api/v1/health')
print(f'Health Status: {response.status_code}')
print(f'Response: {json.dumps(response.json(), indent=2)}')
"
```

### 2. Document Processing Endpoint (Mock)
```powershell
# Test document processing endpoint with test file
uv run python -c "
from fastapi.testclient import TestClient
from main import app
import json
from pathlib import Path

client = TestClient(app)
pdf_path = Path('data/uploads/testing-ocr-pdf-1.pdf')

if pdf_path.exists():
    with open(pdf_path, 'rb') as f:
        files = {'file': ('testing-ocr-pdf-1.pdf', f, 'application/pdf')}
        data = {
            'language_hints': 'en',
            'confidence_threshold': 0.7,
            'force_reprocess': True
        }
        response = client.post('/api/v1/process-document', files=files, data=data)
    
    print(f'Document Processing Status: {response.status_code}')
    if response.status_code == 200:
        result = response.json()
        print(f'Success: {result.get(\"success\", False)}')
        print(f'Pipeline ID: {result.get(\"pipeline_id\", \"N/A\")}')
        print(f'Processing Time: {result.get(\"total_processing_time\", 0):.2f}s')
        if 'final_results_path' in result:
            print(f'Results Path: {result[\"final_results_path\"]}')
    else:
        print(f'Error: {response.text}')
else:
    print('❌ Test PDF file not found')
"
```

### 3. Pipeline Status Check
```powershell
# Test pipeline status endpoint
uv run python -c "
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
# Test with a dummy pipeline ID
response = client.get('/api/v1/pipeline-status/test-id')
print(f'Pipeline Status Check: {response.status_code}')
# 404 is expected for non-existent pipeline
print('✅ Endpoint accessible' if response.status_code == 404 else '❌ Unexpected response')
"
```

## File Processing Validation

### 1. PDF to Images Conversion
```powershell
# Test PDF conversion with user session structure
uv run python scripts/test_vision_to_docai_simple.py

# Check if artifacts were created in user session structure
$newest_artifacts = Get-ChildItem "data\processed" -Recurse -Directory | Where-Object { $_.Name -eq "vision_to_docai" } | Sort-Object CreationTime -Descending | Select-Object -First 1

if ($newest_artifacts) {
    echo "✅ Vision-to-DocAI artifacts found: $($newest_artifacts.FullName)"
    Get-ChildItem $newest_artifacts.FullName | Select-Object Name, Length
} else {
    echo "❌ No vision-to-docai artifacts found in user session structure"
}
```

### 2. MVP Test Scripts
```powershell
# Test MVP processing scripts
echo "🔄 Testing MVP Scripts..."

# PowerShell MVP script
if (Test-Path "scripts\mvp_run.ps1") {
    echo "Testing PowerShell MVP script..."
    # Note: This creates its own user session
    # .\scripts\mvp_run.ps1
    echo "✅ MVP PowerShell script exists"
}

# Check if MVP artifacts use user session structure
$mvp_artifacts = Get-ChildItem "data\processed" -Recurse -Directory | Where-Object { $_.Name -eq "mvp" }
if ($mvp_artifacts) {
    echo "✅ MVP artifacts found in user session structure"
    $mvp_artifacts | ForEach-Object { echo "  📁 $($_.Parent.Name)" }
} else {
    echo "⚠️  No MVP artifacts found (run MVP scripts to generate)"
}
```

### 3. Metadata Validation
```powershell
# Check metadata files in user sessions
$metadata_files = Get-ChildItem "data\processed" -Recurse -Filter "metadata.json"
echo "📊 Found $($metadata_files.Count) metadata files:"

foreach ($file in $metadata_files | Select-Object -First 3) {
    echo "📄 $($file.FullName)"
    $content = Get-Content $file.FullName | ConvertFrom-Json
    echo "  UID: $($content.uid)"
    echo "  Processing Method: $($content.processing_info.processing_method)"
    echo "  Success Rate: $($content.processing_info.success_rate)%"
    echo ""
}
```

## Integration Testing

### 1. End-to-End Pipeline Test
```powershell
# Run integration test
echo "🔗 Running End-to-End Integration Test..."
uv run python tests/test_complete_orchestration.py --integration

# Capture results
if ($LASTEXITCODE -eq 0) {
    echo "✅ Integration test passed"
} else {
    echo "⚠️  Integration test had issues (check DocAI configuration)"
}
```

### 2. Multiple Document Processing
```powershell
# Test processing multiple documents to verify separate user sessions
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from services.project_utils import get_user_session_structure
import time

# Simulate processing multiple documents
documents = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
sessions = []

for doc in documents:
    session = get_user_session_structure(doc)
    sessions.append(session['user_session_id'])
    time.sleep(0.1)  # Ensure different timestamps

print('📄 Multiple Document Sessions:')
for i, session_id in enumerate(sessions):
    print(f'  {documents[i]} → {session_id}')

# Verify all sessions are unique
unique_sessions = set(sessions)
print(f'✅ Unique sessions: {len(unique_sessions)}/{len(sessions)}')
"
```

### 3. GCS Path Validation
```powershell
# Test GCS path generation
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from services.project_utils import get_gcs_paths, get_username_from_env, generate_user_uid

username = get_username_from_env()
uid = generate_user_uid('test.pdf')
user_session_id = f'{username}-{uid}'

gcs_paths = get_gcs_paths('test-bucket', user_session_id)

print('🌐 GCS Path Structure:')
for key, path in gcs_paths.items():
    print(f'  {key}: {path}')
"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. No User Session Folders Created
```powershell
# Check permissions
Test-Path "data\processed" -PathType Container
if (-not (Test-Path "data\processed")) {
    New-Item -Path "data\processed" -ItemType Directory -Force
    echo "✅ Created data\processed directory"
}

# Check username resolution
uv run python -c "
from services.project_utils import get_username_from_env
print(f'Username: {get_username_from_env()}')
"
```

#### 2. Import Errors
```powershell
# Verify Python path and imports
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    from services.project_utils import get_user_session_structure
    print('✅ project_utils import successful')
except ImportError as e:
    print(f'❌ Import error: {e}')

try:
    from services.util_services import PDFToImageConverter
    print('✅ util_services import successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
"
```

#### 3. PDF Processing Issues
```powershell
# Check PDF file and dependencies
Test-Path "data\uploads\testing-ocr-pdf-1.pdf"

uv run python -c "
try:
    import fitz
    print('✅ PyMuPDF available')
except ImportError:
    print('❌ PyMuPDF not available')
    
try:
    from PIL import Image
    print('✅ Pillow available')
except ImportError:
    print('❌ Pillow not available')
"
```

#### 4. API Endpoint Issues
```powershell
# Test FastAPI setup
uv run python -c "
try:
    from main import app
    print('✅ FastAPI app loads successfully')
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    print('✅ Test client created successfully')
except Exception as e:
    print(f'❌ FastAPI setup error: {e}')
"
```

### Quick Commands Script

#### Use Pre-made Command Script
```powershell
# Run the quick test commands script
.\scripts\quick_test_commands.ps1

# Or source it for individual commands
. .\scripts\quick_test_commands.ps1
```

### Cleanup Commands

#### Reset Test Environment
```powershell
# Clean up test artifacts (be careful!)
# Remove-Item "data\processed\test_user-*" -Recurse -Force
# Remove-Item "data\processed\*-metadata_*" -Recurse -Force

# Better: Just list what would be cleaned
Get-ChildItem "data\processed" | Where-Object { $_.Name -like "test_user-*" -or $_.Name -like "*-metadata_*" } | Select-Object Name, CreationTime
```

#### Generate Fresh Test Data
```powershell
# Run a fresh test to generate new data
uv run python tests/test_complete_orchestration.py

# Verify new structure
Get-ChildItem "data\processed" | Sort-Object CreationTime -Descending | Select-Object Name, CreationTime -First 3
```

## Success Indicators

When the orchestration system is working correctly, you should see:

1. ✅ **User Session Folders**: Created with format `{username-UID}`
2. ✅ **Proper Structure**: Contains `artifacts/`, `uploads/`, `pipeline/`, `metadata/`, `diagnostics/`
3. ✅ **File Processing**: PDF converted to images and stored in user session
4. ✅ **Metadata**: Generated and stored in appropriate locations
5. ✅ **API Endpoints**: Health check and main endpoints respond correctly
6. ✅ **Test Results**: 14+ tests passing (93%+ success rate)

## Test Report Generation

```powershell
# Generate comprehensive test report
uv run python tests/test_complete_orchestration.py --integration 2>&1 | Tee-Object -FilePath "orchestration_test_results.log"

# Run validation script for quick overview
uv run python tests/validate_orchestration.py

echo "📋 Test report saved to: orchestration_test_results.log"
echo "📊 Test artifacts in: tests/orchestration_test_report.json"
echo "✅ Validation report in: docs/validation_report.json"
```

---

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Run the validation script: `uv run python tests/validate_orchestration.py`
3. Use quick commands: `scripts/quick_test_commands.ps1`
4. Review the test logs in `orchestration_test_results.log`
5. Examine the detailed test report in `tests/orchestration_test_report.json`
6. Check the validation report in `docs/validation_report.json`
7. Verify environment variables and dependencies are properly configured