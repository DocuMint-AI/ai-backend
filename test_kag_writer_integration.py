"""
Integration Test for KAG Writer Pipeline

This script tests the integration of the new KAG writer into the document
processing pipeline, ensuring that all required files are generated correctly.

Test Coverage:
- Validates that parsed_output.json is created
- Validates that classification_verdict.json is created  
- Validates that kag_input.json is created with correct schema
- Verifies all files are in the same pipeline folder
- Tests the unified schema structure
"""

import json
import logging
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kag.kag_writer import generate_kag_input, validate_kag_input_file
from services.template_matching.regex_classifier import create_classifier


class TestKAGWriterPipelineIntegration(unittest.TestCase):
    """Integration tests for KAG writer pipeline functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample document text for processing
        self.sample_document_text = """
        SALE DEED
        
        This sale deed is executed between Mr. John Smith, the vendor, and Ms. Jane Doe, the vendee,
        for the property located at 123 Main Street, Mumbai, Maharashtra.
        
        The consideration amount is Rs. 50,00,000/- (Rupees Fifty Lakhs only).
        The vendor hereby transfers all rights, title, and interest in the property to the vendee.
        
        This document is registered with the Sub-Registrar office as per the Indian Registration Act.
        """
        
        # Sample DocAI-style parsed output
        self.sample_docai_output = {
            "text": self.sample_document_text.strip(),
            "clauses": [
                {
                    "type": "transfer_clause",
                    "text": "The vendor hereby transfers all rights, title, and interest in the property to the vendee",
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
                {"key": "consideration_amount", "value": "Rs. 50,00,000", "confidence": 0.90}
            ]
        }
    
    def test_complete_pipeline_file_generation(self):
        """Test that all required files are generated in the pipeline folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_folder = Path(temp_dir)
            
            logger.info(f"Testing complete pipeline in: {pipeline_folder}")
            
            # Step 1: Create DocAI output (parsed_output.json)
            parsed_output_path = pipeline_folder / "parsed_output.json"
            with open(parsed_output_path, 'w', encoding='utf-8') as f:
                json.dump(self.sample_docai_output, f, indent=2)
            
            logger.info("✅ Step 1: parsed_output.json created")
            
            # Step 2: Generate classification verdict using regex classifier
            classifier = create_classifier()
            classification_result = classifier.classify_document(self.sample_document_text)
            classification_verdict = classifier.export_classification_verdict(classification_result)
            
            classification_verdict_path = pipeline_folder / "classification_verdict.json"
            with open(classification_verdict_path, 'w', encoding='utf-8') as f:
                json.dump(classification_verdict, f, indent=2)
            
            logger.info("✅ Step 2: classification_verdict.json created")
            
            # Step 3: Generate KAG input using the new writer
            kag_input_path = generate_kag_input(
                artifact_dir=pipeline_folder,
                doc_id="integration-test-pipeline-123",
                processor_id="docai-integration-processor",
                gcs_uri="gs://integration-test-bucket/sale-deed.pdf",
                pipeline_version="v1",
                metadata={
                    "test_mode": True,
                    "integration_test": "pipeline_validation",
                    "source_system": "kag_writer_integration_test"
                }
            )
            
            logger.info("✅ Step 3: kag_input.json created")
            
            # Verify all three key files exist in the same folder
            required_files = ["parsed_output.json", "classification_verdict.json", "kag_input.json"]
            
            for filename in required_files:
                file_path = pipeline_folder / filename
                self.assertTrue(file_path.exists(), f"Required file missing: {filename}")
                
                # Verify file is not empty
                self.assertGreater(file_path.stat().st_size, 0, f"File is empty: {filename}")
            
            logger.info("✅ All required files present in pipeline folder")
            
            # Verify KAG input structure and content
            self._validate_kag_input_structure(kag_input_path)
            
            # Verify content matching between files
            self._validate_content_matching(
                parsed_output_path,
                classification_verdict_path, 
                kag_input_path
            )
            
            logger.info("✅ Integration test completed successfully")
    
    def _validate_kag_input_structure(self, kag_input_path: Path):
        """Validate the KAG input structure matches requirements."""
        with open(kag_input_path, 'r', encoding='utf-8') as f:
            kag_data = json.load(f)
        
        # Test required top-level keys
        required_top_level = ["document_id", "parsed_document", "classifier_verdict", "metadata"]
        for key in required_top_level:
            self.assertIn(key, kag_data, f"Missing required top-level key: {key}")
        
        # Test parsed_document structure
        parsed_doc = kag_data["parsed_document"]
        required_parsed_fields = ["full_text", "clauses", "named_entities", "key_value_pairs"]
        for field in required_parsed_fields:
            self.assertIn(field, parsed_doc, f"Missing parsed_document field: {field}")
        
        # Test classifier_verdict structure
        verdict = kag_data["classifier_verdict"]
        required_verdict_fields = ["label", "score", "confidence"]
        for field in required_verdict_fields:
            self.assertIn(field, verdict, f"Missing classifier_verdict field: {field}")
        
        # Test metadata structure
        metadata = kag_data["metadata"]
        required_metadata_fields = ["processor_id", "source", "pipeline_version", "timestamp"]
        for field in required_metadata_fields:
            self.assertIn(field, metadata, f"Missing metadata field: {field}")
        
        # Test nested source structure
        source = metadata["source"]
        self.assertIn("gcs_uri", source, "Missing metadata.source.gcs_uri")
        
        # Verify specific values
        self.assertEqual(kag_data["document_id"], "integration-test-pipeline-123")
        self.assertEqual(metadata["processor_id"], "docai-integration-processor")
        self.assertEqual(metadata["source"]["gcs_uri"], "gs://integration-test-bucket/sale-deed.pdf")
        self.assertEqual(metadata["pipeline_version"], "v1")
        
        # Verify custom metadata was included
        self.assertTrue(metadata.get("test_mode"))
        self.assertEqual(metadata.get("integration_test"), "pipeline_validation")
        
        logger.info("✅ KAG input structure validation passed")
    
    def _validate_content_matching(
        self, 
        parsed_output_path: Path,
        classification_verdict_path: Path,
        kag_input_path: Path
    ):
        """Validate that content matches between source files and KAG input."""
        # Load all files
        with open(parsed_output_path, 'r') as f:
            parsed_data = json.load(f)
        
        with open(classification_verdict_path, 'r') as f:
            verdict_data = json.load(f)
        
        with open(kag_input_path, 'r') as f:
            kag_data = json.load(f)
        
        # Verify parsed_document.full_text matches DocAI output text
        source_text = parsed_data["text"]
        kag_text = kag_data["parsed_document"]["full_text"]
        self.assertEqual(source_text, kag_text, "parsed_document.full_text doesn't match source")
        
        # Verify clause counts match
        source_clauses = len(parsed_data.get("clauses", []))
        kag_clauses = len(kag_data["parsed_document"].get("clauses", []))
        self.assertEqual(source_clauses, kag_clauses, "Clause count mismatch")
        
        # Verify entity counts match
        source_entities = len(parsed_data.get("named_entities", []))
        kag_entities = len(kag_data["parsed_document"].get("named_entities", []))
        self.assertEqual(source_entities, kag_entities, "Entity count mismatch")
        
        # Verify classifier verdict fields match
        verdict_fields = ["label", "score", "confidence"]
        for field in verdict_fields:
            source_value = verdict_data.get(field)
            kag_value = kag_data["classifier_verdict"].get(field)
            self.assertEqual(source_value, kag_value, f"Classifier verdict {field} mismatch")
        
        logger.info("✅ Content matching validation passed")
    
    def test_kag_input_validation(self):
        """Test that generated KAG input passes validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_folder = Path(temp_dir)
            
            # Create minimal test files
            parsed_output = {
                "text": "Simple test document about property sale",
                "clauses": [],
                "named_entities": [],
                "key_value_pairs": []
            }
            
            with open(pipeline_folder / "parsed_output.json", 'w') as f:
                json.dump(parsed_output, f)
            
            classifier = create_classifier()
            result = classifier.classify_document(parsed_output["text"])
            verdict = classifier.export_classification_verdict(result)
            
            with open(pipeline_folder / "classification_verdict.json", 'w') as f:
                json.dump(verdict, f)
            
            # Generate KAG input
            kag_input_path = generate_kag_input(
                artifact_dir=pipeline_folder,
                doc_id="validation-test"
            )
            
            # Validate using the built-in validator
            is_valid = validate_kag_input_file(kag_input_path)
            self.assertTrue(is_valid, "Generated KAG input failed validation")
            
            logger.info("✅ KAG input validation test passed")
    
    def test_error_handling(self):
        """Test error handling in pipeline integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_folder = Path(temp_dir)
            
            # Test with missing files
            with self.assertRaises(FileNotFoundError):
                generate_kag_input(
                    artifact_dir=pipeline_folder,
                    doc_id="error-test"
                )
            
            # Test with invalid JSON
            with open(pipeline_folder / "parsed_output.json", 'w') as f:
                f.write("invalid json")
            
            with open(pipeline_folder / "classification_verdict.json", 'w') as f:
                json.dump({"label": "test", "score": 0.5, "confidence": "medium"}, f)
            
            with self.assertRaises(ValueError):
                generate_kag_input(
                    artifact_dir=pipeline_folder,
                    doc_id="error-test"
                )
            
            logger.info("✅ Error handling test passed")


def run_integration_tests():
    """Run all integration tests."""
    logger.info("="*60)
    logger.info("STARTING KAG WRITER PIPELINE INTEGRATION TESTS")
    logger.info("="*60)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestKAGWriterPipelineIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    logger.info("="*60)
    logger.info("INTEGRATION TEST RESULTS")
    logger.info("="*60)
    
    if result.wasSuccessful():
        logger.info("✅ ALL INTEGRATION TESTS PASSED!")
        logger.info("The pipeline now correctly generates:")
        logger.info("  - parsed_output.json (DocAI output)")
        logger.info("  - classification_verdict.json (classifier output)")
        logger.info("  - kag_input.json (unified schema)")
        logger.info("All files are generated in the same pipeline folder.")
    else:
        logger.error("❌ SOME INTEGRATION TESTS FAILED!")
        logger.error(f"Failures: {len(result.failures)}")
        logger.error(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)