"""
Test GCS Staging Functionality.

Tests the auto_stage_document function to ensure local files are properly
uploaded to GCS before processing.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.gcs_staging import auto_stage_document, is_gcs_uri, get_staging_bucket_name
from services.doc_ai.client import DocAIError


class TestGCSStaging:
    """Test GCS staging functionality."""
    
    @pytest.fixture
    def test_pdf_path(self):
        """Create a temporary test PDF file."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4 fake pdf content for testing')
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)
    
    def test_is_gcs_uri(self):
        """Test GCS URI detection."""
        assert is_gcs_uri("gs://bucket/file.pdf") == True
        assert is_gcs_uri("/path/to/file.pdf") == False
        assert is_gcs_uri("file.pdf") == False
        assert is_gcs_uri("http://example.com") == False
        assert is_gcs_uri("") == False
    
    def test_get_staging_bucket_name_from_env(self):
        """Test getting bucket name from environment."""
        with patch.dict(os.environ, {"GCS_TEST_BUCKET": "gs://test-bucket/"}):
            bucket = get_staging_bucket_name()
            assert bucket == "test-bucket"
        
        with patch.dict(os.environ, {"GCS_TEST_BUCKET": "test-bucket-2"}):
            bucket = get_staging_bucket_name()
            assert bucket == "test-bucket-2"
    
    def test_get_staging_bucket_name_missing(self):
        """Test error when bucket not configured."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GCS_TEST_BUCKET not configured"):
                get_staging_bucket_name()
    
    def test_auto_stage_gcs_uri_passthrough(self):
        """Test that existing GCS URIs are passed through unchanged."""
        gcs_uri = "gs://existing-bucket/document.pdf"
        result = auto_stage_document(gcs_uri)
        assert result == gcs_uri
    
    @patch('services.gcs_staging.DocAIClient')
    def test_auto_stage_local_file(self, mock_docai_client, test_pdf_path):
        """Test staging a local file to GCS."""
        # Mock the DocAI client
        mock_client_instance = Mock()
        mock_client_instance.stage_to_gcs.return_value = "gs://test-bucket/staging/documents/123-abc-test.pdf"
        mock_docai_client.return_value = mock_client_instance
        
        # Set environment
        with patch.dict(os.environ, {
            "GCS_TEST_BUCKET": "test-bucket",
            "GOOGLE_CLOUD_PROJECT_ID": "test-project",
            "DOCAI_LOCATION": "us"
        }):
            result = auto_stage_document(test_pdf_path)
            
            # Verify result
            assert result.startswith("gs://test-bucket/staging/documents/")
            assert result.endswith("test.pdf")
            
            # Verify client was called correctly
            mock_client_instance.stage_to_gcs.assert_called_once()
            call_args = mock_client_instance.stage_to_gcs.call_args
            assert call_args[0][0] == test_pdf_path  # local_path
            assert call_args[0][1] == "test-bucket"  # bucket_name
            assert "staging/documents/" in call_args[0][2]  # blob_name
    
    def test_auto_stage_nonexistent_file(self):
        """Test error handling for nonexistent files."""
        with pytest.raises(ValueError, match="Local file not found"):
            auto_stage_document("/path/to/nonexistent/file.pdf")
    
    def test_auto_stage_non_pdf_file(self):
        """Test error handling for non-PDF files."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'not a pdf')
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Only PDF files are supported"):
                auto_stage_document(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('services.gcs_staging.DocAIClient')
    def test_auto_stage_staging_error(self, mock_docai_client, test_pdf_path):
        """Test error handling when staging fails."""
        # Mock the DocAI client to raise an error
        mock_client_instance = Mock()
        mock_client_instance.stage_to_gcs.side_effect = DocAIError("Upload failed")
        mock_docai_client.return_value = mock_client_instance
        
        with patch.dict(os.environ, {"GCS_TEST_BUCKET": "test-bucket"}):
            with pytest.raises(DocAIError, match="Upload failed"):
                auto_stage_document(test_pdf_path)


if __name__ == "__main__":
    # Quick validation
    print("🧪 Running GCS staging tests...")
    
    # Test basic functionality
    assert is_gcs_uri("gs://bucket/file.pdf") == True
    assert is_gcs_uri("/local/file.pdf") == False
    
    print("✅ Basic tests passed")
    print("🏁 Run with pytest for full test suite: pytest test_gcs_staging.py -v")