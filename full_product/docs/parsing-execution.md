# Parsing Execution Guide

This document provides comprehensive instructions for using the text parsing services in the AI backend system.

## Overview

The parsing service provides powerful text processing capabilities including:
- Text cleaning and normalization
- Section parsing and extraction
- Key-value pair extraction using regex patterns
- JSON serialization of parsed documents

## Quick Start

### Prerequisites

```bash
# Install required dependencies
pip install pathlib json re

# Optional: For better Unicode handling
pip install unicodedata
```

### Basic Usage

```python
from services.preprocessing.parsing import LocalTextParser, ParsedDocument

# Initialize with text string
parser = LocalTextParser("Your document text here")

# Or initialize with file path
parser = LocalTextParser("path/to/document.txt")

# Clean the text
cleaned_text = parser.clean_text()

# Parse into sections
sections = parser.parse_sections()

# Extract key-value pairs
patterns = {
    "name": r"Name:\s*(.+)",
    "email": r"Email:\s*([\w.-]+@[\w.-]+)"
}
extracted_data = parser.extract_key_values(patterns)

# Convert to JSON
json_output = parser.to_json()
```

## Detailed Workflow

### 1. Text Input and Initialization

#### From String
```python
text_content = """
INVOICE #12345

Company: Acme Corp
Date: 2023-09-07
Amount: $1,500.00

ITEMS:
- Software License: $1,000
- Support: $500
"""

parser = LocalTextParser(text_content)
```

#### From File
```python
from pathlib import Path

# Various file formats supported
parser = LocalTextParser("document.txt")
parser = LocalTextParser(Path("document.txt"))

# Handles different encodings automatically
# First tries UTF-8, falls back to latin-1
```

### 2. Text Cleaning

The cleaning process includes:
- Normalizing line endings (`\r\n`, `\r` → `\n`)
- Removing excessive whitespace
- Filtering non-ASCII and control characters
- Trimming whitespace from lines

```python
# Before cleaning
messy_text = "  Multiple    spaces\n\n\n\nExcessive   line   breaks  "

parser = LocalTextParser(messy_text)
cleaned = parser.clean_text()

# After cleaning
# "Multiple spaces\n\nExcessive line breaks"
```

#### Customizing Text Cleaning
```python
# The clean_text method can be extended
class CustomTextParser(LocalTextParser):
    def clean_text(self) -> str:
        # Call parent method first
        text = super().clean_text()
        
        # Add custom cleaning rules
        text = text.replace("©", "(c)")  # Replace copyright symbol
        text = re.sub(r'\$(\d+)', r'USD \1', text)  # Format currency
        
        return text
```

### 3. Section Parsing

The parser automatically identifies document sections using various patterns:

#### Supported Section Patterns
- **ALL CAPS headers**: `SECTION TITLE`
- **Numbered sections**: `SECTION 1`, `1. Title`
- **Title Case headers**: `Section Title`
- **Custom patterns**: Configurable via regex

```python
document = """
COMPANY OVERVIEW

Acme Corporation provides software solutions.

SECTION 1: Products

We offer various products including:
- Web applications
- Mobile apps

Financial Information

Revenue: $2M
Employees: 25
"""

parser = LocalTextParser(document)
sections = parser.parse_sections()

# Result:
# {
#     "company_overview": "Acme Corporation provides software solutions.",
#     "section_1": "We offer various products including:\n- Web applications\n- Mobile apps",
#     "financial_information": "Revenue: $2M\nEmployees: 25"
# }
```

#### Custom Section Patterns
```python
# Extend the parser for domain-specific patterns
class ContractParser(LocalTextParser):
    def parse_sections(self):
        # Add contract-specific patterns
        additional_patterns = [
            r'^(WHEREAS\s+.+):?\s*$',  # Legal whereas clauses
            r'^(ARTICLE\s+\d+):?\s*(.*)$',  # Article sections
        ]
        
        # Implement custom parsing logic
        # ... your custom implementation
```

### 4. Key-Value Extraction

Extract structured data using regex patterns:

#### Basic Patterns
```python
# Common extraction patterns
patterns = {
    "invoice_number": r"Invoice\s*#?\s*(\w+)",
    "date": r"Date:\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
    "amount": r"Amount:\s*\$?([\d,]+\.?\d*)",
    "email": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    "phone": r"(\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
    "currency": r"\$?([\d,]+\.?\d*)\s*(USD|EUR|GBP)?",
}

extracted = parser.extract_key_values(patterns)
```

#### Advanced Pattern Examples
```python
# Complex patterns for specific use cases
legal_patterns = {
    "case_number": r"Case\s+No\.?\s*:?\s*(\d{4}-\w+-\d+)",
    "court": r"(?:in\s+the\s+)?(.+?court.+?)(?:\n|$)",
    "parties": r"(.+?)\s+v\.?\s+(.+?)(?:\n|,)",
    "statute": r"(\d+\s+U\.S\.C\.?\s*§?\s*\d+(?:\(\w+\))?)",
}

financial_patterns = {
    "revenue": r"Revenue:?\s*\$?([\d,]+(?:\.\d{2})?)\s*([MBK])?",
    "profit_margin": r"(?:Profit\s+)?Margin:?\s*(\d+(?:\.\d+)?)%?",
    "fiscal_year": r"(?:FY|Fiscal\s+Year):?\s*(\d{4})",
    "quarter": r"Q([1-4])\s*(\d{4})",
}
```

