"""
Unit tests for OCR processing module.

Tests cover OCRResult dataclass and GoogleVisionOCR class functionality
including Google Vision API integration with proper mocking.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import tempfile

# Add services directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'preprocessing'))

from google.cloud import vision
from google.api_core import exceptions as gcp_exceptions

# Import the modules to test
from OCR_processing import OCRResult, GoogleVisionOCR


class TestOCRResult(unittest.TestCase):
    """Test cases for OCRResult dataclass."""
    
    def test_ocr_result_creation(self):
        """Test OCRResult dataclass creation with valid data."""
        blocks = [
            {
                "text": "Sample text",
                "confidence": 0.95,
                "bounding_box": [{"x": 0, "y": 0}, {"x": 100, "y": 100}]
            }
        ]
        
        result = OCRResult(
            text="Sample extracted text",
            blocks=blocks,
            confidence=0.95
        )
        
        self.assertEqual(result.text, "Sample extracted text")
        self.assertEqual(len(result.blocks), 1)
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.blocks[0]["text"], "Sample text")
    
    def test_ocr_result_empty(self):
        """Test OCRResult with empty/default values."""
        result = OCRResult(text="", blocks=[], confidence=0.0)
        
        self.assertEqual(result.text, "")
        self.assertEqual(result.blocks, [])
        self.assertEqual(result.confidence, 0.0)


class TestGoogleVisionOCR(unittest.TestCase):
    """Test cases for GoogleVisionOCR class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_project_id = "test-project"
        self.mock_credentials_path = "/path/to/test-credentials.json"
        self.mock_language_hints = ["en", "es"]
        
        # Create mock Vision API response
        self.mock_response = Mock(spec=vision.AnnotateImageResponse)
        self.mock_response.error.message = ""
        
        # Create mock full text annotation
        self.mock_full_text = Mock()
        self.mock_full_text.text = "Sample extracted text"
        self.mock_response.full_text_annotation = self.mock_full_text
        
        # Create mock page structure
        self.mock_page = Mock()
        self.mock_block = Mock()
        self.mock_paragraph = Mock()
        self.mock_word = Mock()
        self.mock_symbol = Mock()
        
        # Set up mock hierarchy
        self.mock_symbol.text = "word"
        self.mock_word.symbols = [self.mock_symbol]
        self.mock_word.confidence = 0.95
        self.mock_paragraph.words = [self.mock_word]
        self.mock_block.paragraphs = [self.mock_paragraph]
        
        # Mock bounding box
        self.mock_vertex = Mock()
        self.mock_vertex.x = 0
        self.mock_vertex.y = 0
        self.mock_bounding_box = Mock()
        self.mock_bounding_box.vertices = [self.mock_vertex]
        self.mock_block.bounding_box = self.mock_bounding_box
        
        self.mock_page.blocks = [self.mock_block]
        self.mock_full_text.pages = [self.mock_page]
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_initialization_success(self, mock_client_constructor):
        """Test successful GoogleVisionOCR initialization."""
        mock_client = Mock()
        mock_client_constructor.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path,
            language_hints=self.mock_language_hints
        )
        
        self.assertEqual(ocr.project_id, self.mock_project_id)
        self.assertEqual(ocr.credentials_path, self.mock_credentials_path)
        self.assertEqual(ocr.language_hints, self.mock_language_hints)
        mock_client_constructor.assert_called_once_with(self.mock_credentials_path)
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_initialization_default_language(self, mock_client_constructor):
        """Test initialization with default language hints."""
        mock_client = Mock()
        mock_client_constructor.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        self.assertEqual(ocr.language_hints, ["en"])
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_initialization_failure(self, mock_client_constructor):
        """Test GoogleVisionOCR initialization failure."""
        mock_client_constructor.side_effect = Exception("Credentials error")
        
        with self.assertRaises(Exception):
            GoogleVisionOCR(
                project_id=self.mock_project_id,
                credentials_path=self.mock_credentials_path
            )
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_image_data')
    @patch('OCR_processing.Path.exists')
    def test_extract_text_success(self, mock_exists, mock_file, mock_client_constructor):
        """Test successful text extraction from image file."""
        # Setup mocks
        mock_exists.return_value = True
        mock_client = Mock()
        mock_client.document_text_detection.return_value = self.mock_response
        mock_client_constructor.return_value = mock_client
        
        # Create OCR instance
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        # Test extract_text
        result = ocr.extract_text("fake_image.jpg")
        
        # Verify results
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.text, "Sample extracted text")
        mock_file.assert_called_once_with(Path("fake_image.jpg"), "rb")
        mock_client.document_text_detection.assert_called_once()
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    @patch('OCR_processing.Path.exists')
    def test_extract_text_file_not_found(self, mock_exists, mock_client_constructor):
        """Test extract_text with non-existent file."""
        mock_exists.return_value = False
        mock_client_constructor.return_value = Mock()
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        with self.assertRaises(FileNotFoundError):
            ocr.extract_text("nonexistent.jpg")
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_extract_from_bytes_success(self, mock_client_constructor):
        """Test successful text extraction from bytes."""
        mock_client = Mock()
        mock_client.document_text_detection.return_value = self.mock_response
        mock_client_constructor.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        image_bytes = b'fake_image_data'
        result = ocr.extract_from_bytes(image_bytes)
        
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.text, "Sample extracted text")
        mock_client.document_text_detection.assert_called_once()
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_extract_from_bytes_api_error(self, mock_client_constructor):
        """Test extract_from_bytes with API error."""
        mock_client = Mock()
        mock_response_error = Mock()
        mock_response_error.error.message = "API Error occurred"
        mock_client.document_text_detection.return_value = mock_response_error
        mock_client_constructor.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        with self.assertRaises(gcp_exceptions.GoogleAPIError):
            ocr.extract_from_bytes(b'fake_data')
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_extract_from_bytes_gcp_exception(self, mock_client_constructor):
        """Test extract_from_bytes with Google Cloud exception."""
        mock_client = Mock()
        mock_client.document_text_detection.side_effect = gcp_exceptions.GoogleAPIError("API failure")
        mock_client_constructor.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        with self.assertRaises(gcp_exceptions.GoogleAPIError):
            ocr.extract_from_bytes(b'fake_data')
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_parse_response_with_full_annotation(self, mock_client_constructor):
        """Test _parse_response with complete annotation data."""
        mock_client_constructor.return_value = Mock()
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        result = ocr._parse_response(self.mock_response)
        
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.text, "Sample extracted text")
        self.assertEqual(len(result.blocks), 1)
        self.assertGreater(result.confidence, 0)
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_parse_response_empty_annotation(self, mock_client_constructor):
        """Test _parse_response with empty annotation."""
        mock_client_constructor.return_value = Mock()
        
        # Create empty response
        empty_response = Mock(spec=vision.AnnotateImageResponse)
        empty_response.full_text_annotation = None
        empty_response.error.message = ""
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        result = ocr._parse_response(empty_response)
        
        self.assertEqual(result.text, "")
        self.assertEqual(result.blocks, [])
        self.assertEqual(result.confidence, 0.0)
    
    @patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file')
    def test_parse_response_no_confidence(self, mock_client_constructor):
        """Test _parse_response with missing confidence data."""
        mock_client_constructor.return_value = Mock()
        
        # Create response with no confidence
        self.mock_word.confidence = None
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        result = ocr._parse_response(self.mock_response)
        
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.confidence, 0.0)


class TestGoogleVisionOCRIntegration(unittest.TestCase):
    """Integration tests for GoogleVisionOCR (requires actual setup)."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    
    @unittest.skip("Requires actual Google Cloud credentials")
    def test_real_api_call(self):
        """Test with real API call (skipped by default)."""
        # This test would require actual credentials and would make real API calls
        # Only enable for integration testing with proper setup
        pass
    
    def test_image_context_creation(self):
        """Test Vision API image context creation."""
        with patch('OCR_processing.vision.ImageAnnotatorClient.from_service_account_file'):
            ocr = GoogleVisionOCR("test-project", "test-creds.json", ["en", "fr"])
            
            # Test that language hints are properly set
            self.assertEqual(ocr.language_hints, ["en", "fr"])


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)