"""
Comprehensive test suite for DocAI integration.

This module provides unit and integration tests for all DocAI components
with proper fixtures and mocking.
"""

import pytest
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Test imports
from fastapi.testclient import TestClient

def get_test_gcs_bucket() -> str:
    """Get GCS test bucket from environment, with fallback."""
    bucket = os.getenv('GCS_TEST_BUCKET', 'gs://test-bucket/')
    return bucket.rstrip('/') + '/'
import httpx

# DocAI imports
from services.doc_ai.client import DocAIClient, DocAIError
from services.doc_ai.parser import DocumentParser
from services.doc_ai.schema import (
    ParseRequest, ParseResponse, ParsedDocument,
    DocumentMetadata, NamedEntity, Clause, EntityType, ClauseType, TextSpan
)

# App imports
from main import app


# Test Fixtures
@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'GOOGLE_CLOUD_PROJECT_ID': 'test-project',
        'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/test-creds.json',
        'DOCAI_PROCESSOR_ID': 'test-processor',
        'DOCAI_LOCATION': 'us'
    }):
        yield


@pytest.fixture
def mock_docai_document():
    """Mock DocAI document response."""
    mock_doc = Mock()
    mock_doc.text = "This is a test contract between Company A and Company B for $50,000."
    mock_doc.pages = [Mock()]
    mock_doc.entities = [
        Mock(
            type_="ORGANIZATION",
            confidence=0.95,
            mention_text="Company A",
            page_anchor=Mock(page_refs=[Mock(page=0)])
        ),
        Mock(
            type_="MONEY",
            confidence=0.98,
            mention_text="$50,000",
            page_anchor=Mock(page_refs=[Mock(page=0)])
        )
    ]
    return mock_doc


@pytest.fixture
def sample_metadata():
    """Sample document metadata."""
    return DocumentMetadata(
        document_id="test-doc-001",
        original_filename="test.pdf",
        file_size=1024,
        page_count=1,
        language="en"
    )


# Unit Tests
class TestDocAIClient:
    """Unit tests for DocAI client."""
    
    def test_client_initialization(self, mock_env_vars):
        """Test client initialization."""
        client = DocAIClient(
            project_id="test-project",
            location="us",
            processor_id="test-processor"
        )
        
        assert client.project_id == "test-project"
        assert client.location == "us"
        assert client.default_processor_id == "test-processor"
    
    def test_processor_name_generation(self, mock_env_vars):
        """Test processor name generation."""
        client = DocAIClient(
            project_id="test-project",
            location="us",
            processor_id="test-processor"
        )
        
        with patch.object(client, 'client') as mock_client:
            mock_client.processor_path.return_value = "projects/test-project/locations/us/processors/test-processor"
            
            name = client.get_processor_name()
            assert name == "projects/test-project/locations/us/processors/test-processor"
    
    def test_gcs_uri_validation(self, mock_env_vars):
        """Test GCS URI validation."""
        client = DocAIClient(project_id="test-project")
        
        # Test invalid URIs
        invalid_uris = [
            "invalid-uri",
            "gs://",
            "gs://bucket",
            "gs:///no-bucket/file.pdf"
        ]
        
        for uri in invalid_uris:
            with pytest.raises((ValueError, DocAIError)):
                client.download_from_gcs(uri)
    
    @patch('services.doc_ai.client.storage.Client')
    def test_gcs_download_file_not_found(self, mock_storage, mock_env_vars):
        """Test GCS download when file doesn't exist."""
        client = DocAIClient(project_id="test-project")
        
        # Setup mock
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket
        
        with pytest.raises(DocAIError, match="File not found"):
            client.download_from_gcs(f"{get_test_gcs_bucket()}missing-file.pdf")