### 5. Data Export and Serialization

#### JSON Export
```python
# Full document export
json_output = parser.to_json()

# Parsed JSON structure:
{
    "sections": {
        "title": "Document content...",
        "summary": "Summary content..."
    },
    "metadata": {
        "source": "document.txt",
        "original_length": 1500,
        "cleaned_length": 1400,
        "sections_count": 5,
        "parser_version": "1.0"
    }
}
```

#### Custom Export Formats
```python
# Create custom export methods
class ExtendedParser(LocalTextParser):
    def to_xml(self) -> str:
        """Export to XML format."""
        sections = self.parse_sections()
        
        xml = "<document>\n"
        for name, content in sections.items():
            xml += f"  <section name='{name}'>\n"
            xml += f"    <content>{content}</content>\n"
            xml += f"  </section>\n"
        xml += "</document>"
        
        return xml
    
    def to_markdown(self) -> str:
        """Export to Markdown format."""
        sections = self.parse_sections()
        
        markdown = ""
        for name, content in sections.items():
            markdown += f"## {name.replace('_', ' ').title()}\n\n"
            markdown += f"{content}\n\n"
        
        return markdown
```

## Advanced Usage Patterns

### 1. Document Type Classification

```python
def classify_document_type(text: str) -> str:
    """Classify document based on content patterns."""
    parser = LocalTextParser(text)
    
    # Define classification patterns
    patterns = {
        "invoice": [r"invoice", r"bill\s+to", r"amount\s+due"],
        "contract": [r"whereas", r"parties", r"agreement"],
        "resume": [r"experience", r"education", r"skills"],
        "legal": [r"court", r"case\s+no", r"plaintiff"],
    }
    
    for doc_type, keywords in patterns.items():
        matches = sum(1 for pattern in keywords 
                     if re.search(pattern, text, re.IGNORECASE))
        if matches >= len(keywords) // 2:  # Majority match
            return doc_type
    
    return "unknown"
```

### 2. Multi-Document Processing

```python
def process_document_batch(file_paths: List[str]) -> Dict[str, dict]:
    """Process multiple documents in batch."""
    results = {}
    
    for file_path in file_paths:
        try:
            parser = LocalTextParser(file_path)
            
            # Standard processing pipeline
            parser.clean_text()
            sections = parser.parse_sections()
            
            # Document-specific patterns
            doc_type = classify_document_type(parser.raw_text)
            patterns = get_patterns_for_type(doc_type)
            extracted = parser.extract_key_values(patterns)
            
            results[file_path] = {
                "type": doc_type,
                "sections": sections,
                "extracted_data": extracted,
                "metadata": parser.to_json()
            }
            
        except Exception as e:
            results[file_path] = {"error": str(e)}
    
    return results
```

### 3. Template-Based Parsing

```python
class TemplateParser:
    """Parse documents using predefined templates."""
    
    def __init__(self):
        self.templates = {
            "invoice": {
                "patterns": {
                    "number": r"Invoice\s*#?\s*(\w+)",
                    "date": r"Date:\s*(.+)",
                    "total": r"Total:\s*\$?([\d,]+\.?\d*)"
                },
                "required_sections": ["billing", "items"]
            },
            "contract": {
                "patterns": {
                    "parties": r"between\s+(.+?)\s+and\s+(.+?)(?:\n|,)",
                    "effective_date": r"effective\s+(.+?)(?:\n|,)",
                    "term": r"term\s+of\s+(.+?)(?:\n|,)"
                },
                "required_sections": ["terms", "conditions"]
            }
        }
    
    def parse_with_template(self, text: str, template_name: str) -> dict:
        """Parse document using specific template."""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = self.templates[template_name]
        parser = LocalTextParser(text)
        
        # Extract using template patterns
        extracted = parser.extract_key_values(template["patterns"])
        
        # Validate required sections
        sections = parser.parse_sections()
        missing_sections = [
            section for section in template["required_sections"]
            if not any(section in name for name in sections.keys())
        ]
        
        return {
            "extracted_data": extracted,
            "sections": sections,
            "validation": {
                "missing_sections": missing_sections,
                "valid": len(missing_sections) == 0
            }
        }
```

## Error Handling and Troubleshooting

### Common Issues and Solutions

#### 1. Encoding Problems
```python
# Handle files with unknown encoding
def safe_text_loading(file_path: str) -> str:
    """Safely load text with encoding detection."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Could not decode file: {file_path}")
```

