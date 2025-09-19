"""
Comprehensive tests for DocAI integration.

Tests cover unit and integration testing for the DocAI client, parser,
and FastAPI router with mocked DocAI responses.
"""

import json
import os
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

# FastAPI and HTTP testing
from fastapi.testclient import TestClient
import httpx

# Import DocAI components
from services.doc_ai import (
    DocAIClient,
    DocumentParser,
    ParseRequest,
    ParseResponse,
    ParsedDocument,
    DocumentMetadata,
    Clause,
    NamedEntity,
    KeyValuePair,
    CrossReference,
    EntityType,
    ClauseType,
    TextSpan,
    BoundingBox
)

from services.doc_ai.client import (
    DocAIError,
    DocAIAuthenticationError,
    DocAIProcessingError
)

# Import router for integration tests
from routers.doc_ai_router import router
from main import app


def get_test_gcs_bucket() -> str:
    """Get GCS test bucket from environment, with fallback."""
    bucket = os.getenv('GCS_TEST_BUCKET', 'gs://test-bucket/')
    return bucket.rstrip('/') + '/'


class TestDocAIClient:
    """Test suite for DocAI client."""
    
    @pytest.fixture
    def mock_documentai_client(self):
        """Mock DocumentAI client."""
        with patch('services.doc_ai.client.documentai.DocumentProcessorServiceClient') as mock:
            client_instance = Mock()
            mock.return_value = client_instance
            mock.from_service_account_file.return_value = client_instance
            yield client_instance
    
    @pytest.fixture
    def mock_storage_client(self):
        """Mock Storage client."""
        with patch('services.doc_ai.client.storage.Client') as mock:
            client_instance = Mock()
            mock.return_value = client_instance
            mock.from_service_account_json.return_value = client_instance
            yield client_instance
    
    @pytest.fixture
    def docai_client(self, mock_documentai_client, mock_storage_client):
        """DocAI client instance for testing."""
        return DocAIClient(
            project_id="test-project",
            location="us",
            processor_id="test-processor",
            credentials_path="/path/to/test-credentials.json"
        )
    
    @pytest.fixture
    def mock_docai_document(self):
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
                type_="ORGANIZATION", 
                confidence=0.93,
                mention_text="Company B",
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
    
    def test_client_initialization(self, docai_client):
        """Test DocAI client initialization."""
        assert docai_client.project_id == "test-project"
        assert docai_client.location == "us"
        assert docai_client.default_processor_id == "test-processor"
        assert docai_client.credentials_path == "/path/to/test-credentials.json"
    
    def test_get_processor_name(self, docai_client, mock_documentai_client):
        """Test processor name generation."""
        mock_documentai_client.processor_path.return_value = "projects/test-project/locations/us/processors/test-processor"
        
        processor_name = docai_client.get_processor_name()
        
        mock_documentai_client.processor_path.assert_called_once_with(
            "test-project", "us", "test-processor"
        )
        assert processor_name == "projects/test-project/locations/us/processors/test-processor"
    
    def test_download_from_gcs(self, docai_client, mock_storage_client):
        """Test GCS download functionality."""
        # Setup mock
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.return_value = b"test content"
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.bucket.return_value = mock_bucket
        
        # Test download
        content = docai_client.download_from_gcs(f"{get_test_gcs_bucket()}test-file.pdf")
        
        assert content == b"test content"
        bucket_name = get_test_gcs_bucket().replace('gs://', '').rstrip('/')
        mock_storage_client.bucket.assert_called_once_with(bucket_name)
        mock_bucket.blob.assert_called_once_with("test-file.pdf")
        mock_blob.download_as_bytes.assert_called_once()
    
    def test_download_from_gcs_invalid_uri(self, docai_client):
        """Test GCS download with invalid URI."""
        with pytest.raises(DocAIError, match="Invalid GCS URI"):
            docai_client.download_from_gcs("invalid-uri")
    
    def test_download_from_gcs_file_not_found(self, docai_client, mock_storage_client):
        """Test GCS download when file doesn't exist."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.bucket.return_value = mock_bucket
        
        with pytest.raises(DocAIError, match="File not found"):
            docai_client.download_from_gcs(f"{get_test_gcs_bucket()}missing-file.pdf")
    
    def test_process_document_sync(self, docai_client, mock_documentai_client, mock_docai_document):
        """Test synchronous document processing."""
        # Setup mock response
        mock_response = Mock()
        mock_response.document = mock_docai_document
        mock_documentai_client.process_document.return_value = mock_response
        mock_documentai_client.processor_path.return_value = "test-processor-path"
        
        # Test processing
        result = docai_client.process_document_sync(
            content=b"test content",
            mime_type="application/pdf"
        )
        
        assert result == mock_docai_document
        mock_documentai_client.process_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_async(self, docai_client, mock_documentai_client, mock_docai_document):
        """Test asynchronous document processing."""
        # Setup mock response
        mock_response = Mock()
        mock_response.document = mock_docai_document
        mock_documentai_client.process_document.return_value = mock_response
        mock_documentai_client.processor_path.return_value = "test-processor-path"
        
        # Test async processing
        result = await docai_client.process_document_async(
            content=b"test content",
            mime_type="application/pdf"
        )
        
        assert result == mock_docai_document


class TestDocumentParser:
    """Test suite for document parser."""
    
    @pytest.fixture
    def parser(self):
        """Document parser instance for testing."""
        return DocumentParser(confidence_threshold=0.7)
    
    @pytest.fixture
    def mock_docai_document(self):
        """Mock DocAI document for parsing tests."""
        mock_doc = Mock()
        mock_doc.text = "This contract between Company A and Company B specifies a payment of $50,000 due on 2024-01-15. This agreement shall terminate on December 31, 2024."
        
        # Mock entities
        mock_entities = [
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
            ),
            Mock(
                type_="DATE",
                confidence=0.92,
                mention_text="2024-01-15",
                page_anchor=Mock(page_refs=[Mock(page=0)])
            )
        ]
        mock_doc.entities = mock_entities
        
        # Mock pages with form fields
        mock_page = Mock()
        mock_field = Mock()
        mock_field.field_name = Mock(confidence=0.9)
        mock_field.field_value = Mock(confidence=0.9)
        mock_page.form_fields = [mock_field]
        mock_doc.pages = [mock_page]
        
        return mock_doc
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample document metadata."""
        return DocumentMetadata(
            document_id="test-doc-001",
            original_filename="test-contract.pdf",
            file_size=1024,
            page_count=1,
            language="en"
        )
    
    def test_parser_initialization(self, parser):
        """Test parser initialization."""
        assert parser.confidence_threshold == 0.7
        assert len(parser.entity_type_mapping) > 0
        assert len(parser.clause_patterns) > 0
    
    def test_extract_full_text(self, parser, mock_docai_document):
        """Test full text extraction."""
        text = parser._extract_full_text(mock_docai_document)
        assert "Company A" in text
        assert "$50,000" in text
        assert len(text) > 0
    
    def test_extract_entities(self, parser, mock_docai_document):
        """Test entity extraction."""
        full_text = mock_docai_document.text
        entities = parser._extract_entities(mock_docai_document, full_text)
        
        assert len(entities) == 3
        
        # Check entity types
        org_entities = [e for e in entities if e.type == EntityType.ORGANIZATION]
        money_entities = [e for e in entities if e.type == EntityType.MONEY]
        date_entities = [e for e in entities if e.type == EntityType.DATE]
        
        assert len(org_entities) == 1
        assert len(money_entities) == 1
        assert len(date_entities) == 1
        
        # Check confidence filtering
        for entity in entities:
            assert entity.confidence >= 0.7
    
    def test_detect_clauses(self, parser):
        """Test clause detection."""
        test_text = """
        This agreement shall terminate on December 31, 2024.
        
        Payment terms: All invoices must be paid within 30 days.
        
        Confidential Information shall not be disclosed to third parties.
        """
        
        mock_doc = Mock()
        mock_doc.text = test_text
        
        clauses = parser._detect_clauses(mock_doc, test_text)
        
        # Should detect termination and payment clauses
        clause_types = [c.type for c in clauses]
        assert ClauseType.TERMINATION in clause_types
        assert ClauseType.PAYMENT in clause_types
        assert ClauseType.CONFIDENTIALITY in clause_types
    
    def test_normalize_entity_value_date(self, parser):
        """Test date normalization."""
        normalized = parser._normalize_entity_value(EntityType.DATE, "January 15, 2024")
        assert "2024-01-15" in normalized
    
    def test_normalize_entity_value_money(self, parser):
        """Test money normalization."""
        normalized = parser._normalize_entity_value(EntityType.MONEY, "$50,000")
        assert normalized.startswith("USD:")
    
    def test_parse_document_integration(self, parser, mock_docai_document, sample_metadata):
        """Test complete document parsing integration."""
        parsed_doc = parser.parse_document(
            docai_document=mock_docai_document,
            metadata=sample_metadata,
            include_raw_response=True
        )
        
        assert isinstance(parsed_doc, ParsedDocument)
        assert parsed_doc.metadata == sample_metadata
        assert len(parsed_doc.full_text) > 0
        assert len(parsed_doc.named_entities) > 0
        assert parsed_doc.raw_docai_response is not None
        
        # Check properties
        assert parsed_doc.total_entities > 0
        assert 0 <= parsed_doc.entity_confidence_avg <= 1


