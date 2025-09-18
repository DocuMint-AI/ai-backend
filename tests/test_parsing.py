"""
Unit tests for text parsing module.

Tests cover ParsedDocument dataclass and LocalTextParser class functionality
including text cleaning, section parsing, and key-value extraction.
"""

import os
import sys
import unittest
from unittest.mock import patch, mock_open, Mock
from pathlib import Path
import tempfile
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Add services directory to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'preprocessing'))

# Import the modules to test
from parsing import ParsedDocument, LocalTextParser


class TestParsedDocument(unittest.TestCase):
    """Test cases for ParsedDocument dataclass."""
    
    def test_parsed_document_creation(self):
        """Test ParsedDocument dataclass creation with valid data."""
        sections = {
            "title": "Document Title",
            "content": "Main content here",
            "conclusion": "Final thoughts"
        }
        metadata = {
            "source": "test_document.txt",
            "length": 100,
            "sections_count": 3
        }
        
        doc = ParsedDocument(sections=sections, metadata=metadata)
        
        self.assertEqual(doc.sections, sections)
        self.assertEqual(doc.metadata, metadata)
        self.assertEqual(len(doc.sections), 3)
        self.assertEqual(doc.metadata["source"], "test_document.txt")
    
    def test_parsed_document_empty(self):
        """Test ParsedDocument with empty data."""
        doc = ParsedDocument(sections={}, metadata={})
        
        self.assertEqual(doc.sections, {})
        self.assertEqual(doc.metadata, {})


