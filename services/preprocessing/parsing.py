"""
Local text parsing utilities for document processing.

This module provides utilities for parsing and extracting structured data
from text documents using configurable regex patterns and text processing.
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Union, Any


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """
    Parsed document containing structured sections and metadata.
    
    Attributes:
        sections: Dictionary mapping section names to their content
        metadata: Dictionary containing document metadata and processing info
    """
    sections: Dict[str, str]
    metadata: Dict[str, Any]


class LocalTextParser:
    """
    Local text parser for extracting structured data from documents.
    
    Provides methods for cleaning text, parsing sections, and extracting
    key-value pairs using configurable regex patterns.
    """
    
    def __init__(self, text: Union[str, Path]) -> None:
        """
        Initialize text parser with text content or file path.
        
        Args:
            text: Either raw text string or Path to text file
            
        Example:
            >>> parser = LocalTextParser("Raw text content here")
            >>> # or
            >>> parser = LocalTextParser(Path("document.txt"))
        """
        if isinstance(text, (str, Path)) and Path(text).exists():
            self.raw_text = self.load_text_from_file(str(text))
            self.source = str(text)
        elif isinstance(text, str):
            self.raw_text = text
            self.source = "raw_string"
        else:
            raise ValueError("Input must be either text string or valid file path")
        
        self.cleaned_text = ""
        self.parsed_sections = {}
        
        logger.info(f"Initialized parser with {len(self.raw_text)} characters from {self.source}")
    
    @staticmethod
    def load_text_from_file(path: str) -> str:
        """
        Load text content from a file.
        
        Args:
            path: Path to the text file
            
        Returns:
            Text content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file encoding is unsupported
            
        Example:
            >>> text = LocalTextParser.load_text_from_file("document.txt")
            >>> print(f"Loaded {len(text)} characters")
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        try:
            # Try UTF-8 first, fall back to latin-1 if needed
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode failed for {path}, trying latin-1")
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        logger.info(f"Loaded {len(content)} characters from {path}")
        return content
    
    def clean_text(self) -> str:
        """
        Clean and normalize text content.
        
        Removes extra whitespace, normalizes line endings, and removes
        common artifacts from OCR or document conversion.
        
        Returns:
            Cleaned text string
            
        Example:
            >>> parser = LocalTextParser("  Multiple   spaces\\n\\n\\nText  ")
            >>> cleaned = parser.clean_text()
            >>> print(repr(cleaned))  # "Multiple spaces\\nText"
        """
        text = self.raw_text
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace
        text = re.sub(r' {2,}', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newline
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control chars
        
        # Trim whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        self.cleaned_text = text
        logger.info(f"Text cleaned: {len(self.raw_text)} -> {len(text)} characters")
        
        return text
    
    def parse_sections(self) -> Dict[str, str]:
        """
        Parse text into logical sections using common document patterns.
        
        Identifies sections based on headers, formatting, and content patterns.
        Configurable via regex patterns for different document types.
        
        Returns:
            Dictionary mapping section names to their content
            
        Example:
            >>> parser = LocalTextParser("TITLE\\nContent\\n\\nSECTION 1\\nMore content")
            >>> sections = parser.parse_sections()
            >>> print(sections.keys())  # dict_keys(['title', 'section_1'])
        """
        if not self.cleaned_text:
            self.clean_text()
        
        text = self.cleaned_text
        sections = {}
        
        # Common section header patterns
        header_patterns = [
            r'^([A-Z][A-Z\s]{2,}):?\s*$',  # ALL CAPS headers
            r'^(SECTION\s+\d+):?\s*(.*)$',  # Numbered sections
            r'^(\d+\.?\s+[A-Z][A-Za-z\s]+):?\s*$',  # Numbered titles
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):?\s*$',  # Title Case headers
        ]
        
        current_section = "content"
        current_content = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                current_content.append('')
                continue
            
            # Check if line matches any header pattern
            is_header = False
            for pattern in header_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    # Start new section
                    current_section = match.group(1).lower().replace(' ', '_')
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Save final section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # Remove empty sections
        sections = {k: v for k, v in sections.items() if v.strip()}
        
        self.parsed_sections = sections
        logger.info(f"Parsed {len(sections)} sections: {list(sections.keys())}")
        
        return sections
    
    def extract_key_values(self, patterns: Dict[str, str]) -> Dict[str, str]:
        """
        Extract key-value pairs using custom regex patterns.
        
        Args:
            patterns: Dictionary mapping field names to regex patterns
            
        Returns:
            Dictionary of extracted key-value pairs
            
        Example:
            >>> text = "Name: John Doe\\nEmail: john@example.com\\nPhone: 555-1234"
            >>> parser = LocalTextParser(text)
            >>> patterns = {
            ...     "name": r"Name:\s*(.+)",
            ...     "email": r"Email:\s*([\\w.-]+@[\\w.-]+)",
            ...     "phone": r"Phone:\s*([\\d-]+)"
            ... }
            >>> values = parser.extract_key_values(patterns)
            >>> print(values)  # {'name': 'John Doe', 'email': 'john@example.com', ...}
        """
        if not self.cleaned_text:
            self.clean_text()
        
        text = self.cleaned_text
        extracted = {}
        
        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Use first capture group if available, otherwise full match
                    value = match.group(1) if match.groups() else match.group(0)
                    extracted[field_name] = value.strip()
                    logger.debug(f"Extracted {field_name}: {value.strip()}")
                else:
                    logger.debug(f"No match found for pattern '{field_name}': {pattern}")
            except re.error as e:
                logger.warning(f"Invalid regex pattern for '{field_name}': {e}")
        
        logger.info(f"Extracted {len(extracted)} key-value pairs")
        return extracted
    
    def to_json(self) -> str:
        """
        Convert parsed document to JSON format.
        
        Returns:
            JSON string representation of the parsed document
            
        Example:
            >>> parser = LocalTextParser("TITLE\\nContent here")
            >>> parser.parse_sections()
            >>> json_output = parser.to_json()
            >>> print(json_output)  # {"sections": {...}, "metadata": {...}}
        """
        # Ensure sections are parsed
        if not self.parsed_sections:
            self.parse_sections()
        
        # Create ParsedDocument with metadata
        metadata = {
            "source": self.source,
            "original_length": len(self.raw_text),
            "cleaned_length": len(self.cleaned_text),
            "sections_count": len(self.parsed_sections),
            "parser_version": "1.0"
        }
        
        parsed_doc = ParsedDocument(
            sections=self.parsed_sections,
            metadata=metadata
        )
        
        # Convert to JSON
        return json.dumps(asdict(parsed_doc), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    """
    Demo usage of LocalTextParser.
    """
    # Sample document text
    sample_text = """
    COMPANY OVERVIEW
    
    Acme Corporation is a leading provider of innovative solutions.
    Founded in 2020, we serve customers worldwide.
    
    CONTACT INFORMATION
    
    Name: John Smith
    Email: john.smith@acme.com
    Phone: (555) 123-4567
    Address: 123 Main St, Anytown, USA
    
    SECTION 1: Products
    
    We offer a range of high-quality products including:
    - Software solutions
    - Hardware components
    - Consulting services
    
    FINANCIAL DATA
    
    Revenue: $1.2M
    Employees: 25
    """
    
    try:
        # Initialize parser
        parser = LocalTextParser(sample_text)
        
        # Clean text
        cleaned = parser.clean_text()
        print(f"Cleaned text length: {len(cleaned)} characters")
        
        # Parse sections
        sections = parser.parse_sections()
        print(f"\\nParsed {len(sections)} sections:")
        for section_name in sections.keys():
            print(f"  - {section_name}")
        
        # Extract key-value pairs
        contact_patterns = {
            "name": r"Name:\s*(.+)",
            "email": r"Email:\s*([\w.-]+@[\w.-]+)",
            "phone": r"Phone:\s*([\(\)\d\s-]+)",
            "revenue": r"Revenue:\s*(\$[\d.]+[MK]?)"
        }
        
        extracted = parser.extract_key_values(contact_patterns)
        print(f"\\nExtracted {len(extracted)} key-value pairs:")
        for key, value in extracted.items():
            print(f"  {key}: {value}")
        
        # Convert to JSON
        json_output = parser.to_json()
        print(f"\\nJSON output length: {len(json_output)} characters")
        print("\\nFirst 200 characters of JSON:")
        print(json_output[:200] + "..." if len(json_output) > 200 else json_output)
        
        print("\\nLocalTextParser demo completed successfully!")
        
    except Exception as e:
        print(f"Demo failed: {e}")
