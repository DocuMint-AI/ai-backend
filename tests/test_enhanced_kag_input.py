"""
Enhanced KAG Input Validation Test Suite

This script validates that the pipeline generates correct kag_input.json files
that pair DocAI output with classifier verdicts and include proper metadata.

Test Coverage:
- Validates kag_input.json structure and schema compliance
- Cross-validates content with source files (parsed_output.json, classification_verdict.json)
- Checks for required metadata fields (document_id, processor_id, audit, source.gcs_uri)
- Verifies content matching between source and generated files
- Tests error handling for missing or malformed files
"""

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import components under test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kag_input_enhanced import create_kag_input_generator, create_kag_input_validator
from services.template_matching.regex_classifier import create_classifier


class EnhancedKAGInputTests:
    """Comprehensive test suite for enhanced KAG input functionality."""
    
    def __init__(self):
        """Initialize test suite."""
        self.generator = create_kag_input_generator()
        self.validator = create_kag_input_validator()
        self.test_results = []
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall success status."""
        logger.info("Starting Enhanced KAG Input Test Suite")
        
        tests = [
            self.test_kag_input_generation,
            self.test_schema_validation,
            self.test_cross_validation,
            self.test_metadata_completeness,
            self.test_content_matching,
            self.test_error_handling,
            self.test_integration_with_classifier
        ]
        
        all_passed = True
        for test in tests:
            try:
                test_name = test.__name__
                logger.info(f"Running {test_name}...")
                result = test()
                self.test_results.append((test_name, result, None))
                if not result:
                    all_passed = False
                    logger.error(f"❌ {test_name} FAILED")
                else:
                    logger.info(f"✅ {test_name} PASSED")
            except Exception as e:
                self.test_results.append((test.__name__, False, str(e)))
                logger.error(f"❌ {test.__name__} FAILED with exception: {e}")
                all_passed = False
        
        self._print_summary()
        return all_passed
    
    def test_kag_input_generation(self) -> bool:
        """Test basic KAG input generation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create sample parsed_output.json
            parsed_output = {
                "text": "This is a sample legal document about property sale.",
                "clauses": [{"type": "sale", "text": "property sale clause", "confidence": 0.9}],
                "named_entities": [{"text": "John Doe", "type": "PERSON", "confidence": 0.95}],
                "key_value_pairs": [{"key": "buyer", "value": "John Doe", "confidence": 0.9}],
                "needs_review": False,
                "extraction_method": "docai",
                "processor_id": "test-processor-123"
            }
            
            parsed_output_path = temp_path / "parsed_output.json"
            with open(parsed_output_path, 'w') as f:
                json.dump(parsed_output, f, indent=2)
            
            # Create sample classification_verdict.json
            classifier = create_classifier()
            result = classifier.classify_document(parsed_output["text"])
            verdict = classifier.export_classification_verdict(result)
            
            classification_verdict_path = temp_path / "classification_verdict.json"
            with open(classification_verdict_path, 'w') as f:
                json.dump(verdict, f, indent=2)
            
            # Generate KAG input
            kag_input_path = temp_path / "kag_input.json"
            doc_id = str(uuid.uuid4())
            
            try:
                kag_input = self.generator.generate_kag_input(
                    parsed_output_path=str(parsed_output_path),
                    classification_verdict_path=str(classification_verdict_path),
                    output_path=str(kag_input_path),
                    document_id=doc_id,
                    pipeline_id="test-pipeline-123",
                    gcs_uri="gs://test-bucket/test-file.pdf",
                    processor_id="test-processor-123"
                )
                
                # Verify file was created
                if not kag_input_path.exists():
                    logger.error("KAG input file was not created")
                    return False
                
                # Verify basic structure
                required_keys = ["document_id", "parsed_document", "classifier_verdict", "metadata"]
                for key in required_keys:
                    if key not in kag_input:
                        logger.error(f"Missing required key: {key}")
                        return False
                
                return True
                
            except Exception as e:
                logger.error(f"KAG input generation failed: {e}")
                return False
    
    def test_schema_validation(self) -> bool:
        """Test schema validation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a valid KAG input file
            valid_kag_input = {
                "document_id": "test-doc-123",
                "parsed_document": {
                    "full_text": "Sample document text",
                    "clauses": [],
                    "named_entities": [],
                    "key_value_pairs": [],
                    "needs_review": False,
                    "extraction_method": "docai",
                    "processor_id": "test-processor"
                },
                "classifier_verdict": {
                    "label": "Property_and_Real_Estate",
                    "score": 0.85,
                    "confidence": "high"
                },
                "metadata": {
                    "document_id": "test-doc-123",
                    "processor_id": "test-processor",
                    "audit": {
                        "created_by": "test",
                        "creation_timestamp": "2025-09-20T00:00:00Z"
                    },
                    "source": {
                        "gcs_uri": "gs://test-bucket/test-file.pdf"
                    }
                }
            }
            
            valid_file_path = temp_path / "valid_kag_input.json"
            with open(valid_file_path, 'w') as f:
                json.dump(valid_kag_input, f, indent=2)
            
            # Test valid file
            is_valid, errors, warnings = self.validator.validate_kag_input(str(valid_file_path))
            if not is_valid:
                logger.error(f"Valid file failed validation: {errors}")
                return False
            
            # Test invalid file (missing required field)
            invalid_kag_input = valid_kag_input.copy()
            del invalid_kag_input["document_id"]
            
            invalid_file_path = temp_path / "invalid_kag_input.json"
            with open(invalid_file_path, 'w') as f:
                json.dump(invalid_kag_input, f, indent=2)
            
            is_valid, errors, warnings = self.validator.validate_kag_input(str(invalid_file_path))
            if is_valid:
                logger.error("Invalid file passed validation when it should have failed")
                return False
            
            return True
    
    def test_cross_validation(self) -> bool:
        """Test cross-validation with source files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create source files
            source_text = "This is a legal contract for property sale."
            
            parsed_output = {
                "text": source_text,
                "clauses": [],
                "named_entities": [],
                "key_value_pairs": [],
                "processor_id": "test-processor"
            }
            
            parsed_output_path = temp_path / "parsed_output.json"
            with open(parsed_output_path, 'w') as f:
                json.dump(parsed_output, f, indent=2)
            
            classifier = create_classifier()
            result = classifier.classify_document(source_text)
            verdict = classifier.export_classification_verdict(result)
            
            classification_verdict_path = temp_path / "classification_verdict.json"
            with open(classification_verdict_path, 'w') as f:
                json.dump(verdict, f, indent=2)
            
            # Generate KAG input
            kag_input_path = temp_path / "kag_input.json"
            
            self.generator.generate_kag_input(
                parsed_output_path=str(parsed_output_path),
                classification_verdict_path=str(classification_verdict_path),
                output_path=str(kag_input_path),
                document_id="test-doc-123",
                pipeline_id="test-pipeline",
                gcs_uri="gs://test-bucket/test.pdf"
            )
            
            # Validate with cross-validation
            is_valid, errors, warnings = self.validator.validate_kag_input(
                kag_input_path=str(kag_input_path),
                parsed_output_path=str(parsed_output_path),
                classification_verdict_path=str(classification_verdict_path)
            )
            
            if not is_valid:
                logger.error(f"Cross-validation failed: {errors}")
                return False
            
            # Test with mismatched content
            mismatched_kag_input = json.load(open(kag_input_path))
            mismatched_kag_input["parsed_document"]["full_text"] = "Different text"
            
            mismatched_path = temp_path / "mismatched_kag_input.json"
            with open(mismatched_path, 'w') as f:
                json.dump(mismatched_kag_input, f, indent=2)
            
            is_valid, errors, warnings = self.validator.validate_kag_input(
                kag_input_path=str(mismatched_path),
                parsed_output_path=str(parsed_output_path)
            )
            
            if is_valid:
                logger.error("Mismatched content passed validation")
                return False
            
            return True
    
    def test_metadata_completeness(self) -> bool:
        """Test that all required metadata fields are present and non-empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create minimal source files
            parsed_output = {"text": "test", "processor_id": "test-proc"}
            parsed_output_path = temp_path / "parsed_output.json"
            with open(parsed_output_path, 'w') as f:
                json.dump(parsed_output, f)
            
            classifier = create_classifier()
            result = classifier.classify_document("test document")
            verdict = classifier.export_classification_verdict(result)
            
            classification_verdict_path = temp_path / "classification_verdict.json"
            with open(classification_verdict_path, 'w') as f:
                json.dump(verdict, f)
            
            # Generate KAG input
            kag_input_path = temp_path / "kag_input.json"
            
            self.generator.generate_kag_input(
                parsed_output_path=str(parsed_output_path),
                classification_verdict_path=str(classification_verdict_path),
                output_path=str(kag_input_path),
                document_id="test-doc",
                pipeline_id="test-pipeline",
                gcs_uri="gs://test-bucket/test.pdf",
                processor_id="test-processor"
            )
            
            # Load and verify metadata
            with open(kag_input_path, 'r') as f:
                kag_input = json.load(f)
            
            metadata = kag_input.get("metadata", {})
            
            # Check required metadata fields
            required_fields = ["document_id", "processor_id", "audit", "source"]
            for field in required_fields:
                if field not in metadata or not metadata[field]:
                    logger.error(f"Missing or empty required metadata field: {field}")
                    return False
            
            # Check nested required fields
            if "gcs_uri" not in metadata.get("source", {}):
                logger.error("Missing source.gcs_uri in metadata")
                return False
            
            if "created_by" not in metadata.get("audit", {}):
                logger.error("Missing audit.created_by in metadata")
                return False
            
            return True
    
    def test_content_matching(self) -> bool:
        """Test that content matches between source files and generated KAG input."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create source content
            source_text = "This is a partnership agreement between business partners."
            
            parsed_output = {
                "text": source_text,
                "clauses": [{"type": "partnership", "text": "partnership clause"}],
                "named_entities": [{"text": "Partner A", "type": "PERSON"}],
                "key_value_pairs": [{"key": "type", "value": "partnership"}],
                "processor_id": "test-processor"
            }
            
            parsed_output_path = temp_path / "parsed_output.json"
            with open(parsed_output_path, 'w') as f:
                json.dump(parsed_output, f, indent=2)
            
            classifier = create_classifier()
            result = classifier.classify_document(source_text)
            verdict = classifier.export_classification_verdict(result)
            
            classification_verdict_path = temp_path / "classification_verdict.json"
            with open(classification_verdict_path, 'w') as f:
                json.dump(verdict, f, indent=2)
            
            # Generate KAG input
            kag_input_path = temp_path / "kag_input.json"
            
            self.generator.generate_kag_input(
                parsed_output_path=str(parsed_output_path),
                classification_verdict_path=str(classification_verdict_path),
                output_path=str(kag_input_path),
                document_id="test-doc",
                pipeline_id="test-pipeline"
            )
            
            # Load and verify content matching
            with open(kag_input_path, 'r') as f:
                kag_input = json.load(f)
            
            # Verify parsed_document.full_text matches source
            kag_text = kag_input.get("parsed_document", {}).get("full_text", "")
            if kag_text != source_text:
                logger.error(f"Text mismatch: '{kag_text}' != '{source_text}'")
                return False
            
            # Verify classifier_verdict matches source
            kag_verdict = kag_input.get("classifier_verdict", {})
            source_label = verdict.get("label")
            kag_label = kag_verdict.get("label")
            
            if kag_label != source_label:
                logger.error(f"Label mismatch: '{kag_label}' != '{source_label}'")
                return False
            
            return True
    
    def test_error_handling(self) -> bool:
        """Test error handling for missing or malformed files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test missing parsed_output.json
            try:
                self.generator.generate_kag_input(
                    parsed_output_path=str(temp_path / "nonexistent.json"),
                    classification_verdict_path=str(temp_path / "nonexistent2.json"),
                    output_path=str(temp_path / "output.json"),
                    document_id="test",
                    pipeline_id="test"
                )
                logger.error("Should have failed with missing files")
                return False
            except FileNotFoundError:
                pass  # Expected
            
            # Test invalid JSON
            invalid_json_path = temp_path / "invalid.json"
            with open(invalid_json_path, 'w') as f:
                f.write("invalid json content")
            
            try:
                with open(invalid_json_path, 'r') as f:
                    json.load(f)
                logger.error("Should have failed with invalid JSON")
                return False
            except json.JSONDecodeError:
                pass  # Expected
            
            # Test validator with missing file
            is_valid, errors, warnings = self.validator.validate_kag_input(
                str(temp_path / "nonexistent_kag.json")
            )
            
            if is_valid:
                logger.error("Validation should have failed with missing file")
                return False
            
            return True
    
    def test_integration_with_classifier(self) -> bool:
        """Test integration with the regex classifier."""
        sample_texts = [
            "This is a sale deed for property transfer between vendor and vendee.",
            "Partnership agreement between business partners for joint venture.",
            "Employment contract between employer and employee with terms."
        ]
        
        classifier = create_classifier()
        
        for i, text in enumerate(sample_texts):
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Get classification
                result = classifier.classify_document(text)
                verdict = classifier.export_classification_verdict(result)
                
                # Create source files
                parsed_output = {"text": text, "processor_id": f"test-proc-{i}"}
                parsed_output_path = temp_path / "parsed_output.json"
                with open(parsed_output_path, 'w') as f:
                    json.dump(parsed_output, f)
                
                classification_verdict_path = temp_path / "classification_verdict.json"
                with open(classification_verdict_path, 'w') as f:
                    json.dump(verdict, f)
                
                # Generate and validate KAG input
                kag_input_path = temp_path / "kag_input.json"
                
                try:
                    self.generator.generate_kag_input(
                        parsed_output_path=str(parsed_output_path),
                        classification_verdict_path=str(classification_verdict_path),
                        output_path=str(kag_input_path),
                        document_id=f"test-doc-{i}",
                        pipeline_id=f"test-pipeline-{i}"
                    )
                    
                    is_valid, errors, warnings = self.validator.validate_kag_input(
                        str(kag_input_path),
                        str(parsed_output_path),
                        str(classification_verdict_path)
                    )
                    
                    if not is_valid:
                        logger.error(f"Integration test {i} failed validation: {errors}")
                        return False
                    
                except Exception as e:
                    logger.error(f"Integration test {i} failed: {e}")
                    return False
        
        return True
    
    def _print_summary(self):
        """Print test summary."""
        logger.info("\n" + "="*60)
        logger.info("ENHANCED KAG INPUT TEST SUITE SUMMARY")
        logger.info("="*60)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result, error in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status}: {test_name}")
            if error:
                logger.error(f"  Error: {error}")
        
        logger.info(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.error(f"💥 {total - passed} tests failed")


def main():
    """Main function to run the test suite."""
    test_suite = EnhancedKAGInputTests()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n✅ Enhanced KAG Input functionality is working correctly!")
        print("The pipeline now generates schema-compliant kag_input.json files that:")
        print("  - Pair DocAI output with classifier verdicts")
        print("  - Include all required metadata fields")
        print("  - Pass cross-validation with source files")
        print("  - Handle errors gracefully")
    else:
        print("\n❌ Some tests failed. Please check the logs above.")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)