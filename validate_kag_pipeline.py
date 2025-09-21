"""
Pipeline KAG Input Validation Script

This script validates that the pipeline generates correct kag_input.json files
that meet all the required specifications. It can be run as part of the pipeline
or as a standalone validation tool.

Usage:
    python validate_kag_pipeline.py [kag_input_path] [parsed_output_path] [classification_verdict_path]
    
If no paths provided, it will search for recent files in the data/processed directory.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kag_input_enhanced import create_kag_input_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_recent_kag_files(data_dir: str = "data/processed") -> Optional[Tuple[str, str, str]]:
    """
    Find the most recent KAG input files in the processed data directory.
    
    Returns:
        Tuple of (kag_input_path, parsed_output_path, classification_verdict_path) or None
    """
    try:
        data_path = Path(data_dir)
        if not data_path.exists():
            logger.error(f"Data directory not found: {data_dir}")
            return None
        
        # Search for kag_input.json files
        kag_files = list(data_path.rglob("kag_input.json"))
        if not kag_files:
            logger.error("No kag_input.json files found in data directory")
            return None
        
        # Get the most recent one
        most_recent_kag = max(kag_files, key=lambda p: p.stat().st_mtime)
        
        # Look for corresponding source files in the same directory
        kag_dir = most_recent_kag.parent
        
        parsed_output_path = kag_dir / "parsed_output.json"
        classification_verdict_path = kag_dir / "classification_verdict.json"
        
        # Check if source files exist
        missing_files = []
        if not parsed_output_path.exists():
            missing_files.append("parsed_output.json")
        if not classification_verdict_path.exists():
            missing_files.append("classification_verdict.json")
        
        if missing_files:
            logger.warning(f"Source files not found in {kag_dir}: {missing_files}")
            # Return paths anyway for basic validation
            return str(most_recent_kag), None, None
        
        return str(most_recent_kag), str(parsed_output_path), str(classification_verdict_path)
        
    except Exception as e:
        logger.error(f"Error finding recent KAG files: {e}")
        return None


def validate_kag_input_requirements(kag_input_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that KAG input meets the specific requirements from the user request.
    
    Requirements:
    1. `parsed_document.full_text` from DocAI output
    2. `classifier_verdict.label` and metadata from regex classifier
    3. Metadata block including `document_id`, `processor_id`, `audit`, and `source.gcs_uri`
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    try:
        with open(kag_input_path, 'r', encoding='utf-8') as f:
            kag_data = json.load(f)
        
        # Requirement 1: parsed_document.full_text from DocAI output
        parsed_document = kag_data.get("parsed_document", {})
        if "full_text" not in parsed_document:
            errors.append("Missing parsed_document.full_text field")
        elif not isinstance(parsed_document["full_text"], str):
            errors.append("parsed_document.full_text must be a string")
        elif len(parsed_document["full_text"]) == 0:
            warnings.append("parsed_document.full_text is empty")
        
        # Requirement 2: classifier_verdict.label and metadata
        classifier_verdict = kag_data.get("classifier_verdict", {})
        if "label" not in classifier_verdict:
            errors.append("Missing classifier_verdict.label field")
        elif not classifier_verdict["label"]:
            warnings.append("classifier_verdict.label is empty")
        
        if "score" not in classifier_verdict:
            errors.append("Missing classifier_verdict.score field")
        
        if "confidence" not in classifier_verdict:
            errors.append("Missing classifier_verdict.confidence field")
        
        # Requirement 3: Metadata block with required fields
        metadata = kag_data.get("metadata", {})
        required_metadata_fields = ["document_id", "processor_id", "audit", "source"]
        
        for field in required_metadata_fields:
            if field not in metadata:
                errors.append(f"Missing required metadata.{field} field")
            elif not metadata[field]:
                errors.append(f"metadata.{field} is empty or null")
        
        # Check nested source.gcs_uri
        source = metadata.get("source", {})
        if "gcs_uri" not in source:
            errors.append("Missing metadata.source.gcs_uri field")
        elif not source["gcs_uri"]:
            errors.append("metadata.source.gcs_uri is empty")
        
        # Additional quality checks
        document_id = kag_data.get("document_id")
        metadata_document_id = metadata.get("document_id")
        if document_id != metadata_document_id:
            warnings.append(f"Document ID mismatch: top-level '{document_id}' vs metadata '{metadata_document_id}'")
        
        # Check if classifier_verdict has meaningful data
        verdict_score = classifier_verdict.get("score", 0)
        if isinstance(verdict_score, (int, float)) and verdict_score < 0.1:
            warnings.append(f"Low classification score: {verdict_score}")
        
        return len(errors) == 0, errors, warnings
        
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in KAG input file: {e}")
        return False, errors, warnings
    except Exception as e:
        errors.append(f"Error validating KAG input: {e}")
        return False, errors, warnings


def validate_content_matching(
    kag_input_path: str,
    parsed_output_path: Optional[str],
    classification_verdict_path: Optional[str]
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that KAG input content matches source files.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    try:
        with open(kag_input_path, 'r', encoding='utf-8') as f:
            kag_data = json.load(f)
        
        # Validate against parsed_output.json if provided
        if parsed_output_path and os.path.exists(parsed_output_path):
            with open(parsed_output_path, 'r', encoding='utf-8') as f:
                parsed_output = json.load(f)
            
            # Check text matching
            source_text = parsed_output.get("text", "")
            kag_text = kag_data.get("parsed_document", {}).get("full_text", "")
            
            if source_text != kag_text:
                errors.append("parsed_document.full_text does not match source DocAI output")
            
            # Check processor_id matching
            source_processor = parsed_output.get("processor_id")
            kag_processor = kag_data.get("metadata", {}).get("processor_id")
            
            if source_processor and kag_processor and source_processor != kag_processor:
                warnings.append(f"Processor ID mismatch: source '{source_processor}' vs KAG '{kag_processor}'")
        
        # Validate against classification_verdict.json if provided
        if classification_verdict_path and os.path.exists(classification_verdict_path):
            with open(classification_verdict_path, 'r', encoding='utf-8') as f:
                verdict_data = json.load(f)
            
            kag_verdict = kag_data.get("classifier_verdict", {})
            
            # Check key classifier fields
            for field in ["label", "score", "confidence"]:
                source_value = verdict_data.get(field)
                kag_value = kag_verdict.get(field)
                
                if source_value != kag_value:
                    errors.append(f"classifier_verdict.{field} mismatch: source '{source_value}' vs KAG '{kag_value}'")
        
        return len(errors) == 0, errors, warnings
        
    except Exception as e:
        errors.append(f"Error validating content matching: {e}")
        return False, errors, warnings


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate KAG input pipeline output")
    parser.add_argument("kag_input", nargs="?", help="Path to kag_input.json file")
    parser.add_argument("parsed_output", nargs="?", help="Path to parsed_output.json file")
    parser.add_argument("classification_verdict", nargs="?", help="Path to classification_verdict.json file")
    parser.add_argument("--auto-find", action="store_true", help="Automatically find recent files")
    parser.add_argument("--data-dir", default="data/processed", help="Data directory to search")
    
    args = parser.parse_args()
    
    # Determine file paths
    if args.auto_find or not args.kag_input:
        logger.info("Searching for recent KAG input files...")
        file_paths = find_recent_kag_files(args.data_dir)
        if not file_paths:
            logger.error("No KAG input files found")
            return False
        
        kag_input_path, parsed_output_path, classification_verdict_path = file_paths
        logger.info(f"Found KAG input file: {kag_input_path}")
    else:
        kag_input_path = args.kag_input
        parsed_output_path = args.parsed_output
        classification_verdict_path = args.classification_verdict
    
    # Validate file exists
    if not os.path.exists(kag_input_path):
        logger.error(f"KAG input file not found: {kag_input_path}")
        return False
    
    logger.info("="*60)
    logger.info("KAG INPUT PIPELINE VALIDATION")
    logger.info("="*60)
    logger.info(f"Validating: {kag_input_path}")
    
    # Create validator
    validator = create_kag_input_validator()
    
    # Run schema validation
    logger.info("Running schema validation...")
    is_schema_valid, schema_errors, schema_warnings = validator.validate_kag_input(kag_input_path)
    
    # Run requirement validation
    logger.info("Running requirement validation...")
    is_req_valid, req_errors, req_warnings = validate_kag_input_requirements(kag_input_path)
    
    # Run content matching validation
    logger.info("Running content matching validation...")
    is_content_valid, content_errors, content_warnings = validate_content_matching(
        kag_input_path, parsed_output_path, classification_verdict_path
    )
    
    # Aggregate results
    all_errors = schema_errors + req_errors + content_errors
    all_warnings = schema_warnings + req_warnings + content_warnings
    is_valid = is_schema_valid and is_req_valid and is_content_valid
    
    # Print results
    logger.info("="*60)
    logger.info("VALIDATION RESULTS")
    logger.info("="*60)
    
    if is_valid:
        logger.info("✅ VALIDATION PASSED")
        logger.info("The KAG input file meets all requirements:")
        logger.info("  ✅ Contains parsed_document.full_text from DocAI output")
        logger.info("  ✅ Contains classifier_verdict.label and metadata")
        logger.info("  ✅ Includes required metadata fields (document_id, processor_id, audit, source.gcs_uri)")
        logger.info("  ✅ Content matches source files")
    else:
        logger.error("❌ VALIDATION FAILED")
        
    if all_errors:
        logger.error(f"Errors ({len(all_errors)}):")
        for i, error in enumerate(all_errors, 1):
            logger.error(f"  {i}. {error}")
    
    if all_warnings:
        logger.warning(f"Warnings ({len(all_warnings)}):")
        for i, warning in enumerate(all_warnings, 1):
            logger.warning(f"  {i}. {warning}")
    
    if not all_errors and not all_warnings:
        logger.info("No issues found.")
    
    logger.info("="*60)
    
    return is_valid


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)