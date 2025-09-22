"""
Enhanced KAG Input Generator and Validator

This module provides functionality to generate schema-compliant kag_input.json files
that pair DocAI output with classifier verdicts and include proper metadata fields.

Key Features:
- Reads parsed_output.json and classification_verdict.json
- Merges them into schema-compliant kag_input.json
- Includes runtime metadata (processor_id, pipeline_version, timestamp)
- Validates content matches source files
- Provides clear error messages for mismatched or missing data
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class KAGInputSchema:
    """Schema-compliant KAG input structure."""
    
    # Required top-level fields
    document_id: str
    parsed_document: Dict[str, Any]  # Full DocAI output
    classifier_verdict: Dict[str, Any]  # Full classifier output
    metadata: Dict[str, Any]  # Required metadata block


class KAGInputGenerator:
    """
    Generator for schema-compliant KAG input files that pair DocAI output
    with classifier verdicts and include proper metadata.
    """
    
    def __init__(self, pipeline_version: str = "1.1.0"):
        """Initialize the KAG input generator."""
        self.pipeline_version = pipeline_version
        logger.info("KAGInputGenerator initialized for schema-compliant output")
    
    def generate_kag_input(
        self,
        parsed_output_path: str,
        classification_verdict_path: str,
        output_path: str,
        document_id: str,
        pipeline_id: str,
        gcs_uri: Optional[str] = None,
        processor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate schema-compliant kag_input.json from source files.
        
        Args:
            parsed_output_path: Path to parsed_output.json (DocAI output)
            classification_verdict_path: Path to classification_verdict.json
            output_path: Path where kag_input.json will be saved
            document_id: Unique document identifier
            pipeline_id: Pipeline execution identifier
            gcs_uri: Optional GCS URI for the source document
            processor_id: Optional DocAI processor identifier
            
        Returns:
            Generated KAG input dictionary
            
        Raises:
            FileNotFoundError: If source files don't exist
            ValueError: If source files have invalid format
        """
        try:
            logger.info(f"Generating schema-compliant KAG input for document {document_id}")
            
            # Load DocAI parsed output
            parsed_output = self._load_parsed_output(parsed_output_path)
            
            # Load classifier verdict
            classifier_verdict = self._load_classifier_verdict(classification_verdict_path)
            
            # Extract processor_id from parsed output if not provided
            if not processor_id:
                processor_id = parsed_output.get("processor_id", "unknown")
            
            # Create parsed_document structure
            parsed_document = {
                "full_text": parsed_output.get("text", ""),
                "clauses": parsed_output.get("clauses", []),
                "named_entities": parsed_output.get("named_entities", []),
                "key_value_pairs": parsed_output.get("key_value_pairs", []),
                "needs_review": parsed_output.get("needs_review", False),
                "extraction_method": parsed_output.get("extraction_method", "docai"),
                "processor_id": processor_id
            }
            
            # Create metadata block with required fields
            metadata = {
                "document_id": document_id,
                "processor_id": processor_id,
                "pipeline_id": pipeline_id,
                "pipeline_version": self.pipeline_version,
                "timestamp": datetime.utcnow().isoformat(),
                "audit": {
                    "created_by": "kag_input_generator",
                    "creation_timestamp": datetime.utcnow().isoformat(),
                    "source_files": {
                        "parsed_output": os.path.basename(parsed_output_path),
                        "classification_verdict": os.path.basename(classification_verdict_path)
                    },
                    "validation_status": "pending"
                },
                "source": {
                    "gcs_uri": gcs_uri or f"file://{parsed_output_path}",
                    "processing_method": "mvp_regex_classification",
                    "original_format": "pdf"
                },
                "quality_metrics": {
                    "text_length": len(parsed_document["full_text"]),
                    "entity_count": len(parsed_document["named_entities"]),
                    "clause_count": len(parsed_document["clauses"]),
                    "kv_pair_count": len(parsed_document["key_value_pairs"]),
                    "classification_score": classifier_verdict.get("score", 0.0),
                    "classification_confidence": classifier_verdict.get("confidence", "unknown")
                }
            }
            
            # Create schema-compliant KAG input
            kag_input = {
                "document_id": document_id,
                "parsed_document": parsed_document,
                "classifier_verdict": classifier_verdict,
                "metadata": metadata
            }
            
            # Save to output path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(kag_input, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Schema-compliant KAG input saved to: {output_file}")
            
            return kag_input
            
        except Exception as e:
            logger.error(f"Failed to generate KAG input: {str(e)}")
            raise
    
    def _load_parsed_output(self, file_path: str) -> Dict[str, Any]:
        """Load and validate DocAI parsed output file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Parsed output file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            if "text" not in data:
                raise ValueError(f"Parsed output missing required 'text' field: {file_path}")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in parsed output file {file_path}: {str(e)}")
    
    def _load_classifier_verdict(self, file_path: str) -> Dict[str, Any]:
        """Load and validate classifier verdict file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Classification verdict file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ["label", "score", "confidence"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Classification verdict missing required '{field}' field: {file_path}")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in classification verdict file {file_path}: {str(e)}")


