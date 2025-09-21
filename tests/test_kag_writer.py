"""
Unit Tests for KAG Writer

This module contains comprehensive unit tests for the KAG writer functionality,
ensuring that kag_input.json files are generated correctly from DocAI output
and classifier verdicts.

Test Coverage:
- Basic KAG input generation
- Schema validation
- Atomic file writing
- Error handling for missing/invalid files
- Edge cases and boundary conditions
"""

import json
import pytest
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kag.kag_writer import (
    generate_kag_input,
    validate_kag_input_file,
    get_kag_input_summary,
    _validate_kag_input_schema
)


class TestKAGWriter(unittest.TestCase):
    """Test suite for KAG writer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample parsed output (DocAI format)
        self.sample_parsed_output = {
            "text": "This is a sale deed executed between vendor and vendee for property transfer.",
            "clauses": [
                {
                    "type": "sale",
                    "text": "property sale clause",
                    "confidence": 0.9
                }
            ],
            "named_entities": [
                {
                    "text": "John Doe",
                    "type": "PERSON",
                    "confidence": 0.95
                },
                {
                    "text": "property",
                    "type": "ASSET",
                    "confidence": 0.85
                }
            ],
            "key_value_pairs": [
                {
                    "key": "document_type",
                    "value": "sale deed",
                    "confidence": 0.92
                },
                {
                    "key": "buyer",
                    "value": "John Doe",
                    "confidence": 0.88
                }
            ]
        }
        
        # Sample classification verdict
        self.sample_classification_verdict = {
            "label": "Property_and_Real_Estate",
            "score": 0.85,
            "confidence": "high",
            "matched_patterns": [
                {
                    "keyword": "sale deed",
                    "frequency": 1,
                    "subcategory": "sale_deeds"
                }
            ]
        }
    
    def test_basic_kag_input_generation(self):
        """Test basic KAG input generation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create input files
            self._create_input_files(temp_path)
            
            # Generate KAG input
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc-123",
                processor_id="test-processor-456",
                gcs_uri="gs://test-bucket/test-file.pdf",
                pipeline_version="v1"
            )
            
            # Verify file was created
            self.assertTrue(Path(kag_path).exists())
            self.assertEqual(Path(kag_path).name, "kag_input.json")
            
            # Verify content
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            # Check top-level structure
            self.assertIn("document_id", kag_data)
            self.assertIn("parsed_document", kag_data)
            self.assertIn("classifier_verdict", kag_data)
            self.assertIn("metadata", kag_data)
            
            # Check values
            self.assertEqual(kag_data["document_id"], "test-doc-123")
            self.assertEqual(kag_data["metadata"]["processor_id"], "test-processor-456")
            self.assertEqual(kag_data["metadata"]["source"]["gcs_uri"], "gs://test-bucket/test-file.pdf")
            self.assertEqual(kag_data["metadata"]["pipeline_version"], "v1")
    
    def test_parsed_document_structure(self):
        """Test that parsed_document structure is correct."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc"
            )
            
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            parsed_doc = kag_data["parsed_document"]
            
            # Check required fields
            self.assertIn("full_text", parsed_doc)
            self.assertIn("clauses", parsed_doc)
            self.assertIn("named_entities", parsed_doc)
            self.assertIn("key_value_pairs", parsed_doc)
            
            # Check content matches source
            self.assertEqual(parsed_doc["full_text"], self.sample_parsed_output["text"])
            self.assertEqual(len(parsed_doc["clauses"]), len(self.sample_parsed_output["clauses"]))
            self.assertEqual(len(parsed_doc["named_entities"]), len(self.sample_parsed_output["named_entities"]))
            self.assertEqual(len(parsed_doc["key_value_pairs"]), len(self.sample_parsed_output["key_value_pairs"]))
    
    def test_classifier_verdict_structure(self):
        """Test that classifier_verdict structure is correct."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc"
            )
            
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            verdict = kag_data["classifier_verdict"]
            
            # Check required fields
            self.assertIn("label", verdict)
            self.assertIn("score", verdict)
            self.assertIn("confidence", verdict)
            
            # Check content matches source
            self.assertEqual(verdict["label"], self.sample_classification_verdict["label"])
            self.assertEqual(verdict["score"], self.sample_classification_verdict["score"])
            self.assertEqual(verdict["confidence"], self.sample_classification_verdict["confidence"])
    
    def test_metadata_structure(self):
        """Test that metadata structure is complete."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc",
                processor_id="proc-123",
                gcs_uri="gs://bucket/file.pdf",
                pipeline_version="v1.1",
                metadata={"custom_field": "custom_value"}
            )
            
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            metadata = kag_data["metadata"]
            
            # Check required fields
            self.assertIn("processor_id", metadata)
            self.assertIn("source", metadata)
            self.assertIn("pipeline_version", metadata)
            self.assertIn("timestamp", metadata)
            
            # Check values
            self.assertEqual(metadata["processor_id"], "proc-123")
            self.assertEqual(metadata["source"]["gcs_uri"], "gs://bucket/file.pdf")
            self.assertEqual(metadata["pipeline_version"], "v1.1")
            self.assertIn("custom_field", metadata)
            self.assertEqual(metadata["custom_field"], "custom_value")
            
            # Check timestamp format (ISO8601)
            self.assertRegex(metadata["timestamp"], r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z')
    
    def test_atomic_file_writing(self):
        """Test that files are written atomically using .tmp pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc"
            )
            
            # Verify final file exists
            self.assertTrue(Path(kag_path).exists())
            
            # Verify no .tmp file left behind
            tmp_files = list(temp_path.glob("*.tmp"))
            self.assertEqual(len(tmp_files), 0)
    
    def test_missing_parsed_output_file(self):
        """Test error handling when parsed_output.json is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Only create classification_verdict.json
            with open(temp_path / "classification_verdict.json", 'w') as f:
                json.dump(self.sample_classification_verdict, f)
            
            with self.assertRaises(FileNotFoundError) as context:
                generate_kag_input(
                    artifact_dir=temp_path,
                    doc_id="test-doc"
                )
            
            self.assertIn("parsed_output.json not found", str(context.exception))
    
    def test_missing_classification_verdict_file(self):
        """Test error handling when classification_verdict.json is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Only create parsed_output.json
            with open(temp_path / "parsed_output.json", 'w') as f:
                json.dump(self.sample_parsed_output, f)
            
            with self.assertRaises(FileNotFoundError) as context:
                generate_kag_input(
                    artifact_dir=temp_path,
                    doc_id="test-doc"
                )
            
            self.assertIn("classification_verdict.json not found", str(context.exception))
    
    def test_invalid_json_files(self):
        """Test error handling for invalid JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create invalid JSON files
            with open(temp_path / "parsed_output.json", 'w') as f:
                f.write("invalid json content")
            
            with open(temp_path / "classification_verdict.json", 'w') as f:
                json.dump(self.sample_classification_verdict, f)
            
            with self.assertRaises(ValueError) as context:
                generate_kag_input(
                    artifact_dir=temp_path,
                    doc_id="test-doc"
                )
            
            self.assertIn("Invalid JSON", str(context.exception))
    
    def test_missing_required_fields(self):
        """Test error handling for missing required fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create parsed_output.json missing 'text' field
            invalid_parsed = {"clauses": []}
            with open(temp_path / "parsed_output.json", 'w') as f:
                json.dump(invalid_parsed, f)
            
            with open(temp_path / "classification_verdict.json", 'w') as f:
                json.dump(self.sample_classification_verdict, f)
            
            with self.assertRaises(ValueError) as context:
                generate_kag_input(
                    artifact_dir=temp_path,
                    doc_id="test-doc"
                )
            
            self.assertIn("missing required field 'text'", str(context.exception))
    
    def test_schema_validation(self):
        """Test schema validation functionality."""
        # Test valid schema
        valid_schema = {
            "document_id": "test",
            "parsed_document": {
                "full_text": "test",
                "clauses": [],
                "named_entities": [],
                "key_value_pairs": []
            },
            "classifier_verdict": {
                "label": "test",
                "score": 0.5,
                "confidence": "medium"
            },
            "metadata": {
                "processor_id": "test",
                "source": {"gcs_uri": "test"},
                "pipeline_version": "v1",
                "timestamp": "2023-01-01T00:00:00Z"
            }
        }
        
        # Should not raise exception
        _validate_kag_input_schema(valid_schema)
        
        # Test invalid schema (missing document_id)
        invalid_schema = valid_schema.copy()
        del invalid_schema["document_id"]
        
        with self.assertRaises(ValueError) as context:
            _validate_kag_input_schema(invalid_schema)
        
        self.assertIn("missing required top-level key: document_id", str(context.exception))
    
    def test_validate_kag_input_file(self):
        """Test file validation utility function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            # Generate valid KAG input
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc"
            )
            
            # Test validation
            self.assertTrue(validate_kag_input_file(kag_path))
            
            # Test with non-existent file
            self.assertFalse(validate_kag_input_file(temp_path / "nonexistent.json"))
    
    def test_get_kag_input_summary(self):
        """Test KAG input summary utility function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc-456",
                processor_id="proc-789"
            )
            
            summary = get_kag_input_summary(kag_path)
            
            # Check summary fields
            self.assertEqual(summary["document_id"], "test-doc-456")
            self.assertEqual(summary["processor_id"], "proc-789")
            self.assertEqual(summary["classification_label"], "Property_and_Real_Estate")
            self.assertEqual(summary["classification_score"], 0.85)
            self.assertEqual(summary["classification_confidence"], "high")
            self.assertGreater(summary["text_length"], 0)
            self.assertGreaterEqual(summary["clause_count"], 0)
            self.assertGreaterEqual(summary["entity_count"], 0)
            self.assertGreaterEqual(summary["kv_pair_count"], 0)
    
    def test_default_values(self):
        """Test default values when optional parameters are not provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self._create_input_files(temp_path)
            
            # Generate with minimal parameters
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="test-doc"
            )
            
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            metadata = kag_data["metadata"]
            
            # Check default values
            self.assertEqual(metadata["processor_id"], "unknown")
            self.assertEqual(metadata["pipeline_version"], "v1")
            self.assertIn("file://local/test-doc.pdf", metadata["source"]["gcs_uri"])
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test with minimal valid data
            minimal_parsed = {
                "text": "",  # Empty text
                "clauses": [],
                "named_entities": [],
                "key_value_pairs": []
            }
            
            minimal_verdict = {
                "label": "",  # Empty label
                "score": 0.0,
                "confidence": "very_low"
            }
            
            with open(temp_path / "parsed_output.json", 'w') as f:
                json.dump(minimal_parsed, f)
            
            with open(temp_path / "classification_verdict.json", 'w') as f:
                json.dump(minimal_verdict, f)
            
            # Should still generate valid KAG input
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="edge-case-test"
            )
            
            # Verify it's valid
            self.assertTrue(validate_kag_input_file(kag_path))
            
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            # Check that empty values are preserved
            self.assertEqual(kag_data["parsed_document"]["full_text"], "")
            self.assertEqual(kag_data["classifier_verdict"]["label"], "")
            self.assertEqual(kag_data["classifier_verdict"]["score"], 0.0)
    
    def _create_input_files(self, temp_path: Path):
        """Helper method to create sample input files."""
        # Create parsed_output.json
        with open(temp_path / "parsed_output.json", 'w') as f:
            json.dump(self.sample_parsed_output, f, indent=2)
        
        # Create classification_verdict.json
        with open(temp_path / "classification_verdict.json", 'w') as f:
            json.dump(self.sample_classification_verdict, f, indent=2)


# Additional integration test
class TestKAGWriterIntegration(unittest.TestCase):
    """Integration tests for KAG writer with realistic data."""
    
    def test_realistic_document_processing(self):
        """Test with realistic document processing data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Realistic DocAI output
            realistic_parsed = {
                "text": "SALE DEED\n\nThis deed of sale is executed on this day between Mr. John Smith (Vendor) and Ms. Jane Doe (Vendee) for the property located at 123 Main Street, Mumbai. The consideration amount is Rs. 50,00,000/-. The vendor hereby transfers all rights and title to the vendee.",
                "clauses": [
                    {
                        "type": "transfer_clause",
                        "text": "The vendor hereby transfers all rights and title to the vendee",
                        "confidence": 0.92
                    },
                    {
                        "type": "consideration_clause", 
                        "text": "The consideration amount is Rs. 50,00,000/-",
                        "confidence": 0.89
                    }
                ],
                "named_entities": [
                    {"text": "John Smith", "type": "PERSON", "confidence": 0.95},
                    {"text": "Jane Doe", "type": "PERSON", "confidence": 0.94},
                    {"text": "123 Main Street, Mumbai", "type": "ADDRESS", "confidence": 0.88},
                    {"text": "Rs. 50,00,000", "type": "MONEY", "confidence": 0.91}
                ],
                "key_value_pairs": [
                    {"key": "vendor", "value": "John Smith", "confidence": 0.93},
                    {"key": "vendee", "value": "Jane Doe", "confidence": 0.92},
                    {"key": "property_address", "value": "123 Main Street, Mumbai", "confidence": 0.87},
                    {"key": "consideration_amount", "value": "Rs. 50,00,000", "confidence": 0.90}
                ]
            }
            
            # Realistic classifier verdict
            realistic_verdict = {
                "label": "Property_and_Real_Estate",
                "score": 0.92,
                "confidence": "high",
                "total_matches": 15,
                "matched_patterns": [
                    {"keyword": "sale deed", "frequency": 1, "subcategory": "sale_deeds"},
                    {"keyword": "vendor", "frequency": 2, "subcategory": "sale_deeds"},
                    {"keyword": "vendee", "frequency": 2, "subcategory": "sale_deeds"},
                    {"keyword": "property", "frequency": 1, "subcategory": "property_certificates"}
                ],
                "category_scores": {
                    "Property_and_Real_Estate": 0.92,
                    "Business_and_Corporate": 0.15,
                    "Judicial_Documents": 0.08
                }
            }
            
            # Create input files
            with open(temp_path / "parsed_output.json", 'w') as f:
                json.dump(realistic_parsed, f, indent=2)
            
            with open(temp_path / "classification_verdict.json", 'w') as f:
                json.dump(realistic_verdict, f, indent=2)
            
            # Generate KAG input
            kag_path = generate_kag_input(
                artifact_dir=temp_path,
                doc_id="sale-deed-12345",
                processor_id="docai-processor-real-estate",
                gcs_uri="gs://legal-docs-bucket/sale-deeds/smith-doe-2023.pdf",
                pipeline_version="v1.2",
                metadata={
                    "document_type": "sale_deed",
                    "processing_priority": "high",
                    "source_system": "legal_document_manager"
                }
            )
            
            # Validate generated file
            self.assertTrue(validate_kag_input_file(kag_path))
            
            # Get summary and verify
            summary = get_kag_input_summary(kag_path)
            
            self.assertEqual(summary["document_id"], "sale-deed-12345")
            self.assertEqual(summary["classification_label"], "Property_and_Real_Estate")
            self.assertEqual(summary["classification_score"], 0.92)
            self.assertEqual(summary["classification_confidence"], "high")
            self.assertGreater(summary["text_length"], 200)  # Realistic text length
            self.assertEqual(summary["clause_count"], 2)
            self.assertEqual(summary["entity_count"], 4)
            self.assertEqual(summary["kv_pair_count"], 4)
            
            # Verify custom metadata was included
            with open(kag_path, 'r') as f:
                kag_data = json.load(f)
            
            metadata = kag_data["metadata"]
            self.assertEqual(metadata["document_type"], "sale_deed")
            self.assertEqual(metadata["processing_priority"], "high")
            self.assertEqual(metadata["source_system"], "legal_document_manager")


def run_tests():
    """Run all tests and return success status."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestKAGWriter))
    suite.addTests(loader.loadTestsFromTestCase(TestKAGWriterIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    
    if success:
        print("\n✅ All KAG Writer tests passed!")
    else:
        print("\n❌ Some KAG Writer tests failed!")
    
    exit(0 if success else 1)