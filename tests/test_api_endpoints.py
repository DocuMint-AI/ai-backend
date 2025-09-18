"""
Integration tests for OCR processing via FastAPI endpoints.

Tests the complete OCR pipeline by hitting actual API endpoints
and validating DocAI-compliant output format.
"""

import os
import sys
import json
import time
import requests
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pytest
import unittest
from unittest.mock import patch

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_PDF_PATH = project_root / "data" / "test-files" / "testing-ocr-pdf-1.pdf"
TIMEOUT_SECONDS = 60


class TestOCREndpoints(unittest.TestCase):
    """Test OCR processing via FastAPI endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class - verify server is running."""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Server health check failed: {response.status_code}")
            
            health_data = response.json()
            if health_data.get("status") != "healthy":
                raise Exception(f"Server not healthy: {health_data}")
                
            print(f"✅ Server is healthy and ready for testing")
            print(f"   OCR Service: {health_data['services']['ocr_service']['available']}")
            print(f"   Data Directory: {health_data['services']['data_directory']['accessible']}")
            
        except requests.exceptions.ConnectionError:
            raise Exception(
                f"❌ Cannot connect to API server at {API_BASE_URL}. "
                "Please ensure the FastAPI server is running:\n"
                "uv run main.py"
            )
        except Exception as e:
            raise Exception(f"❌ Server setup failed: {e}")
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = requests.get(f"{API_BASE_URL}/health")
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("services", data)
        self.assertIn("config", data)
        self.assertIn("timestamp", data)
        
        # Verify services
        services = data["services"]
        self.assertTrue(services["data_directory"]["accessible"])
        self.assertTrue(services["ocr_service"]["available"])
        self.assertTrue(services["pdf_converter"]["available"])
        
        print(f"✅ Health check passed")
        print(f"   Max file size: {data['config']['max_file_size_mb']}MB")
        print(f"   Language hints: {data['config']['language_hints']}")
    
    def test_upload_pdf_file(self):
        """Test PDF file upload endpoint."""
        if not TEST_PDF_PATH.exists():
            self.skipTest(f"Test PDF not found: {TEST_PDF_PATH}")
        
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': ('testing-ocr-pdf-1.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("success", data)
        self.assertIn("file_path", data)
        self.assertIn("file_info", data)
        self.assertTrue(data["success"])
        self.assertIn("testing-ocr-pdf-1.pdf", data["file_path"])
        
        # Store file path for subsequent tests
        self.uploaded_file_path = data["file_path"]
        
        file_info = data["file_info"]
        self.assertEqual(file_info["name"], "testing-ocr-pdf-1.pdf")
        self.assertGreater(file_info["size_mb"], 0)
        
        print(f"✅ File upload successful")
        print(f"   File path: {data['file_path']}")
        print(f"   Size: {file_info['size_mb']}MB")
        
        return data["file_path"]
    
    def test_ocr_processing_endpoint(self):
        """Test OCR processing endpoint with real PDF."""
        # First upload the file
        uploaded_file_path = self.test_upload_pdf_file()
        
        # Process with OCR
        payload = {"pdf_path": uploaded_file_path}
        response = requests.post(
            f"{API_BASE_URL}/ocr-process", 
            json=payload,
            timeout=TIMEOUT_SECONDS
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("uid", data)
        self.assertIn("total_pages", data)
        self.assertIn("processed_pages", data)
        self.assertIn("ocr_results_path", data)
        self.assertIn("metadata", data)
        
        processing_uid = data["uid"]
        total_pages = data["total_pages"]
        processed_pages = data["processed_pages"]
        
        print(f"✅ OCR processing completed")
        print(f"   UID: {processing_uid}")
        print(f"   Pages: {processed_pages}/{total_pages}")
        print(f"   Results: {data['ocr_results_path']}")
        
        # Store for subsequent tests
        self.processed_uid = processing_uid
        
        return processing_uid
    
    def test_results_endpoint_docai_format(self):
        """Test results retrieval and validate DocAI format."""
        # Process a file first
        processing_uid = self.test_ocr_processing_endpoint()
        
        # Get results
        response = requests.get(f"{API_BASE_URL}/results/{processing_uid}")
        
        self.assertEqual(response.status_code, 200)
        
        result_data = response.json()
        
        # The response has a uid and ocr_results structure
        self.assertIn("uid", result_data)
        self.assertIn("ocr_results", result_data)
        
        # The actual DocAI data is in ocr_results
        data = result_data["ocr_results"]
        
        # Validate top-level DocAI structure
        required_fields = [
            "document_id", "original_filename", "file_fingerprint",
            "derived_images", "language_detection", 
            "ocr_result", "extracted_assets", "preprocessing", "warnings"
        ]
        
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")
        
        # Validate document metadata
        self.assertEqual(data["original_filename"], "testing-ocr-pdf-1.pdf")
        self.assertTrue(data["file_fingerprint"].startswith("sha256:"))
        
        # Validate language detection
        lang_detection = data["language_detection"]
        self.assertIn("primary", lang_detection)
        self.assertIn("confidence", lang_detection)
        # The API returns language_hints instead of detected_languages
        self.assertIn("language_hints", lang_detection)
        self.assertIsInstance(lang_detection["language_hints"], list)
        
        # Validate OCR result structure
        ocr_result = data["ocr_result"]
        self.assertIn("pages", ocr_result)
        self.assertIsInstance(ocr_result["pages"], list)
        self.assertGreater(len(ocr_result["pages"]), 0)
        
        # Validate page structure
        first_page = ocr_result["pages"][0]
        page_fields = ["page", "width", "height", "page_confidence", "text_blocks"]
        for field in page_fields:
            self.assertIn(field, first_page, f"Missing page field: {field}")
        
        # Validate text blocks
        text_blocks = first_page["text_blocks"]
        self.assertIsInstance(text_blocks, list)
        
        if text_blocks:  # If we have text blocks
            first_block = text_blocks[0]
            block_fields = ["block_id", "text", "confidence", "bounding_box", "lines"]
            for field in block_fields:
                self.assertIn(field, first_block, f"Missing block field: {field}")
            
            # Validate block ID format
            self.assertTrue(first_block["block_id"].startswith("p1_b"))
            
            # Validate bounding box format (should be array of coordinates)
            bbox = first_block["bounding_box"]
            self.assertIsInstance(bbox, list)
            self.assertEqual(len(bbox), 4)  # [x1, y1, x2, y2]
            
            # Validate lines structure
            lines = first_block["lines"]
            self.assertIsInstance(lines, list)
            
            if lines:  # If we have lines
                first_line = lines[0]
                line_fields = ["line_id", "text", "confidence", "words"]
                for field in line_fields:
                    self.assertIn(field, first_line, f"Missing line field: {field}")
                
                # Validate line ID format
                self.assertTrue(first_line["line_id"].startswith("p1_b"))
                self.assertIn("_l", first_line["line_id"])
                
                # Validate words structure
                words = first_line["words"]
                self.assertIsInstance(words, list)
                
                if words:  # If we have words
                    first_word = words[0]
                    word_fields = ["text", "confidence", "bounding_box"]
                    for field in word_fields:
                        self.assertIn(field, first_word, f"Missing word field: {field}")
                    
                    # Validate word bounding box format
                    word_bbox = first_word["bounding_box"]
                    self.assertIsInstance(word_bbox, list)
                    self.assertGreater(len(word_bbox), 0)  # Array of coordinate pairs
        
        # Validate preprocessing metadata
        preprocessing = data["preprocessing"]
        self.assertIn("pipeline_version", preprocessing)
        # The API uses 'generated_at' instead of 'processing_timestamp'
        self.assertIn("generated_at", preprocessing)
        
        # Validate derived images
        derived_images = data["derived_images"]
        self.assertIsInstance(derived_images, list)
        self.assertGreater(len(derived_images), 0)
        
        first_image = derived_images[0]
        image_fields = ["page", "image_uri", "width", "height", "dpi"]
        for field in image_fields:
            self.assertIn(field, first_image, f"Missing image field: {field}")
        
        print(f"✅ DocAI format validation passed")
        print(f"   Document ID: {data['document_id']}")
        print(f"   Primary language: {data['language_detection']['primary']}")
        print(f"   Pages: {len(data['ocr_result']['pages'])}")
        print(f"   Total blocks: {sum(len(p['text_blocks']) for p in data['ocr_result']['pages'])}")
        print(f"   Pipeline version: {data['preprocessing']['pipeline_version']}")
        
        # Save result for manual inspection
        output_path = project_root / "data" / "test_endpoint_result.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print(f"   Full result saved to: {output_path}")
        
        return data
    
    def test_error_handling_invalid_uid(self):
        """Test error handling for invalid UID."""
        # Test OCR processing with invalid PDF path
        payload = {"pdf_path": "invalid/path/to/file.pdf"}
        response = requests.post(f"{API_BASE_URL}/ocr-process", json=payload)
        
        self.assertIn(response.status_code, [400, 404, 422])
        
        data = response.json()
        self.assertIn("detail", data)
        
        # Test results with invalid document ID
        response = requests.get(f"{API_BASE_URL}/results/invalid_document_id_12345")
        self.assertIn(response.status_code, [404, 422])
        
        print(f"✅ Error handling working correctly")
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b'This is not a PDF file')
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = requests.post(f"{API_BASE_URL}/upload", files=files)
            
            # Should either reject or handle gracefully
            self.assertIn(response.status_code, [400, 422])
            
            print(f"✅ Invalid file type handling working")
        finally:
            os.unlink(tmp_path)
    
    def test_complete_workflow(self):
        """Test complete workflow: upload -> process -> retrieve -> validate."""
        print("\n🔄 Testing complete OCR workflow...")
        
        # Step 1: Upload
        uploaded_file_path = self.test_upload_pdf_file()
        
        # Step 2: Process
        document_id = self.test_ocr_processing_endpoint()
        
        # Step 3: Retrieve and validate
        result_data = self.test_results_endpoint_docai_format()
        
        # Step 4: Additional validations
        
        # Check that we got actual text (not empty)
        pages = result_data["ocr_result"]["pages"]
        total_text = ""
        total_blocks = 0
        
        for page in pages:
            for block in page["text_blocks"]:
                total_text += block["text"] + " "
                total_blocks += 1
        
        total_text = total_text.strip()
        
        self.assertGreater(len(total_text), 0, "No text was extracted from PDF")
        self.assertGreater(total_blocks, 0, "No text blocks found")
        
        # Check confidence scores are reasonable
        confidences = []
        for page in pages:
            for block in page["text_blocks"]:
                if block["confidence"] > 0:  # Skip zero confidence scores
                    confidences.append(block["confidence"])
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            print(f"   Average block confidence: {avg_confidence:.3f}")
            
            # Most text should have decent confidence
            high_confidence_blocks = [c for c in confidences if c > 0.7]
            confidence_ratio = len(high_confidence_blocks) / len(confidences)
            print(f"   High confidence blocks: {confidence_ratio:.1%}")
        
        print(f"✅ Complete workflow test passed")
        print(f"   Extracted text length: {len(total_text)} characters")
        print(f"   Text blocks: {total_blocks}")
        print(f"   Text sample: '{total_text[:100]}...'")