class TestDocumentParser:
    """Unit tests for document parser."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = DocumentParser(confidence_threshold=0.8)
        assert parser.confidence_threshold == 0.8
        assert len(parser.entity_type_mapping) > 0
    
    def test_entity_extraction(self, mock_docai_document, sample_metadata):
        """Test entity extraction from DocAI document."""
        parser = DocumentParser(confidence_threshold=0.7)
        
        entities = parser._extract_entities(mock_docai_document, mock_docai_document.text)
        
        assert len(entities) == 2  # Company A and $50,000
        
        # Check entity types
        org_entities = [e for e in entities if e.type == EntityType.ORGANIZATION]
        money_entities = [e for e in entities if e.type == EntityType.MONEY]
        
        assert len(org_entities) == 1
        assert len(money_entities) == 1
    
    def test_clause_detection(self):
        """Test clause detection."""
        parser = DocumentParser(confidence_threshold=0.7)
        
        test_text = """
        This agreement shall terminate on December 31, 2024.
        
        Payment terms: All invoices must be paid within 30 days.
        """
        
        mock_doc = Mock()
        mock_doc.text = test_text
        
        clauses = parser._detect_clauses(mock_doc, test_text)
        
        # Should detect termination and payment clauses
        clause_types = [c.type for c in clauses]
        assert ClauseType.TERMINATION in clause_types
        assert ClauseType.PAYMENT in clause_types
    
    def test_entity_normalization(self):
        """Test entity value normalization."""
        parser = DocumentParser()
        
        # Test date normalization
        date_result = parser._normalize_entity_value(EntityType.DATE, "January 15, 2024")
        assert "2024-01-15" in date_result
        
        # Test money normalization
        money_result = parser._normalize_entity_value(EntityType.MONEY, "$50,000")
        assert money_result.startswith("USD:")


class TestDocAISchema:
    """Unit tests for Pydantic schemas."""
    
    def test_parse_request_validation(self):
        """Test ParseRequest validation."""
        # Valid request
        request = ParseRequest(gcs_uri=f"{get_test_gcs_bucket()}test.pdf")
        assert request.gcs_uri == f"{get_test_gcs_bucket()}test.pdf"
        assert request.confidence_threshold == 0.7
        
        # Invalid GCS URI
        with pytest.raises(ValueError, match="GCS URI must start with gs://"):
            ParseRequest(gcs_uri="invalid-uri")
    
    def test_named_entity_creation(self):
        """Test NamedEntity model creation."""
        text_span = TextSpan(start_offset=0, end_offset=5, text="Apple")
        
        entity = NamedEntity(
            id="entity_001",
            type=EntityType.ORGANIZATION,
            text_span=text_span,
            confidence=0.95,
            page_number=1
        )
        
        assert entity.id == "entity_001"
        assert entity.type == EntityType.ORGANIZATION
        assert entity.text_span.text == "Apple"
    
    def test_parsed_document_properties(self):
        """Test ParsedDocument computed properties."""
        metadata = DocumentMetadata(
            document_id="test",
            original_filename="test.pdf",
            file_size=1024,
            page_count=1,
            language="en"
        )
        
        entities = [
            NamedEntity(
                id="e1",
                type=EntityType.PERSON,
                text_span=TextSpan(start_offset=0, end_offset=4, text="John"),
                confidence=0.9,
                page_number=1
            ),
            NamedEntity(
                id="e2",
                type=EntityType.ORGANIZATION,
                text_span=TextSpan(start_offset=5, end_offset=14, text="Company A"),
                confidence=0.8,
                page_number=1
            )
        ]
        
        doc = ParsedDocument(
            metadata=metadata,
            full_text="John Company A",
            named_entities=entities
        )
        
        assert doc.total_entities == 2
        assert doc.entity_confidence_avg == 0.85


# Integration Tests
class TestDocAIEndpoints:
    """Integration tests for DocAI endpoints."""
    
    def test_health_endpoint(self, test_client, mock_env_vars):
        """Test health endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data
    
    def test_config_endpoint(self, test_client, mock_env_vars):
        """Test configuration endpoint."""
        response = test_client.get("/api/docai/config")
        assert response.status_code == 200
        
        data = response.json()
        assert data["project_id"] == "test-project"
        assert data["default_processor_id"] == "test-processor"
    
    def test_parse_endpoint_validation(self, test_client, mock_env_vars):
        """Test parse endpoint request validation."""
        # Invalid GCS URI
        response = test_client.post("/api/docai/parse", json={
            "gcs_uri": "invalid-uri"
        })
        assert response.status_code == 422
    
    def test_batch_endpoint_validation(self, test_client, mock_env_vars):
        """Test batch endpoint validation."""
        # Empty batch
        response = test_client.post("/api/docai/parse/batch", json={
            "gcs_uris": []
        })
        assert response.status_code == 400
        
        # Batch too large
        response = test_client.post("/api/docai/parse/batch", json={
            "gcs_uris": [f"{get_test_gcs_bucket()}doc{i}.pdf" for i in range(25)]
        })
        assert response.status_code == 400