class TestLocalTextParser(unittest.TestCase):
    """Test cases for LocalTextParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_text = """
        DOCUMENT TITLE
        
        This is the main content of the document.
        It contains multiple paragraphs and sections.
        
        SECTION 1: Introduction
        
        This is the introduction section.
        It provides background information.
        
        CONTACT INFORMATION
        
        Name: John Doe
        Email: john.doe@example.com
        Phone: (555) 123-4567
        
        SECTION 2: Details
        
        More detailed information here.
        Revenue: $1.5M
        Employees: 50
        """
        
        self.simple_text = "Simple text content"
        
        self.messy_text = """
        
        
        Multiple    spaces   and    excessive
        
        
        
        line breaks.    Needs   cleaning.
        
        
        """
    
    def test_initialization_with_string(self):
        """Test LocalTextParser initialization with string input."""
        parser = LocalTextParser(self.sample_text)
        
        self.assertEqual(parser.raw_text, self.sample_text)
        self.assertEqual(parser.source, "raw_string")
        self.assertEqual(parser.cleaned_text, "")
        self.assertEqual(parser.parsed_sections, {})
    
    @patch('parsing.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_initialization_with_file_path(self, mock_file, mock_exists):
        """Test LocalTextParser initialization with file path."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = self.sample_text
        
        test_path = Path("test_document.txt")
        parser = LocalTextParser(test_path)
        
        self.assertEqual(parser.raw_text, self.sample_text)
        self.assertEqual(parser.source, str(test_path))
        mock_file.assert_called_once_with(test_path, 'r', encoding='utf-8')
    
    def test_initialization_with_invalid_input(self):
        """Test LocalTextParser initialization with invalid input."""
        with self.assertRaises(ValueError):
            LocalTextParser(123)  # Invalid type
    
    @patch('parsing.Path.exists')
    def test_initialization_with_nonexistent_file(self, mock_exists):
        """Test initialization with non-existent file path."""
        mock_exists.return_value = False
        
        with self.assertRaises(ValueError):
            LocalTextParser("nonexistent.txt")
    
    def test_load_text_from_file_success(self):
        """Test successful text loading from file."""
        with patch('builtins.open', mock_open(read_data=self.sample_text)):
            with patch('parsing.Path.exists', return_value=True):
                text = LocalTextParser.load_text_from_file("test.txt")
                self.assertEqual(text, self.sample_text)
    
    def test_load_text_from_file_not_found(self):
        """Test load_text_from_file with non-existent file."""
        with patch('parsing.Path.exists', return_value=False):
            with self.assertRaises(FileNotFoundError):
                LocalTextParser.load_text_from_file("nonexistent.txt")
    
    @patch('parsing.Path.exists')
    @patch('builtins.open')
    def test_load_text_from_file_encoding_fallback(self, mock_open_func, mock_exists):
        """Test load_text_from_file with encoding fallback."""
        mock_exists.return_value = True
        
        # Mock UTF-8 failure and latin-1 success
        utf8_mock = mock_open(read_data=self.sample_text)
        utf8_mock.return_value.read.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        
        latin1_mock = mock_open(read_data=self.sample_text)
        
        mock_open_func.side_effect = [utf8_mock.return_value, latin1_mock.return_value]
        
        text = LocalTextParser.load_text_from_file("test.txt")
        self.assertEqual(text, self.sample_text)
        self.assertEqual(mock_open_func.call_count, 2)
    
    def test_clean_text_basic(self):
        """Test basic text cleaning functionality."""
        parser = LocalTextParser(self.messy_text)
        cleaned = parser.clean_text()
        
        # Check that excessive whitespace is removed
        self.assertNotIn("    ", cleaned)  # No multiple spaces
        self.assertNotIn("\n\n\n", cleaned)  # No triple newlines
        
        # Check that text is trimmed
        self.assertFalse(cleaned.startswith("\n"))
        self.assertFalse(cleaned.endswith("\n"))
        
        # Verify cleaned text is stored
        self.assertEqual(parser.cleaned_text, cleaned)
    
    def test_clean_text_line_endings(self):
        """Test normalization of different line endings."""
        text_with_crlf = "Line 1\r\nLine 2\rLine 3\nLine 4"
        parser = LocalTextParser(text_with_crlf)
        cleaned = parser.clean_text()
        
        # All line endings should be normalized to \n
        self.assertNotIn("\r\n", cleaned)
        self.assertNotIn("\r", cleaned)
        self.assertIn("\n", cleaned)
    
    def test_clean_text_non_ascii_removal(self):
        """Test removal of non-ASCII and control characters."""
        text_with_artifacts = "Normal text\x00\x08\x7F\u2019special chars"
        parser = LocalTextParser(text_with_artifacts)
        cleaned = parser.clean_text()
        
        # Control characters should be removed
        self.assertEqual(cleaned, "Normal textspecial chars")
    
    def test_parse_sections_basic(self):
        """Test basic section parsing functionality."""
        parser = LocalTextParser(self.sample_text)
        sections = parser.parse_sections()
        
        # Check that sections are identified
        self.assertIsInstance(sections, dict)
        self.assertGreater(len(sections), 0)
        
        # Check for expected sections
        section_names = list(sections.keys())
        self.assertIn("document_title", section_names)
        self.assertIn("section_1", section_names)
        self.assertIn("contact_information", section_names)
        
        # Verify sections contain content
        for section_name, content in sections.items():
            self.assertIsInstance(content, str)
            self.assertGreater(len(content.strip()), 0)
    
    def test_parse_sections_numbered_sections(self):
        """Test parsing of numbered sections."""
        numbered_text = """
        1. First Section
        Content of first section.
        
        2. Second Section
        Content of second section.
        
        SECTION 3: Third Section
        Content of third section.
        """
        
        parser = LocalTextParser(numbered_text)
        sections = parser.parse_sections()
        
        # Should identify numbered sections
        self.assertIn("1._first_section", sections)
        self.assertIn("section_3", sections)
    
    def test_parse_sections_empty_sections_removed(self):
        """Test that empty sections are removed."""
        text_with_empty = """
        EMPTY SECTION
        
        FILLED SECTION
        This has content.
        
        ANOTHER EMPTY
        """
        
        parser = LocalTextParser(text_with_empty)
        sections = parser.parse_sections()
        
        # Empty sections should be filtered out
        for content in sections.values():
            self.assertGreater(len(content.strip()), 0)
    
    def test_extract_key_values_basic(self):
        """Test basic key-value extraction."""
        parser = LocalTextParser(self.sample_text)
        
        patterns = {
            "name": r"Name:\s*(.+)",
            "email": r"Email:\s*([\w.-]+@[\w.-]+)",
            "phone": r"Phone:\s*([\(\)\d\s-]+)",
            "revenue": r"Revenue:\s*(\$[\d.]+[MK]?)"
        }
        
        extracted = parser.extract_key_values(patterns)
        
        # Check extracted values
        self.assertIn("name", extracted)
        self.assertIn("email", extracted)
        self.assertIn("phone", extracted)
        self.assertIn("revenue", extracted)
        
        self.assertEqual(extracted["name"], "John Doe")
        self.assertEqual(extracted["email"], "john.doe@example.com")
        self.assertEqual(extracted["phone"], "(555) 123-4567")
        self.assertEqual(extracted["revenue"], "$1.5M")
    
    def test_extract_key_values_no_matches(self):
        """Test key-value extraction with no matches."""
        parser = LocalTextParser("Simple text with no patterns")
        
        patterns = {
            "name": r"Name:\s*(.+)",
            "email": r"Email:\s*([\w.-]+@[\w.-]+)"
        }
        
        extracted = parser.extract_key_values(patterns)
        self.assertEqual(extracted, {})
    
    def test_extract_key_values_invalid_regex(self):
        """Test key-value extraction with invalid regex patterns."""
        parser = LocalTextParser(self.sample_text)
        
        patterns = {
            "invalid": r"[unclosed bracket",
            "valid": r"Name:\s*(.+)"
        }
        
        # Should not raise exception, just skip invalid patterns
        extracted = parser.extract_key_values(patterns)
        
        # Valid pattern should still work
        self.assertIn("valid", extracted)
        self.assertNotIn("invalid", extracted)
    
    def test_extract_key_values_case_insensitive(self):
        """Test case-insensitive key-value extraction."""
        text = "NAME: John Doe\nemail: john@example.com"
        parser = LocalTextParser(text)
        
        patterns = {
            "name": r"name:\s*(.+)",
            "email": r"EMAIL:\s*([\w.-]+@[\w.-]+)"
        }
        
        extracted = parser.extract_key_values(patterns)
        
        self.assertEqual(extracted["name"], "John Doe")
        self.assertEqual(extracted["email"], "john@example.com")
    
    def test_to_json_basic(self):
        """Test JSON conversion functionality."""
        parser = LocalTextParser(self.sample_text)
        parser.parse_sections()  # Ensure sections are parsed
        
        json_output = parser.to_json()
        
        # Verify it's valid JSON
        parsed_json = json.loads(json_output)
        
        # Check structure
        self.assertIn("sections", parsed_json)
        self.assertIn("metadata", parsed_json)
        
        # Check metadata content
        metadata = parsed_json["metadata"]
        self.assertIn("source", metadata)
        self.assertIn("original_length", metadata)
        self.assertIn("cleaned_length", metadata)
        self.assertIn("sections_count", metadata)
        self.assertIn("parser_version", metadata)
        
        # Verify sections are included
        sections = parsed_json["sections"]
        self.assertIsInstance(sections, dict)
        self.assertGreater(len(sections), 0)
    
    def test_to_json_without_parsing(self):
        """Test JSON conversion triggers section parsing if not done."""
        parser = LocalTextParser(self.sample_text)
        
        # Don't call parse_sections explicitly
        json_output = parser.to_json()
        
        # Should still work and include sections
        parsed_json = json.loads(json_output)
        self.assertIn("sections", parsed_json)
        self.assertGreater(len(parsed_json["sections"]), 0)
    
    def test_to_json_unicode_handling(self):
        """Test JSON conversion with Unicode characters."""
        unicode_text = "Text with unicode: café, naïve, résumé"
        parser = LocalTextParser(unicode_text)
        
        json_output = parser.to_json()
        
        # Should handle Unicode without issues
        parsed_json = json.loads(json_output)
        self.assertIn("café", json_output)


