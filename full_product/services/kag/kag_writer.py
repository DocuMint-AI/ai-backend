"""
KAG Writer for Document Processing Pipeline

This module provides functionality to generate kag_input.json files by merging
DocAI parsed output with classifier verdicts into the required schema format.

Features:
- Reads parsed_output.json (DocAI output) and classification_verdict.json
- Merges them into a unified kag_input.json schema
- Supports atomic writes with .tmp → final file pattern
- Validates required keys before returning
- Provides comprehensive logging and error handling
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


def generate_kag_input(
    artifact_dir: Union[str, Path],
    doc_id: str,
    processor_id: Optional[str] = None,
    gcs_uri: Optional[str] = None,
    pipeline_version: str = "v1",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate kag_input.json by merging DocAI output and classifier verdict.
    
    This function reads parsed_output.json and classification_verdict.json from
    the artifact directory and merges them into a unified kag_input.json file
    following the required schema format.
    
    Args:
        artifact_dir: Directory containing parsed_output.json and classification_verdict.json
        doc_id: Document ID (typically pipeline_id)
        processor_id: Optional DocAI processor ID
        gcs_uri: Optional GCS URI for the source document
        pipeline_version: Pipeline version string (default "v1")
        metadata: Optional additional metadata to include
        
    Returns:
        Path to the generated kag_input.json file
        
    Raises:
        FileNotFoundError: If required input files are missing
        ValueError: If input files are invalid or missing required fields
        IOError: If file operations fail
        
    Example:
        >>> kag_path = generate_kag_input(
        ...     artifact_dir="/path/to/artifacts",
        ...     doc_id="pipeline-123",
        ...     processor_id="docai-proc-456",
        ...     gcs_uri="gs://bucket/file.pdf"
        ... )
        >>> print(f"KAG input generated: {kag_path}")
    """
    try:
        artifact_path = Path(artifact_dir)
        
        # Validate artifact directory exists
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact directory not found: {artifact_path}")
        
        # Define input file paths
        parsed_output_path = artifact_path / "parsed_output.json"
        classification_verdict_path = artifact_path / "classification_verdict.json"
        kag_input_path = artifact_path / "kag_input.json"
        
        logger.info(f"Generating KAG input for document {doc_id} in {artifact_path}")
        
        # Load parsed_output.json (DocAI output)
        parsed_document = _load_parsed_output(parsed_output_path)
        
        # Load classification_verdict.json (classifier output)
        classifier_verdict = _load_classification_verdict(classification_verdict_path)
        
        # Create the unified KAG input schema
        kag_input = _create_kag_input_schema(
            doc_id=doc_id,
            parsed_document=parsed_document,
            classifier_verdict=classifier_verdict,
            processor_id=processor_id,
            gcs_uri=gcs_uri,
            pipeline_version=pipeline_version,
            metadata=metadata
        )
        
        # Validate the created schema
        _validate_kag_input_schema(kag_input)
        
        # Write kag_input.json with atomic operation
        _write_kag_input_atomic(kag_input, kag_input_path)
        
        logger.info(f"KAG Input generated -> {kag_input_path}")
        
        return str(kag_input_path)
        
    except Exception as e:
        logger.error(f"Failed to generate KAG input for document {doc_id}: {str(e)}")
        raise


