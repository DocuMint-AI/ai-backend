# Test Configuration and Documentation

## Overview

This directory contains all tests for the AI Backend Document Processing API. Tests are organized by functionality and include unit tests, integration tests, and validation scripts.

## Running Tests

### Prerequisites
Install test dependencies:
```bash
# Using UV (recommended)
cd tests/
uv pip install -r test_requirements.txt

# Or using pip
pip install -r test_requirements.txt
```

### Running All Tests (Recommended)
```bash
# From the tests directory
python run_all_tests.py

# Or with pattern matching
python run_all_tests.py --pattern ocr
python run_all_tests.py --pattern docai
```

### List Available Tests
```bash
python run_all_tests.py --list
```

### Running Individual Test Files
```bash
# Unit tests for OCR processing
python test_ocr_processing.py

# Unit tests for text parsing
python test_parsing.py

# API endpoint tests
python test_api_endpoints.py

# Orchestration tests
python test_orchestration.py

# DocAI integration tests
python test_docai_integration.py
```

### Legacy Test Runners
```bash
# Original unit test runner
python unit-tests.py

# Comprehensive test runner (deprecated - use run_all_tests.py)
python run_tests.py

# Integration test runner
python run_integration_test.py
```

## Test Categories

### Unit Tests
- **test_ocr_processing.py**: Tests for GoogleVisionOCR class
- **test_parsing.py**: Tests for LocalTextParser class  
- **test_ocr_structure.py**: OCR structure tests without Google Cloud dependencies
- **unit-tests.py**: Original unified unit test runner

### API Tests
- **test_api_endpoints.py**: FastAPI endpoint integration tests
- **test_orchestration.py**: Orchestration router validation tests
- **test_docai_endpoints.py**: Document AI endpoint tests
- **test_docai_schema.py**: DocAI schema validation tests

### Integration Tests
- **test_docai_integration.py**: Complete DocAI pipeline integration tests
- **test_pdf_to_docai.py**: PDF to DocAI processing tests
- **test_vision_connection.py**: Google Vision API connection tests
- **run_integration_test.py**: Integration test runner

### Validation Tests
- **test_final_validation.py**: Output format validation
- **final_status_report.py**: Comprehensive status report and testing

### Test Utilities
- **create_test_image.py**: Utility for creating test images
- **run_all_tests.py**: Unified test runner (NEW - recommended)
- **run_tests.py**: Comprehensive test runner (legacy)

## Test Features

### Automated Test Discovery
The `run_all_tests.py` script automatically discovers and runs all test files using pattern matching:
- `test_*.py` - Standard test files
- `*_test.py` - Alternative naming convention
- `unit-tests.py` - Legacy unit test runner

### Path Management
All tests now use proper import paths:
```python
# Project root path setup (from tests/ directory)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

### Mocking and Isolation
- Google Vision API calls are fully mocked for unit tests
- File operations use mock_open for controlled testing
- External dependencies are isolated for reliable testing

### Error Handling
- Comprehensive error catching and reporting
- Timeout protection for long-running tests
- Graceful handling of missing dependencies

## Test Environment Setup

### Environment Variables Required
```bash
# For integration tests with real APIs
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
DOCAI_PROCESSOR_ID=your-processor-id

# Optional configuration
DATA_ROOT=./data
DOCAI_LOCATION=us
```

### Mock vs Real Testing
- **Unit tests**: Use mocked Google Cloud APIs (no credentials needed)
- **Integration tests**: Use real APIs (credentials required)
- **API tests**: Use FastAPI TestClient (no external dependencies)

## Test Coverage

### OCR Processing (`test_ocr_processing.py`)
- GoogleVisionOCR initialization and configuration
- Text extraction from images and bytes
- Error handling for API failures
- Response parsing and validation
- DocAI-compatible output format

### Text Parsing (`test_parsing.py`)
- ParsedDocument dataclass validation
- LocalTextParser text cleaning and processing
- Section parsing and key-value extraction
- File loading and encoding handling
- JSON conversion and unicode support

### API Endpoints (`test_api_endpoints.py`)
- FastAPI route registration and functionality
- File upload and validation
- OCR processing pipeline
- Result retrieval and status checking
- Error response handling

### Orchestration (`test_orchestration.py`)
- Pipeline orchestration workflow
- Status tracking and monitoring
- Result consolidation and storage
- Error handling and graceful degradation
- Performance metrics and timing

### Document AI (`test_docai_*.py`)
- DocAI client initialization and authentication
- Document parsing and entity extraction
- Schema validation and response formatting
- Batch processing and concurrency
- Integration with existing pipeline

## Running Tests in CI/CD

The test suite is designed for automated execution:

```bash
# Quick validation (unit tests only)
python run_all_tests.py --pattern "test_ocr test_parsing unit"

# Full test suite (requires credentials)
python run_all_tests.py

# API tests only
python run_all_tests.py --pattern "api endpoints orchestration"
```

## Test Data Requirements

### Test Files
- PDF files in `../data/test-files/` for integration tests
- Sample JSON responses for mocked API calls
- Test images for OCR processing validation

### Temporary Data
- Tests create temporary files in system temp directory
- All temporary files are automatically cleaned up
- No persistent data modification during testing

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure project root is in Python path
2. **Missing Dependencies**: Install test requirements
3. **API Failures**: Check Google Cloud credentials for integration tests
4. **Path Issues**: Run tests from tests/ directory or use run_all_tests.py

### Debug Mode
```bash
# Run with verbose output
python -v test_file.py

# Run specific test with debugging
python -m pdb test_file.py
```

## Contributing

When adding new tests:
1. Follow naming convention: `test_*.py`
2. Use proper import paths (see existing tests)
3. Include both unit and integration test versions
4. Add documentation for test purpose and coverage
5. Update this README if adding new test categories