class TestLocalTextParserIntegration(unittest.TestCase):
    """Integration tests for LocalTextParser with file operations."""
    
    def test_full_workflow_with_temp_file(self):
        """Test complete workflow with temporary file."""
        sample_content = """
        INVOICE
        
        Invoice Number: INV-2023-001
        Date: 2023-09-07
        
        BILL TO
        
        Company: Acme Corp
        Contact: Jane Smith
        Email: jane@acme.com
        
        ITEMS
        
        Item 1: Software License - $500
        Item 2: Support Package - $200
        
        TOTAL: $700
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_content)
            temp_path = f.name
        
        try:
            # Test full workflow
            parser = LocalTextParser(temp_path)
            
            # Clean text
            cleaned = parser.clean_text()
            self.assertGreater(len(cleaned), 0)
            
            # Parse sections
            sections = parser.parse_sections()
            self.assertIn("invoice", sections)
            self.assertIn("bill_to", sections)
            self.assertIn("items", sections)
            
            # Extract key values
            patterns = {
                "invoice_number": r"Invoice Number:\s*(.+)",
                "date": r"Date:\s*(.+)",
                "company": r"Company:\s*(.+)",
                "total": r"TOTAL:\s*(\$[\d,]+)"
            }
            
            extracted = parser.extract_key_values(patterns)
            self.assertEqual(extracted["invoice_number"], "INV-2023-001")
            self.assertEqual(extracted["date"], "2023-09-07")
            self.assertEqual(extracted["company"], "Acme Corp")
            self.assertEqual(extracted["total"], "$700")
            
            # Convert to JSON
            json_output = parser.to_json()
            parsed_json = json.loads(json_output)
            
            self.assertIn("sections", parsed_json)
            self.assertIn("metadata", parsed_json)
            self.assertEqual(parsed_json["metadata"]["source"], temp_path)
            
        finally:
            # Cleanup
            os.unlink(temp_path)


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)