def _load_parsed_output(file_path: Path) -> Dict[str, Any]:
    """
    Load and validate parsed_output.json from DocAI processing.
    
    Args:
        file_path: Path to parsed_output.json
        
    Returns:
        Parsed document data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or missing required fields
    """
    if not file_path.exists():
        raise FileNotFoundError(f"parsed_output.json not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate required fields for parsed document (flexible field names)
        text_content = data.get("text") or data.get("full_text") or ""
        if not text_content:
            raise ValueError(f"parsed_output.json missing text content ('text' or 'full_text' field): {file_path}")
        
        # Create structured parsed_document with defaults
        parsed_document = {
            "full_text": text_content,
            "clauses": data.get("clauses", []),
            "named_entities": data.get("named_entities", []),
            "key_value_pairs": data.get("key_value_pairs", [])
        }
        
        logger.debug(f"Loaded parsed output with {len(parsed_document['full_text'])} characters")
        
        return parsed_document
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in parsed_output.json: {file_path} - {str(e)}")
    except Exception as e:
        raise ValueError(f"Error loading parsed_output.json: {file_path} - {str(e)}")


def _load_classification_verdict(file_path: Path) -> Dict[str, Any]:
    """
    Load and validate classification_verdict.json from classifier.
    
    Args:
        file_path: Path to classification_verdict.json
        
    Returns:
        Classifier verdict data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or missing required fields
    """
    if not file_path.exists():
        raise FileNotFoundError(f"classification_verdict.json not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate required fields for classifier verdict
        required_fields = ["label", "score", "confidence"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"classification_verdict.json missing required field '{field}': {file_path}")
        
        # Create structured classifier verdict
        classifier_verdict = {
            "label": data.get("label", ""),
            "score": data.get("score", 0.0),
            "confidence": data.get("confidence", "unknown")
        }
        
        logger.debug(f"Loaded classifier verdict: {classifier_verdict['label']} ({classifier_verdict['confidence']})")
        
        return classifier_verdict
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in classification_verdict.json: {file_path} - {str(e)}")
    except Exception as e:
        raise ValueError(f"Error loading classification_verdict.json: {file_path} - {str(e)}")


def _create_kag_input_schema(
    doc_id: str,
    parsed_document: Dict[str, Any],
    classifier_verdict: Dict[str, Any],
    processor_id: Optional[str] = None,
    gcs_uri: Optional[str] = None,
    pipeline_version: str = "v1",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create the unified KAG input schema from components.
    
    Args:
        doc_id: Document identifier
        parsed_document: Parsed document data from DocAI
        classifier_verdict: Classifier verdict data
        processor_id: Optional DocAI processor ID
        gcs_uri: Optional GCS URI
        pipeline_version: Pipeline version
        metadata: Optional additional metadata
        
    Returns:
        Complete KAG input schema dictionary
    """
    # Create timestamp
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Build metadata section
    metadata_section = {
        "processor_id": processor_id or "unknown",
        "source": {
            "gcs_uri": gcs_uri or f"file://local/{doc_id}.pdf"
        },
        "pipeline_version": pipeline_version,
        "timestamp": timestamp
    }
    
    # Add any additional metadata provided (but preserve required structure)
    if metadata:
        for key, value in metadata.items():
            if key not in ["processor_id", "source", "pipeline_version", "timestamp"]:
                metadata_section[key] = value
    
    # Create the complete KAG input schema
    kag_input = {
        "document_id": doc_id,
        "parsed_document": parsed_document,
        "classifier_verdict": classifier_verdict,
        "metadata": metadata_section
    }
    
    logger.debug(f"Created KAG input schema for document {doc_id}")
    
    return kag_input


def _validate_kag_input_schema(kag_input: Dict[str, Any]) -> None:
    """
    Validate the KAG input schema contains all required keys.
    
    Args:
        kag_input: KAG input dictionary to validate
        
    Raises:
        ValueError: If required keys are missing or invalid
    """
    # Top-level required keys
    required_top_level = ["document_id", "parsed_document", "classifier_verdict", "metadata"]
    
    for key in required_top_level:
        if key not in kag_input:
            raise ValueError(f"KAG input missing required top-level key: {key}")
        if not kag_input[key]:
            raise ValueError(f"KAG input key '{key}' is empty or null")
    
    # Validate parsed_document structure
    parsed_doc = kag_input["parsed_document"]
    if not isinstance(parsed_doc, dict):
        raise ValueError("parsed_document must be a dictionary")
    
    required_parsed_fields = ["full_text", "clauses", "named_entities", "key_value_pairs"]
    for field in required_parsed_fields:
        if field not in parsed_doc:
            raise ValueError(f"parsed_document missing required field: {field}")
    
    # Validate classifier_verdict structure
    verdict = kag_input["classifier_verdict"]
    if not isinstance(verdict, dict):
        raise ValueError("classifier_verdict must be a dictionary")
    
    required_verdict_fields = ["label", "score", "confidence"]
    for field in required_verdict_fields:
        if field not in verdict:
            raise ValueError(f"classifier_verdict missing required field: {field}")
    
    # Validate metadata structure
    metadata = kag_input["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dictionary")
    
    required_metadata_fields = ["processor_id", "source", "pipeline_version", "timestamp"]
    for field in required_metadata_fields:
        if field not in metadata:
            raise ValueError(f"metadata missing required field: {field}")
    
    # Validate nested source structure
    source = metadata.get("source", {})
    if not isinstance(source, dict) or "gcs_uri" not in source:
        raise ValueError("metadata.source must contain gcs_uri field")
    
    logger.debug("KAG input schema validation passed")


def _write_kag_input_atomic(kag_input: Dict[str, Any], output_path: Path) -> None:
    """
    Write KAG input to file using atomic operation (.tmp → final).
    
    Args:
        kag_input: KAG input dictionary to write
        output_path: Final output file path
        
    Raises:
        IOError: If file operations fail
    """
    temp_path = output_path.with_suffix('.tmp')
    
    try:
        # Write to temporary file first
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(kag_input, f, indent=2, ensure_ascii=False, default=str)
        
        # Atomic rename to final file
        if output_path.exists():
            output_path.unlink()  # Remove existing file
        
        temp_path.rename(output_path)
        
        logger.debug(f"Atomically wrote KAG input to {output_path}")
        
    except Exception as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        
        raise IOError(f"Failed to write KAG input to {output_path}: {str(e)}")


# Utility functions for testing and validation
def validate_kag_input_file(file_path: Union[str, Path]) -> bool:
    """
    Validate an existing kag_input.json file.
    
    Args:
        file_path: Path to kag_input.json file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            kag_input = json.load(f)
        
        _validate_kag_input_schema(kag_input)
        return True
        
    except Exception as e:
        logger.error(f"KAG input validation failed for {file_path}: {str(e)}")
        return False


def get_kag_input_summary(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get a summary of a kag_input.json file.
    
    Args:
        file_path: Path to kag_input.json file
        
    Returns:
        Summary dictionary with key metrics
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            kag_input = json.load(f)
        
        parsed_doc = kag_input.get("parsed_document", {})
        verdict = kag_input.get("classifier_verdict", {})
        metadata = kag_input.get("metadata", {})
        
        return {
            "document_id": kag_input.get("document_id"),
            "text_length": len(parsed_doc.get("full_text", "")),
            "clause_count": len(parsed_doc.get("clauses", [])),
            "entity_count": len(parsed_doc.get("named_entities", [])),
            "kv_pair_count": len(parsed_doc.get("key_value_pairs", [])),
            "classification_label": verdict.get("label"),
            "classification_score": verdict.get("score"),
            "classification_confidence": verdict.get("confidence"),
            "processor_id": metadata.get("processor_id"),
            "pipeline_version": metadata.get("pipeline_version"),
            "timestamp": metadata.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Failed to get KAG input summary for {file_path}: {str(e)}")
        return {"error": str(e)}


# Example usage and testing
if __name__ == "__main__":
    import tempfile
    
    # Example usage with temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create sample parsed_output.json
        sample_parsed = {
            "text": "This is a sample legal document about property sale.",
            "clauses": [{"type": "sale", "text": "property sale clause"}],
            "named_entities": [{"text": "John Doe", "type": "PERSON"}],
            "key_value_pairs": [{"key": "buyer", "value": "John Doe"}]
        }
        
        with open(temp_path / "parsed_output.json", 'w') as f:
            json.dump(sample_parsed, f, indent=2)
        
        # Create sample classification_verdict.json
        sample_verdict = {
            "label": "Property_and_Real_Estate",
            "score": 0.85,
            "confidence": "high"
        }
        
        with open(temp_path / "classification_verdict.json", 'w') as f:
            json.dump(sample_verdict, f, indent=2)
        
        # Generate KAG input
        kag_path = generate_kag_input(
            artifact_dir=temp_path,
            doc_id="test-doc-123",
            processor_id="test-processor",
            gcs_uri="gs://test-bucket/test.pdf"
        )
        
        print(f"Generated KAG input: {kag_path}")
        
        # Validate and summarize
        is_valid = validate_kag_input_file(kag_path)
        summary = get_kag_input_summary(kag_path)
        
        print(f"Valid: {is_valid}")
        print(f"Summary: {summary}")