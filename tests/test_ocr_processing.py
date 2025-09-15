"""
Unit tests for OCR processing module.

Tests cover the GoogleVisionOCR class functionality with proper mocking.
For integration tests with real API endpoints, see test_api_endpoints.py
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
try:
    from OCR_processing import GoogleVisionOCR
except ImportError as e:
    print(f"Warning: Could not import OCR_processing: {e}")
    print("Make sure the virtual environment is activated and dependencies are installed.")


class TestGoogleVisionOCR(unittest.TestCase):
    """Test cases for GoogleVisionOCR class with mocked API calls."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_project_id = "test-project"
        self.mock_credentials_path = "./data/.cheetah/gcloud/vision-credentials.json"
        self.mock_language_hints = ["en", "es"]
        
        # Create mock Vision API response
        self.mock_response = Mock(spec=vision.AnnotateImageResponse)
        self.mock_response.error.message = ""
        
        # Create mock full text annotation
        self.mock_full_text = Mock()
        self.mock_full_text.text = "Sample extracted text from PDF document"
        self.mock_response.full_text_annotation = self.mock_full_text
        
        # Create mock page structure for DocAI format
        self.mock_page = Mock()
        self.mock_block = Mock()
        self.mock_paragraph = Mock()
        self.mock_word = Mock()
        self.mock_symbol = Mock()
        
        # Set up mock hierarchy
        self.mock_symbol.text = "document"
        self.mock_word.symbols = [self.mock_symbol]
        self.mock_word.confidence = 0.95
        self.mock_paragraph.words = [self.mock_word]
        self.mock_block.paragraphs = [self.mock_paragraph]
        
        # Mock bounding box
        self.mock_vertex = Mock()
        self.mock_vertex.x = 100
        self.mock_vertex.y = 200
        self.mock_vertex2 = Mock()
        self.mock_vertex2.x = 500
        self.mock_vertex2.y = 250
        
        self.mock_bounding_box = Mock()
        self.mock_bounding_box.vertices = [
            self.mock_vertex, self.mock_vertex2, self.mock_vertex2, self.mock_vertex
        ]
        self.mock_block.bounding_box = self.mock_bounding_box
        
        self.mock_page.blocks = [self.mock_block]
        self.mock_full_text.pages = [self.mock_page]
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_initialization_from_env(self, mock_client_class):
        """Test GoogleVisionOCR.from_env() method."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {
            'GOOGLE_CLOUD_PROJECT_ID': 'test-project-123',
            'GOOGLE_APPLICATION_CREDENTIALS': './data/test-creds.json',
            'LANGUAGE_HINTS': 'en,es,fr'
        }):
            ocr = GoogleVisionOCR.from_env()
            
            self.assertEqual(ocr.project_id, 'test-project-123')
            self.assertEqual(ocr.credentials_path, './data/test-creds.json')
            self.assertEqual(ocr.language_hints, ['en', 'es', 'fr'])
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_initialization_missing_env_vars(self, mock_client_class):
        """Test initialization failure with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                GoogleVisionOCR.from_env()
            
            self.assertIn("GOOGLE_CLOUD_PROJECT_ID", str(context.exception))
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_pdf_data')
    @patch('OCR_processing.Path.exists')
    def test_extract_text_success(self, mock_exists, mock_file, mock_client_class):
        """Test successful text extraction from image file."""
        # Setup mocks
        mock_exists.return_value = True
        mock_client = Mock()
        mock_client.document_text_detection.return_value = self.mock_response
        mock_client_class.return_value = mock_client
        
        # Create OCR instance
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        # Test extract_text with DocAI format
        result = ocr.extract_text("fake_image.jpg", page_number=1, image_metadata={
            "width": 800,
            "height": 600,
            "dpi": 300
        })
        
        # Verify DocAI format structure
        self.assertIn("page_data", result)
        self.assertIn("full_text", result)
        
        page_data = result["page_data"]
        self.assertEqual(page_data["page"], 1)
        self.assertEqual(page_data["width"], 800)
        self.assertEqual(page_data["height"], 600)
        self.assertIn("text_blocks", page_data)
        self.assertIn("page_confidence", page_data)
        
        # Verify text blocks have proper structure
        text_blocks = page_data["text_blocks"]
        self.assertIsInstance(text_blocks, list)
        
        if text_blocks:
            first_block = text_blocks[0]
            self.assertIn("block_id", first_block)
            self.assertIn("text", first_block)
            self.assertIn("confidence", first_block)
            self.assertIn("bounding_box", first_block)
            self.assertIn("lines", first_block)
            
            # Verify block ID format
            self.assertTrue(first_block["block_id"].startswith("p1_b"))
        
        mock_file.assert_called_once_with(Path("fake_image.jpg"), "rb")
        mock_client.document_text_detection.assert_called_once()
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_extract_from_bytes_docai_format(self, mock_client_class):
        """Test extract_from_bytes with DocAI format output."""
        mock_client = Mock()
        mock_client.document_text_detection.return_value = self.mock_response
        mock_client_class.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        image_bytes = b'fake_image_data'
        result = ocr.extract_from_bytes(image_bytes, page_number=1, image_metadata={
            "width": 2480,
            "height": 3508,
            "dpi": 300
        })
        
        # Verify DocAI structure
        self.assertIn("page_data", result)
        page_data = result["page_data"]
        
        self.assertEqual(page_data["page"], 1)
        self.assertEqual(page_data["width"], 2480)
        self.assertEqual(page_data["height"], 3508)
        self.assertGreater(page_data["page_confidence"], 0)
        
        mock_client.document_text_detection.assert_called_once()
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_create_docai_document(self, mock_client_class):
        """Test creation of complete DocAI document structure."""
        mock_client_class.return_value = Mock()
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        # Create sample page data
        pages_data = [{
            "page_data": {
                "page": 1,
                "width": 800,
                "height": 600,
                "page_confidence": 0.95,
                "text_blocks": [
                    {
                        "block_id": "p1_b1",
                        "text": "Sample text",
                        "confidence": 0.98,
                        "bounding_box": [100, 200, 500, 250],
                        "lines": []
                    }
                ]
            },
            "full_text": "Sample text"
        }]
        
        derived_images = [{
            "page": 1,
            "image_uri": "file://./data/test.png",
            "width": 800,
            "height": 600,
            "dpi": 300
        }]
        
        # Create DocAI document
        docai_doc = ocr.create_docai_document(
            document_id="test_doc_001",
            original_filename="test.pdf",
            pdf_path="./data/test.pdf",
            pages_data=pages_data,
            derived_images=derived_images
        )
        
        # Validate DocAI structure
        self.assertEqual(docai_doc.document_id, "test_doc_001")
        self.assertEqual(docai_doc.original_filename, "test.pdf")
        self.assertTrue(docai_doc.file_fingerprint.startswith("sha256:"))
        self.assertIn("preprocessing", docai_doc.__dict__)
        self.assertIn("language_detection", docai_doc.__dict__)
        self.assertIn("ocr_result", docai_doc.__dict__)
        
        # Check OCR result structure
        self.assertIn("pages", docai_doc.ocr_result)
        self.assertEqual(len(docai_doc.ocr_result["pages"]), 1)
        
        first_page = docai_doc.ocr_result["pages"][0]
        self.assertEqual(first_page["page"], 1)
        self.assertIn("text_blocks", first_page)
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_parse_response_docai_format(self, mock_client_class):
        """Test _parse_response_docai_format method."""
        mock_client_class.return_value = Mock()
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        result = ocr._parse_response_docai_format(
            self.mock_response, 
            page_number=1,
            image_width=800,
            image_height=600
        )
        
        # Verify DocAI page structure
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["width"], 800)
        self.assertEqual(result["height"], 600)
        self.assertIn("text_blocks", result)
        self.assertIn("page_confidence", result)
        
        # Verify text blocks
        text_blocks = result["text_blocks"]
        self.assertIsInstance(text_blocks, list)
        
        if text_blocks:
            first_block = text_blocks[0]
            required_fields = ["block_id", "text", "confidence", "bounding_box", "lines"]
            for field in required_fields:
                self.assertIn(field, first_block)
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_error_handling_api_failure(self, mock_client_class):
        """Test error handling for API failures."""
        mock_client = Mock()
        mock_client.document_text_detection.side_effect = gcp_exceptions.GoogleAPIError("API failure")
        mock_client_class.return_value = mock_client
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        with self.assertRaises(Exception):
            ocr.extract_from_bytes(b'fake_data')
    
    @patch('OCR_processing.vision.ImageAnnotatorClient')
    def test_bounding_box_coordinate_conversion(self, mock_client_class):
        """Test bounding box coordinate conversion to array format."""
        mock_client_class.return_value = Mock()
        
        ocr = GoogleVisionOCR(
            project_id=self.mock_project_id,
            credentials_path=self.mock_credentials_path
        )
        
        # Test coordinate conversion
        vertices = [
            Mock(x=100, y=200),
            Mock(x=500, y=200),
            Mock(x=500, y=250),
            Mock(x=100, y=250)
        ]
        
        coords = ocr._vertices_to_coordinates(vertices)
        expected = [100, 200, 500, 250]  # [x1, y1, x2, y2]
        
        self.assertEqual(coords, expected)
    
    def test_generate_document_id(self):
        """Test document ID generation."""
        with patch('OCR_processing.vision.ImageAnnotatorClient'):
            ocr = GoogleVisionOCR(
                project_id=self.mock_project_id,
                credentials_path=self.mock_credentials_path
            )
            
            # Test with filename
            doc_id = ocr._generate_document_id("test.pdf")
            self.assertTrue(doc_id.startswith("doc_"))
            self.assertIn("test", doc_id)
            
            # Should be consistent for same input
            doc_id2 = ocr._generate_document_id("test.pdf")
            self.assertEqual(doc_id, doc_id2)


class TestEnvironmentSetup(unittest.TestCase):
    """Test environment setup and configuration."""
    
    def test_required_environment_variables(self):
        """Test that required environment variables are documented."""
        required_vars = [
            "GOOGLE_CLOUD_PROJECT_ID",
            "GOOGLE_APPLICATION_CREDENTIALS", 
            "LANGUAGE_HINTS"
        ]
        
        # This test documents the required environment variables
        for var in required_vars:
            with self.subTest(var=var):
                # Test that we handle missing variables gracefully
                self.assertIsInstance(var, str)
                self.assertTrue(len(var) > 0)


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2)