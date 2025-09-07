# Test Configuration and Documentation

## Running Tests

### Prerequisites
Install test dependencies:
```bash
pip install -r test_requirements.txt
```

### Running All Tests
```bash
# From the tests directory
python unit-tests.py

# Or using the unittest module
python -m unittest discover -s . -p "test_*.py" -v
```

### Running Specific Service Tests
```bash
# OCR processing tests only
python unit-tests.py ocr

# Text parsing tests only  
python unit-tests.py parsing
```

### Running Individual Test Files
```bash
# OCR tests
python test_ocr_processing.py

# Parsing tests
python test_parsing.py
```

## Test Coverage

### OCR Processing Tests (`test_ocr_processing.py`)
- **TestOCRResult**: Tests for OCRResult dataclass
  - Creation with valid data
  - Empty/default values
  
- **TestGoogleVisionOCR**: Tests for GoogleVisionOCR class
  - Initialization (success, failure, defaults)
  - Text extraction from files
  - Text extraction from bytes
  - Error handling (file not found, API errors)
  - Response parsing (full annotation, empty, missing confidence)
  
- **TestGoogleVisionOCRIntegration**: Integration test placeholders

### Text Parsing Tests (`test_parsing.py`)
- **TestParsedDocument**: Tests for ParsedDocument dataclass
  - Creation with valid data
  - Empty data handling
  
- **TestLocalTextParser**: Tests for LocalTextParser class
  - Initialization (string, file path, invalid input)
  - File loading (success, not found, encoding fallback)
  - Text cleaning (basic, line endings, artifacts)
  - Section parsing (basic, numbered, empty removal)
  - Key-value extraction (basic, no matches, invalid regex, case insensitive)
  - JSON conversion (basic, without parsing, unicode)
  
- **TestLocalTextParserIntegration**: Full workflow tests with temporary files

## Test Features

### Mocking
- Google Vision API calls are fully mocked
- File operations use mock_open for controlled testing
- Path operations mocked for cross-platform compatibility

### Error Scenarios
- File not found errors
- Google Cloud API exceptions
- Invalid input handling
- Encoding errors

### Edge Cases
- Empty inputs
- Malformed data
- Unicode characters
- Invalid regex patterns

## Notes

- Google Cloud Vision integration tests are skipped by default (require actual credentials)
- Tests use temporary files for file operation testing
- All external dependencies are mocked for unit tests
- Test runner provides detailed output and summary statistics