class TestDocAIRouter:
    """Test suite for DocAI FastAPI router."""
    
    @pytest.fixture
    def client(self):
        """Test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT_ID': 'test-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/test-creds.json',
            'DOCAI_PROCESSOR_ID': 'test-processor',
            'DOCAI_LOCATION': 'us'
        }):
            yield
    
    @pytest.fixture
    def mock_docai_services(self):
        """Mock DocAI services."""
        with patch('routers.doc_ai_router.get_docai_client') as mock_client, \
             patch('routers.doc_ai_router.get_document_parser') as mock_parser:
            
            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            
            # Setup mock parser  
            mock_parser_instance = Mock()
            mock_parser.return_value = mock_parser_instance
            
            # Setup mock processing result
            mock_metadata = DocumentMetadata(
                document_id="test-doc-001",
                original_filename="test.pdf",
                file_size=1024,
                page_count=1,
                language="en"
            )
            
            mock_parsed_doc = ParsedDocument(
                metadata=mock_metadata,
                full_text="Test document text",
                named_entities=[],
                clauses=[],
                key_value_pairs=[],
                cross_references=[]
            )
            
            mock_client_instance.process_gcs_document_async.return_value = (Mock(), mock_metadata)
            mock_parser_instance.parse_document.return_value = mock_parsed_doc
            
            yield mock_client_instance, mock_parser_instance
    
    def test_health_check_success(self, client, mock_env_vars, mock_docai_services):
        """Test health check endpoint success."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "services" in data
        assert "environment" in data
    
    def test_parse_document_success(self, client, mock_env_vars, mock_docai_services):
        """Test successful document parsing."""
        request_data = {
            "gcs_uri": f"{get_test_gcs_bucket()}test-document.pdf",
            "confidence_threshold": 0.8,
            "include_raw_response": False
        }
        
        response = client.post("/api/docai/parse", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["document"] is not None
        assert "request_id" in data
        assert "processing_time_seconds" in data
    
    def test_parse_document_invalid_gcs_uri(self, client, mock_env_vars):
        """Test parsing with invalid GCS URI."""
        request_data = {
            "gcs_uri": "invalid-uri",
            "confidence_threshold": 0.8
        }
        
        response = client.post("/api/docai/parse", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_parse_document_authentication_error(self, client, mock_env_vars):
        """Test parsing with authentication error."""
        with patch('routers.doc_ai_router.get_docai_client') as mock_get_client:
            mock_get_client.side_effect = DocAIAuthenticationError("Auth failed")
            
            request_data = {
                "gcs_uri": f"{get_test_gcs_bucket()}test-document.pdf"
            }
            
            response = client.post("/api/docai/parse", json=request_data)
            
            assert response.status_code == 200  # Returns ParseResponse with success=False
            data = response.json()
            assert data["success"] is False
            assert "Authentication failed" in data["error_message"]
    
    def test_list_processors(self, client, mock_env_vars):
        """Test list processors endpoint."""
        response = client.get("/api/docai/processors")
        
        assert response.status_code == 200
        data = response.json()
        assert "processors" in data
        assert "project_id" in data
        assert "location" in data
    
    def test_get_configuration(self, client, mock_env_vars):
        """Test get configuration endpoint."""
        response = client.get("/api/docai/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "test-project"
        assert data["location"] == "us"
        assert data["default_processor_id"] == "test-processor"
    
    def test_parse_documents_batch(self, client, mock_env_vars, mock_docai_services):
        """Test batch document parsing."""
        gcs_uris = [
            f"{get_test_gcs_bucket()}doc1.pdf",
            f"{get_test_gcs_bucket()}doc2.pdf"
        ]
        
        response = client.post("/api/docai/parse/batch", json=gcs_uris)
        
        assert response.status_code == 200
        data = response.json()
        assert "batch_id" in data
        assert data["total_documents"] == 2
        assert "results" in data
        assert len(data["results"]) == 2
    
    def test_parse_documents_batch_size_limit(self, client, mock_env_vars):
        """Test batch size limit."""
        gcs_uris = [f"{get_test_gcs_bucket()}doc{i}.pdf" for i in range(15)]
        
        response = client.post("/api/docai/parse/batch", json=gcs_uris)
        
        assert response.status_code == 400
        assert "Batch size limited" in response.json()["detail"]


class TestSchemaValidation:
    """Test suite for Pydantic schema validation."""
    
    def test_parse_request_validation(self):
        """Test ParseRequest validation."""
        # Valid request
        request = ParseRequest(gcs_uri=f"{get_test_gcs_bucket()}test.pdf")
        assert request.gcs_uri == f"{get_test_gcs_bucket()}test.pdf"
        assert request.confidence_threshold == 0.7
        
        # Invalid GCS URI
        with pytest.raises(ValueError, match="GCS URI must start with gs://"):
            ParseRequest(gcs_uri="invalid-uri")
    
    def test_named_entity_normalization(self):
        """Test named entity value normalization."""
        text_span = TextSpan(start_offset=0, end_offset=10, text="2024-01-15")
        
        entity = NamedEntity(
            id="test-entity",
            type=EntityType.DATE,
            text_span=text_span,
            confidence=0.9,
            page_number=1
        )
        
        # Should normalize date
        assert entity.normalized_value is not None
    
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
                text_span=TextSpan(start_offset=0, end_offset=5, text="John"),
                confidence=0.9,
                page_number=1
            ),
            NamedEntity(
                id="e2", 
                type=EntityType.ORGANIZATION,
                text_span=TextSpan(start_offset=6, end_offset=15, text="Company A"),
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
        assert doc.clause_confidence_avg == 0.0  # No clauses


@pytest.mark.asyncio
async def test_integration_end_to_end():
    """Integration test for complete DocAI processing pipeline."""
    # This would test the complete flow from GCS URI to parsed document
    # In a real environment, this would use actual test documents in GCS
    
    with patch('services.doc_ai.client.DocAIClient.process_gcs_document_async') as mock_process:
        # Setup mock response
        mock_metadata = DocumentMetadata(
            document_id="integration-test",
            original_filename="test.pdf",
            file_size=2048,
            page_count=1,
            language="en"
        )
        
        mock_document = Mock()
        mock_document.text = "Integration test document"
        mock_document.entities = []
        mock_document.pages = []
        
        mock_process.return_value = (mock_document, mock_metadata)
        
        # Create client and parser
        client = DocAIClient("test-project", "us", "test-processor")
        parser = DocumentParser()
        
        # Process document
        gcs_uri = f"{get_test_gcs_bucket()}integration-test.pdf"
        docai_doc, metadata = await client.process_gcs_document_async(gcs_uri)
        parsed_doc = parser.parse_document(docai_doc, metadata)
        
        assert isinstance(parsed_doc, ParsedDocument)
        assert parsed_doc.metadata.document_id == "integration-test"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])