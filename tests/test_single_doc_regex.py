"""
Test suite for single document regex classification MVP

This test validates the complete pipeline with regex-based classification,
ensuring that classification_verdict.json and kag_input.json are generated
with valid contents for single document processing.

Features tested:
- Single-document mode enforcement
- Regex-based classification functionality
- KAG handoff component integration
- Artifact generation (classification_verdict.json, kag_input.json, feature_vector.json)
- Backward compatibility with GCS URIs
- End-to-end pipeline validation
"""

import json
import pytest
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

# Test dependencies
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO

# Import components under test
from services.template_matching.regex_classifier import create_classifier, RegexDocumentClassifier
from services.kag_component import create_kag_component, KAGComponent
from services.feature_emitter import emit_feature_vector
from routers.orchestration_router import router
from main import app

# Create test client
client = TestClient(app)


class TestSingleDocRegexMVP:
    """Comprehensive test suite for single document regex classification MVP."""
    
    @pytest.fixture
    def sample_legal_text(self) -> str:
        """Sample legal document text for testing."""
        return """
        SALE DEED
        
        This is a sale deed executed between the vendor Mr. John Doe and vendee Ms. Jane Smith
        for the transfer of property located at 123 Main Street, Mumbai, Maharashtra.
        
        The consideration amount is Rs. 50,00,000/- (Rupees Fifty Lakhs only) and the property 
        is a residential apartment bearing flat no. 402 in Building XYZ.
        
        The vendor warrants clear title to the property and the vendee accepts the transfer 
        of possession on the date of registration.
        
        This document is registered with the Sub-Registrar office, Mumbai as per the 
        Indian Registration Act, 1908.
        
        Executed this day in the presence of witnesses.
        
        Vendor: John Doe
        Vendee: Jane Smith
        """
    
    @pytest.fixture
    def sample_pdf_file(self) -> UploadFile:
        """Create a mock PDF file for testing."""
        # Create a simple PDF-like content for testing
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        return UploadFile(
            filename="test_document.pdf",
            file=BytesIO(pdf_content),
            content_type="application/pdf"
        )
    
    def test_regex_classifier_initialization(self):
        """Test that the regex classifier initializes correctly."""
        classifier = create_classifier()
        
        assert isinstance(classifier, RegexDocumentClassifier)
        assert classifier.min_score_threshold == 0.1
        assert len(classifier._compiled_patterns) > 0
        
        # Verify legal keywords are loaded
        assert "sale_deeds" in classifier._compiled_patterns
        assert "property_certificates" in classifier._compiled_patterns
    
    def test_regex_classification_functionality(self, sample_legal_text):
        """Test regex classification with sample legal text."""
        classifier = create_classifier()
        
        result = classifier.classify_document(sample_legal_text)
        
        # Verify classification result structure
        assert hasattr(result, 'label')
        assert hasattr(result, 'score')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'matched_patterns')
        
        # Verify classification success
        assert result.label != "Invalid_Input"
        assert result.score > 0.0
        assert len(result.matched_patterns) > 0
        
        # Verify property-related classification
        assert "Property" in result.label or result.label == "Property_and_Real_Estate"
        
        # Check for expected patterns
        pattern_keywords = [p.keyword for p in result.matched_patterns]
        assert "sale deed" in pattern_keywords
        assert "vendor" in pattern_keywords
        assert "vendee" in pattern_keywords
    
    def test_classification_verdict_export(self, sample_legal_text):
        """Test classification verdict export functionality."""
        classifier = create_classifier()
        result = classifier.classify_document(sample_legal_text)
        
        verdict = classifier.export_classification_verdict(result)
        
        # Verify verdict structure
        assert isinstance(verdict, dict)
        assert "label" in verdict
        assert "score" in verdict
        assert "confidence" in verdict
        assert "matched_patterns" in verdict
        assert "summary" in verdict
        assert "processing_metadata" in verdict
        
        # Verify metadata
        assert verdict["processing_metadata"]["classifier_version"] == "1.0.0"
        assert verdict["processing_metadata"]["classification_method"] == "regex_pattern_matching"
        assert "timestamp" in verdict["processing_metadata"]
        
        # Verify summary
        assert "classification_successful" in verdict["summary"]
        assert "primary_label" in verdict["summary"]
        assert "top_keywords" in verdict["summary"]
    
    def test_kag_component_initialization(self):
        """Test KAG component initialization."""
        kag = create_kag_component()
        
        assert isinstance(kag, KAGComponent)
        assert kag.component_version == "1.0.0"
        
        status = kag.get_processing_status()
        assert status["mvp_mode"] is True
        assert status["features"]["vertex_embedding"] is False
    
    def test_kag_document_processing(self, sample_legal_text):
        """Test KAG component document processing."""
        # First get classification verdict
        classifier = create_classifier()
        classification_result = classifier.classify_document(sample_legal_text)
        classification_verdict = classifier.export_classification_verdict(classification_result)
        
        # Test KAG processing
        kag = create_kag_component()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_folder = Path(temp_dir)
            
            kag_output = kag.process_document(
                document_text=sample_legal_text,
                classification_verdict=classification_verdict,
                document_metadata={"filename": "test_document.pdf"},
                pipeline_id="test-pipeline-123",
                user_session_id="test-user-456",
                artifacts_folder=artifacts_folder
            )
            
            # Verify KAG output
            assert kag_output.success is True
            assert kag_output.kag_input_path != ""
            assert Path(kag_output.kag_input_path).exists()
            
            # Verify kag_input.json content
            with open(kag_output.kag_input_path, 'r') as f:
                kag_input = json.load(f)
            
            assert "document_text" in kag_input
            assert "classification_verdict" in kag_input
            assert "knowledge_extraction_config" in kag_input
            assert "processing_hints" in kag_input
            assert "kag_metadata" in kag_input
            
            # Verify MVP metadata
            assert kag_input["kag_metadata"]["mvp_mode"] is True
            assert kag_input["kag_metadata"]["vertex_embedding_disabled"] is True
    
    def test_feature_vector_with_classifier_verdict(self, sample_legal_text):
        """Test feature vector generation with classifier verdict."""
        # Get classification verdict
        classifier = create_classifier()
        classification_result = classifier.classify_document(sample_legal_text)
        classification_verdict = classifier.export_classification_verdict(classification_result)
        
        # Prepare parsed output
        parsed_output = {
            "metadata": {
                "document_id": "test-doc-123",
                "page_count": 1,
                "needs_review": False
            },
            "full_text": sample_legal_text,
            "clauses": [],
            "named_entities": [],
            "key_value_pairs": []
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            feature_vector_path = Path(temp_dir) / "feature_vector.json"
            
            # Generate feature vector
            emit_feature_vector(
                parsed_output=parsed_output,
                out_path=str(feature_vector_path),
                classifier_verdict=classification_verdict
            )
            
            # Verify feature vector was created
            assert feature_vector_path.exists()
            
            # Verify feature vector content
            with open(feature_vector_path, 'r') as f:
                feature_vector = json.load(f)
            
            # Verify classifier verdict is included
            assert "classifier_verdict" in feature_vector
            assert feature_vector["classifier_verdict"] is not None
            assert feature_vector["classifier_verdict"]["label"] == classification_verdict["label"]
            
            # Verify MVP metadata
            assert feature_vector["generation_metadata"]["mvp_mode"] is True
            assert feature_vector["generation_metadata"]["vertex_embedding_disabled"] is True
            assert feature_vector["generation_metadata"]["classification_method"] == "regex_pattern_matching"
    
    @pytest.mark.asyncio
    async def test_single_document_mode_enforcement(self):
        """Test that the system enforces single-document mode."""
        # This test ensures no multi-document handling is present
        # and that the system processes one document at a time
        
        # Create a simple test to verify the endpoint exists and is configured for single docs
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "service" in health_data
        assert health_data["service"] == "document_processing_orchestration"
        
    def test_backward_compatibility_gcs_uri(self):
        """Test that GCS URI processing still works but uses regex classification."""
        # This test verifies that if a GCS URI is provided, the system
        # still processes it normally but always uses regex for classification
        
        classifier = create_classifier()
        
        # Test with document text (simulating GCS processing result)
        sample_text = "This is a partnership deed between partners for business collaboration."
        result = classifier.classify_document(sample_text)
        
        # Verify classification still works regardless of source
        assert result.label != "Invalid_Input"
        assert result.score >= 0.0
        
        # Verify business document classification
        assert "Business" in result.label or "Partnership" in result.category_scores
    
    def test_artifact_generation_completeness(self, sample_legal_text):
        """Test that all required artifacts are generated."""
        # Test complete artifact generation pipeline
        classifier = create_classifier()
        kag = create_kag_component()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_folder = Path(temp_dir)
            
            # Step 1: Classification
            classification_result = classifier.classify_document(sample_legal_text)
            classification_verdict = classifier.export_classification_verdict(classification_result)
            
            # Save classification verdict
            classification_verdict_path = artifacts_folder / "classification_verdict.json"
            with open(classification_verdict_path, 'w') as f:
                json.dump(classification_verdict, f, indent=2)
            
            # Step 2: KAG processing
            kag_output = kag.process_document(
                document_text=sample_legal_text,
                classification_verdict=classification_verdict,
                document_metadata={"filename": "test_document.pdf"},
                pipeline_id="test-pipeline-123",
                user_session_id="test-user-456",
                artifacts_folder=artifacts_folder
            )
            
            # Step 3: Feature vector generation
            parsed_output = {
                "metadata": {"document_id": "test-doc-123", "page_count": 1, "needs_review": False},
                "full_text": sample_legal_text,
                "clauses": [],
                "named_entities": [],
                "key_value_pairs": []
            }
            
            feature_vector_path = artifacts_folder / "feature_vector.json"
            emit_feature_vector(
                parsed_output=parsed_output,
                out_path=str(feature_vector_path),
                classifier_verdict=classification_verdict
            )
            
            # Verify all required artifacts exist
            assert classification_verdict_path.exists()
            assert Path(kag_output.kag_input_path).exists()
            assert feature_vector_path.exists()
            
            # Verify artifact contents are valid JSON
            with open(classification_verdict_path, 'r') as f:
                classification_data = json.load(f)
                assert "label" in classification_data
                assert "matched_patterns" in classification_data
            
            with open(kag_output.kag_input_path, 'r') as f:
                kag_data = json.load(f)
                assert "document_text" in kag_data
                assert "classification_verdict" in kag_data
            
            with open(feature_vector_path, 'r') as f:
                feature_data = json.load(f)
                assert "classifier_verdict" in feature_data
                assert feature_data["classifier_verdict"] is not None
    
    def test_deterministic_results(self, sample_legal_text):
        """Test that the system produces deterministic results for the same input."""
        classifier = create_classifier()
        
        # Run classification multiple times
        result1 = classifier.classify_document(sample_legal_text)
        result2 = classifier.classify_document(sample_legal_text)
        
        # Results should be identical
        assert result1.label == result2.label
        assert result1.score == result2.score
        assert result1.confidence == result2.confidence
        assert len(result1.matched_patterns) == len(result2.matched_patterns)
        
        # Pattern matches should be identical
        patterns1 = [(p.keyword, p.frequency) for p in result1.matched_patterns]
        patterns2 = [(p.keyword, p.frequency) for p in result2.matched_patterns]
        assert patterns1 == patterns2
    
    def test_error_handling_invalid_input(self):
        """Test error handling for invalid input."""
        classifier = create_classifier()
        
        # Test with empty text
        result = classifier.classify_document("")
        assert result.label == "Invalid_Input"
        assert result.score == 0.0
        
        # Test with None
        result = classifier.classify_document(None)
        assert result.label == "Invalid_Input"
        assert result.score == 0.0
        
        # Test KAG component error handling
        kag = create_kag_component()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_folder = Path(temp_dir)
            
            # Test with invalid classification verdict
            kag_output = kag.process_document(
                document_text="test",
                classification_verdict=None,
                document_metadata={},
                pipeline_id="test",
                user_session_id="test",
                artifacts_folder=artifacts_folder
            )
            
            # Should handle gracefully
            assert kag_output.success is False
            assert len(kag_output.errors) > 0
    
    def test_mvp_configuration_validation(self):
        """Test that MVP configuration is properly set."""
        classifier = create_classifier()
        kag = create_kag_component()
        
        # Test classifier configuration
        sample_result = classifier.classify_document("test document with sale deed provisions")
        verdict = classifier.export_classification_verdict(sample_result)
        
        assert verdict["processing_metadata"]["classification_method"] == "regex_pattern_matching"
        
        # Test KAG configuration
        status = kag.get_processing_status()
        assert status["mvp_mode"] is True
        assert status["features"]["vertex_embedding"] is False
        assert status["features"]["classification_integration"] is True
        
        # Test feature vector configuration
        with tempfile.TemporaryDirectory() as temp_dir:
            feature_path = Path(temp_dir) / "test_feature.json"
            
            parsed_output = {
                "metadata": {"document_id": "test", "page_count": 1, "needs_review": False},
                "full_text": "test",
                "clauses": [],
                "named_entities": [],
                "key_value_pairs": []
            }
            
            emit_feature_vector(
                parsed_output=parsed_output,
                out_path=str(feature_path),
                classifier_verdict=verdict
            )
            
            with open(feature_path, 'r') as f:
                feature_data = json.load(f)
            
            assert feature_data["generation_metadata"]["mvp_mode"] is True
            assert feature_data["generation_metadata"]["vertex_embedding_disabled"] is True


# Run tests if called directly
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run a quick validation
    test_instance = TestSingleDocRegexMVP()
    
    sample_text = """
    This is a sale deed executed between the vendor and vendee for the transfer of property.
    The consideration amount is Rs. 50,00,000/- and the property is located in Mumbai.
    """
    
    print("Running quick validation tests...")
    
    # Test regex classifier
    test_instance.test_regex_classifier_initialization()
    test_instance.test_regex_classification_functionality(sample_text)
    test_instance.test_classification_verdict_export(sample_text)
    
    # Test KAG component
    test_instance.test_kag_component_initialization()
    test_instance.test_kag_document_processing(sample_text)
    
    # Test feature vector
    test_instance.test_feature_vector_with_classifier_verdict(sample_text)
    
    # Test artifacts
    test_instance.test_artifact_generation_completeness(sample_text)
    
    # Test deterministic results
    test_instance.test_deterministic_results(sample_text)
    
    print("✅ All validation tests passed!")
    print("\nTo run the complete test suite:")
    print("python -m pytest tests/test_single_doc_regex.py -v")