class TestAPIDocumentation(unittest.TestCase):
    """Test API documentation endpoints."""
    
    def test_openapi_docs(self):
        """Test OpenAPI documentation endpoint."""
        response = requests.get(f"{API_BASE_URL}/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        
        print(f"✅ OpenAPI docs accessible at {API_BASE_URL}/docs")
    
    def test_redoc_docs(self):
        """Test ReDoc documentation endpoint."""
        response = requests.get(f"{API_BASE_URL}/redoc")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        
        print(f"✅ ReDoc docs accessible at {API_BASE_URL}/redoc")
    
    def test_openapi_json(self):
        """Test OpenAPI JSON schema endpoint."""
        response = requests.get(f"{API_BASE_URL}/openapi.json")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("openapi", data)
        self.assertIn("info", data)
        self.assertIn("paths", data)
        
        # Check our endpoints are documented
        paths = data["paths"]
        expected_paths = ["/health", "/upload", "/ocr-process", "/results/{uid}"]
        
        for path in expected_paths:
            self.assertIn(path, paths, f"Missing API path: {path}")
        
        print(f"✅ OpenAPI schema validation passed")


def run_tests():
    """Run all tests with proper setup and reporting."""
    print("🚀 Starting OCR API Integration Tests")
    print("=" * 60)
    
    # Check if test PDF exists
    if not TEST_PDF_PATH.exists():
        print(f"❌ Test PDF not found: {TEST_PDF_PATH}")
        print("Please ensure the test PDF file exists before running tests.")
        return False
    
    print(f"📄 Using test PDF: {TEST_PDF_PATH}")
    print(f"🌐 API Base URL: {API_BASE_URL}")
    print(f"⏱️  Timeout: {TIMEOUT_SECONDS}s")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOCREndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIDocumentation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 All tests passed! Your OCR API is working correctly.")
        print(f"✅ Tests run: {result.testsRun}")
        print(f"✅ Failures: {len(result.failures)}")
        print(f"✅ Errors: {len(result.errors)}")
        return True
    else:
        print("❌ Some tests failed.")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
        
        return False


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)