#### 2. Large File Processing
```python
def process_large_file(file_path: str, chunk_size: int = 1024*1024) -> dict:
    """Process large files in chunks."""
    results = {"sections": {}, "extracted_data": {}}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        chunk_num = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            parser = LocalTextParser(chunk)
            sections = parser.parse_sections()
            
            # Merge results
            for name, content in sections.items():
                section_key = f"{name}_chunk_{chunk_num}"
                results["sections"][section_key] = content
            
            chunk_num += 1
    
    return results
```

#### 3. Regex Pattern Debugging
```python
def debug_patterns(text: str, patterns: dict) -> dict:
    """Debug regex patterns and show matches."""
    debug_info = {}
    
    for name, pattern in patterns.items():
        try:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            debug_info[name] = {
                "pattern": pattern,
                "matches": matches,
                "match_count": len(matches),
                "success": len(matches) > 0
            }
        except re.error as e:
            debug_info[name] = {
                "pattern": pattern,
                "error": str(e),
                "success": False
            }
    
    return debug_info
```

## Performance Optimization

### 1. Caching Strategies
```python
import functools
from typing import Dict, Any

class CachedParser(LocalTextParser):
    """Parser with result caching."""
    
    @functools.lru_cache(maxsize=128)
    def _cached_clean_text(self, text_hash: str) -> str:
        """Cache cleaned text results."""
        return super().clean_text()
    
    @functools.lru_cache(maxsize=128)
    def _cached_parse_sections(self, text_hash: str) -> Dict[str, str]:
        """Cache section parsing results."""
        return super().parse_sections()
    
    def clean_text(self) -> str:
        text_hash = hash(self.raw_text)
        return self._cached_clean_text(text_hash)
    
    def parse_sections(self) -> Dict[str, str]:
        text_hash = hash(self.raw_text)
        return self._cached_parse_sections(text_hash)
```

### 2. Parallel Processing
```python
import concurrent.futures
from typing import List

def parallel_document_processing(file_paths: List[str], max_workers: int = 4) -> Dict[str, dict]:
    """Process multiple documents in parallel."""
    
    def process_single_document(file_path: str) -> tuple:
        try:
            parser = LocalTextParser(file_path)
            sections = parser.parse_sections()
            json_output = parser.to_json()
            return file_path, {"success": True, "sections": sections, "json": json_output}
        except Exception as e:
            return file_path, {"success": False, "error": str(e)}
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_document, file_path): file_path 
            for file_path in file_paths
        }
        
        for future in concurrent.futures.as_completed(future_to_file):
            file_path, result = future.result()
            results[file_path] = result
    
    return results
```

## Integration Examples

### With OCR Pipeline
```python
# Combine with OCR processing
from services.preprocessing.OCR_processing import GoogleVisionOCR

def process_scanned_document(image_path: str) -> dict:
    """Process scanned document: OCR + Parsing."""
    
    # Step 1: Extract text with OCR
    ocr = GoogleVisionOCR.from_env()
    ocr_result = ocr.extract_text(image_path)
    
    # Step 2: Parse extracted text
    parser = LocalTextParser(ocr_result.text)
    sections = parser.parse_sections()
    
    # Step 3: Extract structured data
    patterns = {
        "date": r"Date:\s*(.+)",
        "amount": r"Amount:\s*\$?([\d,]+\.?\d*)",
        "reference": r"Ref(?:erence)?:\s*(.+)"
    }
    extracted = parser.extract_key_values(patterns)
    
    return {
        "ocr_confidence": ocr_result.confidence,
        "extracted_text": ocr_result.text,
        "sections": sections,
        "structured_data": extracted,
        "metadata": {
            "source_image": image_path,
            "processing_date": datetime.now().isoformat()
        }
    }
```

### With FastAPI Service
```python
# Integration with web API
from fastapi import FastAPI, UploadFile
import tempfile

app = FastAPI()

@app.post("/parse-document")
async def parse_uploaded_document(file: UploadFile):
    """Parse uploaded text document."""
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
        content = await file.read()
        tmp.write(content.decode('utf-8'))
        tmp_path = tmp.name
    
    try:
        # Process with parser
        parser = LocalTextParser(tmp_path)
        sections = parser.parse_sections()
        json_output = parser.to_json()
        
        return {
            "filename": file.filename,
            "sections": sections,
            "full_output": json_output
        }
    
    finally:
        # Cleanup
        os.unlink(tmp_path)
```

## Best Practices

1. **Input Validation**: Always validate input files and text before processing
2. **Error Handling**: Implement robust error handling for file operations and regex patterns
3. **Memory Management**: For large documents, consider streaming or chunked processing
4. **Caching**: Cache results for repeated processing of similar documents
5. **Pattern Testing**: Test regex patterns thoroughly with representative data
6. **Performance Monitoring**: Monitor processing time and memory usage for optimization
7. **Documentation**: Document custom patterns and processing logic for maintainability

## Testing

Run the parsing tests to ensure everything works correctly:

```bash
# Run parsing-specific tests
cd tests
python test_parsing.py

# Run all tests
python unit-tests.py parsing

# With coverage
coverage run test_parsing.py
coverage report -m
```

For more information on testing, see the test documentation in `/tests/README.md`.