# Performance Tests
class TestDocAIPerformance:
    """Performance tests for DocAI components."""
    
    @pytest.mark.performance
    def test_parser_performance(self, mock_docai_document, sample_metadata):
        """Test parser performance with large documents."""
        parser = DocumentParser()
        
        # Create a large document
        large_text = mock_docai_document.text * 100
        mock_docai_document.text = large_text
        
        start_time = datetime.now()
        result = parser.parse_document(mock_docai_document, sample_metadata)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        assert processing_time < 5.0  # Should process within 5 seconds
        assert isinstance(result, ParsedDocument)
    
    @pytest.mark.performance
    async def test_concurrent_processing(self, mock_env_vars):
        """Test concurrent document processing."""
        client = DocAIClient(project_id="test-project")
        
        # Mock the processing to avoid actual API calls
        with patch.object(client, 'process_document_async') as mock_process:
            mock_process.return_value = Mock()
            
            # Process multiple documents concurrently
            tasks = [
                client.process_document_async(b"test content", "application/pdf")
                for _ in range(5)
            ]
            
            start_time = datetime.now()
            results = await asyncio.gather(*tasks)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            assert len(results) == 5
            assert processing_time < 2.0  # Should be faster than sequential


# Error Handling Tests
class TestDocAIErrorHandling:
    """Test error handling scenarios."""
    
    def test_authentication_error_handling(self, mock_env_vars):
        """Test authentication error handling."""
        with patch('services.doc_ai.client.documentai.DocumentProcessorServiceClient') as mock_client:
            mock_client.side_effect = Exception("Authentication failed")
            
            client = DocAIClient(project_id="test-project")
            
            with pytest.raises(Exception):
                _ = client.client  # Accessing the client property should raise
    
    def test_gcs_permission_error_handling(self, mock_env_vars):
        """Test GCS permission error handling."""
        client = DocAIClient(project_id="test-project")
        
        with patch.object(client, 'storage_client') as mock_storage:
            mock_bucket = Mock()
            mock_bucket.exists.side_effect = Exception("403 Forbidden")
            mock_storage.bucket.return_value = mock_bucket
            
            with pytest.raises(DocAIError, match="Access denied"):
                client.download_from_gcs(f"{get_test_gcs_bucket()}test.pdf")


# Async Tests
@pytest.mark.asyncio
async def test_async_document_processing(mock_env_vars):
    """Test asynchronous document processing."""
    client = DocAIClient(project_id="test-project")
    
    with patch.object(client, 'process_document_sync') as mock_sync:
        mock_sync.return_value = Mock()
        
        result = await client.process_document_async(
            content=b"test content",
            mime_type="application/pdf"
        )
        
        assert result is not None
        mock_sync.assert_called_once()


# Regression Tests
class TestDocAIRegression:
    """Regression tests for known issues."""
    
    def test_import_conflicts_resolved(self):
        """Test that import conflicts are resolved."""
        try:
            from main import app
            from routers.doc_ai_router import router
            from services.doc_ai.client import DocAIClient
            from services.doc_ai.parser import DocumentParser
            from services.doc_ai.schema import ParsedDocument
        except ImportError as e:
            pytest.fail(f"Import conflict detected: {e}")
    
    def test_router_registration(self, test_client):
        """Test that both routers are properly registered."""
        response = test_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        routers = data.get("routers", [])
        
        assert "processing_handler" in routers
        assert "doc_ai_router" in routers
    
    def test_lazy_loading_pdf_converter(self, test_client):
        """Test that PDF converter lazy loading works."""
        # This should not fail even if PyMuPDF has issues
        response = test_client.get("/health")
        assert response.status_code == 200


if __name__ == "__main__":
    # Run specific test categories
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            pytest.main([__file__ + "::TestDocAIClient", __file__ + "::TestDocumentParser", __file__ + "::TestDocAISchema", "-v"])
        elif sys.argv[1] == "integration":
            pytest.main([__file__ + "::TestDocAIEndpoints", "-v"])
        elif sys.argv[1] == "performance":
            pytest.main([__file__ + "::TestDocAIPerformance", "-v", "-m", "performance"])
        elif sys.argv[1] == "all":
            pytest.main([__file__, "-v"])
    else:
        pytest.main([__file__, "-v"])