class KAGInputValidator:
    """
    Validator for schema-compliant KAG input files that ensures content
    matches source files and all required fields are present.
    """
    
    def __init__(self):
        """Initialize the KAG input validator."""
        logger.info("KAGInputValidator initialized")
    
    def validate_kag_input(
        self,
        kag_input_path: str,
        parsed_output_path: Optional[str] = None,
        classification_verdict_path: Optional[str] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate kag_input.json file for correctness and completeness.
        
        Args:
            kag_input_path: Path to kag_input.json file
            parsed_output_path: Optional path to source parsed_output.json for cross-validation
            classification_verdict_path: Optional path to source classification_verdict.json
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            logger.info(f"Validating KAG input file: {kag_input_path}")
            
            # Load KAG input file
            kag_input = self._load_kag_input(kag_input_path)
            
            # Validate schema compliance
            schema_errors = self._validate_schema(kag_input)
            errors.extend(schema_errors)
            
            # Validate content quality
            content_warnings = self._validate_content_quality(kag_input)
            warnings.extend(content_warnings)
            
            # Cross-validate with source files if provided
            if parsed_output_path:
                cross_val_errors, cross_val_warnings = self._cross_validate_parsed_output(
                    kag_input, parsed_output_path
                )
                errors.extend(cross_val_errors)
                warnings.extend(cross_val_warnings)
            
            if classification_verdict_path:
                cross_val_errors, cross_val_warnings = self._cross_validate_classifier_verdict(
                    kag_input, classification_verdict_path
                )
                errors.extend(cross_val_errors)
                warnings.extend(cross_val_warnings)
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info("KAG input validation passed")
            else:
                logger.error(f"KAG input validation failed with {len(errors)} errors")
            
            return is_valid, errors, warnings
            
        except Exception as e:
            error_msg = f"Validation failed with exception: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg], warnings
    
    def _load_kag_input(self, file_path: str) -> Dict[str, Any]:
        """Load and parse KAG input file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"KAG input file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in KAG input file {file_path}: {str(e)}")
    
    def _validate_schema(self, kag_input: Dict[str, Any]) -> List[str]:
        """Validate KAG input schema compliance."""
        errors = []
        
        # Check required top-level keys
        required_keys = ["document_id", "parsed_document", "classifier_verdict", "metadata"]
        for key in required_keys:
            if key not in kag_input:
                errors.append(f"Missing required top-level key: {key}")
            elif not kag_input[key]:
                errors.append(f"Required key '{key}' is empty or null")
        
        # Validate parsed_document structure
        if "parsed_document" in kag_input:
            parsed_doc = kag_input["parsed_document"]
            if not isinstance(parsed_doc, dict):
                errors.append("parsed_document must be a dictionary")
            else:
                if "full_text" not in parsed_doc:
                    errors.append("parsed_document missing required 'full_text' field")
                elif not isinstance(parsed_doc["full_text"], str):
                    errors.append("parsed_document.full_text must be a string")
        
        # Validate classifier_verdict structure
        if "classifier_verdict" in kag_input:
            verdict = kag_input["classifier_verdict"]
            if not isinstance(verdict, dict):
                errors.append("classifier_verdict must be a dictionary")
            else:
                required_verdict_fields = ["label", "score", "confidence"]
                for field in required_verdict_fields:
                    if field not in verdict:
                        errors.append(f"classifier_verdict missing required '{field}' field")
        
        # Validate metadata structure
        if "metadata" in kag_input:
            metadata = kag_input["metadata"]
            if not isinstance(metadata, dict):
                errors.append("metadata must be a dictionary")
            else:
                required_metadata_fields = ["document_id", "processor_id", "audit", "source"]
                for field in required_metadata_fields:
                    if field not in metadata:
                        errors.append(f"metadata missing required '{field}' field")
                    elif not metadata[field]:
                        errors.append(f"metadata.{field} is empty or null")
                
                # Validate nested metadata structures
                if "source" in metadata and isinstance(metadata["source"], dict):
                    if "gcs_uri" not in metadata["source"]:
                        errors.append("metadata.source missing required 'gcs_uri' field")
        
        return errors
    
    def _validate_content_quality(self, kag_input: Dict[str, Any]) -> List[str]:
        """Validate content quality and provide warnings."""
        warnings = []
        
        # Check document_id consistency
        doc_id = kag_input.get("document_id")
        metadata_doc_id = kag_input.get("metadata", {}).get("document_id")
        if doc_id != metadata_doc_id:
            warnings.append(f"Document ID mismatch: top-level '{doc_id}' vs metadata '{metadata_doc_id}'")
        
        # Check text content quality
        parsed_doc = kag_input.get("parsed_document", {})
        full_text = parsed_doc.get("full_text", "")
        if len(full_text) < 10:
            warnings.append("Document text is very short (< 10 characters)")
        
        # Check classification quality
        verdict = kag_input.get("classifier_verdict", {})
        confidence = verdict.get("confidence", "")
        if confidence in ["very_low", "low"]:
            warnings.append(f"Low classification confidence: {confidence}")
        
        score = verdict.get("score", 0)
        if isinstance(score, (int, float)) and score < 0.1:
            warnings.append(f"Low classification score: {score}")
        
        return warnings
    
    def _cross_validate_parsed_output(
        self, 
        kag_input: Dict[str, Any], 
        parsed_output_path: str
    ) -> Tuple[List[str], List[str]]:
        """Cross-validate parsed_document content with source file."""
        errors = []
        warnings = []
        
        try:
            with open(parsed_output_path, 'r', encoding='utf-8') as f:
                source_data = json.load(f)
            
            parsed_doc = kag_input.get("parsed_document", {})
            
            # Compare full_text
            source_text = source_data.get("text", "")
            kag_text = parsed_doc.get("full_text", "")
            
            if source_text != kag_text:
                errors.append("parsed_document.full_text does not match source DocAI output")
            
            # Compare key counts
            source_entities = len(source_data.get("named_entities", []))
            kag_entities = len(parsed_doc.get("named_entities", []))
            if source_entities != kag_entities:
                warnings.append(f"Entity count mismatch: source {source_entities} vs KAG {kag_entities}")
            
        except Exception as e:
            errors.append(f"Failed to cross-validate with parsed output: {str(e)}")
        
        return errors, warnings
    
    def _cross_validate_classifier_verdict(
        self, 
        kag_input: Dict[str, Any], 
        classification_verdict_path: str
    ) -> Tuple[List[str], List[str]]:
        """Cross-validate classifier_verdict content with source file."""
        errors = []
        warnings = []
        
        try:
            with open(classification_verdict_path, 'r', encoding='utf-8') as f:
                source_verdict = json.load(f)
            
            kag_verdict = kag_input.get("classifier_verdict", {})
            
            # Compare key fields
            key_fields = ["label", "score", "confidence"]
            for field in key_fields:
                source_value = source_verdict.get(field)
                kag_value = kag_verdict.get(field)
                
                if source_value != kag_value:
                    errors.append(f"classifier_verdict.{field} mismatch: source '{source_value}' vs KAG '{kag_value}'")
            
        except Exception as e:
            errors.append(f"Failed to cross-validate with classifier verdict: {str(e)}")
        
        return errors, warnings


def create_kag_input_generator() -> KAGInputGenerator:
    """Factory function to create a KAG input generator."""
    return KAGInputGenerator()


def create_kag_input_validator() -> KAGInputValidator:
    """Factory function to create a KAG input validator."""
    return KAGInputValidator()


# CLI functionality for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        # Quick validation test
        validator = create_kag_input_validator()
        
        # Find a sample kag_input.json file
        sample_files = []
        for root, dirs, files in os.walk("."):
            for file in files:
                if file == "kag_input.json":
                    sample_files.append(os.path.join(root, file))
        
        if sample_files:
            is_valid, errors, warnings = validator.validate_kag_input(sample_files[0])
            print(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
            if errors:
                print("Errors:")
                for error in errors:
                    print(f"  - {error}")
            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print(f"  - {warning}")
        else:
            print("No kag_input.json files found for validation")
    
    else:
        print("Enhanced KAG Input Generator and Validator")
        print("Usage:")
        print("  python kag_input_enhanced.py validate  # Validate existing files")
        print("  from kag_input_enhanced import create_kag_input_generator")