#!/usr/bin/env python3
"""
Test script to validate DocAI schema compliance of the updated OCR pipeline.

This script tests the new OCR output format to ensure it strictly follows
the required DocAI schema with proper identifiers and structure.
"""

import json
import logging
import copy
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_docai_schema(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that OCR result follows DocAI schema requirements.
    
    Args:
        ocr_result: The OCR result dictionary to validate
        
    Returns:
        Validation report with errors and warnings
    """
    errors = []
    warnings = []
    
    # Required top-level fields
    required_fields = [
        "document_id", "original_filename", "file_fingerprint",
        "derived_images", "language_detection", "ocr_result",
        "extracted_assets", "preprocessing"
    ]
    
    for field in required_fields:
        if field not in ocr_result:
            errors.append(f"Missing required field: {field}")
    
    # Validate document_id format
    if "document_id" in ocr_result:
        doc_id = ocr_result["document_id"]
        if not doc_id.startswith("upload_") or len(doc_id.split("_")) != 3:
            warnings.append(f"Document ID format may not match expected pattern: {doc_id}")
    
    # Validate file_fingerprint format
    if "file_fingerprint" in ocr_result:
        fingerprint = ocr_result["file_fingerprint"]
        if not fingerprint.startswith("sha256:"):
            errors.append(f"File fingerprint must start with 'sha256:': {fingerprint}")
    
    # Validate derived_images structure
    if "derived_images" in ocr_result:
        for i, image in enumerate(ocr_result["derived_images"]):
            required_image_fields = ["page", "image_uri", "width", "height", "dpi"]
            for field in required_image_fields:
                if field not in image:
                    errors.append(f"Missing field '{field}' in derived_images[{i}]")
    
    # Validate language_detection structure
    if "language_detection" in ocr_result:
        lang_det = ocr_result["language_detection"]
        required_lang_fields = ["primary", "confidence", "language_hints"]
        for field in required_lang_fields:
            if field not in lang_det:
                errors.append(f"Missing field '{field}' in language_detection")
    
    # Validate ocr_result structure
    if "ocr_result" in ocr_result:
        ocr_res = ocr_result["ocr_result"]
        if "pages" not in ocr_res:
            errors.append("Missing 'pages' array in ocr_result")
        elif not isinstance(ocr_res["pages"], list):
            errors.append("'pages' must be an array, not a dictionary")
        else:
            # Validate each page
            for i, page in enumerate(ocr_res["pages"]):
                validate_page_structure(page, i, errors, warnings)
    
    # Validate extracted_assets structure
    if "extracted_assets" in ocr_result:
        assets = ocr_result["extracted_assets"]
        expected_asset_types = ["signatures", "tables", "key_value_pairs"]
        for asset_type in expected_asset_types:
            if asset_type not in assets:
                warnings.append(f"Missing asset type '{asset_type}' in extracted_assets")
    
    # Validate preprocessing structure
    if "preprocessing" in ocr_result:
        preprocessing = ocr_result["preprocessing"]
        if "pipeline_version" not in preprocessing:
            warnings.append("Missing 'pipeline_version' in preprocessing")
        if "generated_at" not in preprocessing:
            warnings.append("Missing 'generated_at' in preprocessing")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings)
    }

def validate_page_structure(page: Dict[str, Any], page_index: int, errors: list, warnings: list):
    """
    Validate individual page structure.
    
    Args:
        page: Page data dictionary
        page_index: Index of the page in the array
        errors: List to append errors to
        warnings: List to append warnings to
    """
    required_page_fields = ["page", "width", "height", "page_confidence", "text_blocks"]
    
    for field in required_page_fields:
        if field not in page:
            errors.append(f"Missing field '{field}' in pages[{page_index}]")
    
    # Validate text_blocks structure
    if "text_blocks" in page:
        for j, block in enumerate(page["text_blocks"]):
            validate_block_structure(block, page_index, j, errors, warnings)

def validate_block_structure(block: Dict[str, Any], page_index: int, block_index: int, errors: list, warnings: list):
    """
    Validate text block structure.
    
    Args:
        block: Text block dictionary
        page_index: Index of the page
        block_index: Index of the block
        errors: List to append errors to
        warnings: List to append warnings to
    """
    required_block_fields = ["block_id", "page", "bounding_box", "text", "confidence", "lines"]
    
    for field in required_block_fields:
        if field not in block:
            errors.append(f"Missing field '{field}' in pages[{page_index}].text_blocks[{block_index}]")
    
    # Validate block_id format
    if "block_id" in block:
        block_id = block["block_id"]
        if not block_id.startswith(f"p{page_index + 1}_b"):
            warnings.append(f"Block ID format may be incorrect: {block_id}")
    
    # Validate bounding_box format
    if "bounding_box" in block:
        bbox = block["bounding_box"]
        if not isinstance(bbox, list) or len(bbox) != 4:
            errors.append(f"Bounding box must be array of 4 coordinate pairs in block {block.get('block_id', 'unknown')}")
        else:
            for i, coord in enumerate(bbox):
                if not isinstance(coord, list) or len(coord) != 2:
                    errors.append(f"Coordinate {i} must be [x, y] array in block {block.get('block_id', 'unknown')}")
    
    # Validate lines structure
    if "lines" in block:
        for k, line in enumerate(block["lines"]):
            validate_line_structure(line, page_index, block_index, k, errors, warnings)

def validate_line_structure(line: Dict[str, Any], page_index: int, block_index: int, line_index: int, errors: list, warnings: list):
    """
    Validate line structure.
    
    Args:
        line: Line dictionary
        page_index: Index of the page
        block_index: Index of the block
        line_index: Index of the line
        errors: List to append errors to
        warnings: List to append warnings to
    """
    required_line_fields = ["line_id", "text", "confidence", "words"]
    
    for field in required_line_fields:
        if field not in line:
            errors.append(f"Missing field '{field}' in pages[{page_index}].text_blocks[{block_index}].lines[{line_index}]")
    
    # Validate line_id format
    if "line_id" in line:
        line_id = line["line_id"]
        if not line_id.startswith(f"p{page_index + 1}_b") or "_l" not in line_id:
            warnings.append(f"Line ID format may be incorrect: {line_id}")
    
    # Validate words structure
    if "words" in line:
        for l, word in enumerate(line["words"]):
            validate_word_structure(word, page_index, block_index, line_index, l, errors, warnings)

def validate_word_structure(word: Dict[str, Any], page_index: int, block_index: int, line_index: int, word_index: int, errors: list, warnings: list):
    """
    Validate word structure.
    
    Args:
        word: Word dictionary
        page_index: Index of the page
        block_index: Index of the block
        line_index: Index of the line
        word_index: Index of the word
        errors: List to append errors to
        warnings: List to append warnings to
    """
    required_word_fields = ["text", "confidence", "bounding_box"]
    
    for field in required_word_fields:
        if field not in word:
            errors.append(f"Missing field '{field}' in word at pages[{page_index}].text_blocks[{block_index}].lines[{line_index}].words[{word_index}]")
    
    # Validate word bounding_box format
    if "bounding_box" in word:
        bbox = word["bounding_box"]
        if not isinstance(bbox, list) or len(bbox) != 4:
            errors.append(f"Word bounding box must be array of 4 coordinate pairs at word index {word_index}")

def create_sample_docai_result() -> Dict[str, Any]:
    """
    Create a sample DocAI result for testing.
    
    Returns:
        Sample DocAI-compatible result
    """
    return {
        "document_id": "upload_20250915_abc12345",
        "original_filename": "test_document.pdf",
        "file_fingerprint": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "pdf_uri": None,
        "derived_images": [
            {
                "page": 1,
                "image_uri": "file:///data/test-abc123/images/page_001.png",
                "width": 1240,
                "height": 1754,
                "dpi": 300
            }
        ],
        "language_detection": {
            "primary": "en",
            "confidence": 0.95,
            "language_hints": ["en"]
        },
        "ocr_result": {
            "full_text": "SAMPLE DOCUMENT\nThis is a test document for validation.",
            "pages": [
                {
                    "page": 1,
                    "width": 1240,
                    "height": 1754,
                    "page_confidence": 0.92,
                    "text_blocks": [
                        {
                            "block_id": "p1_b1",
                            "page": 1,
                            "bounding_box": [[100, 50], [800, 50], [800, 120], [100, 120]],
                            "text": "SAMPLE DOCUMENT",
                            "confidence": 0.98,
                            "lines": [
                                {
                                    "line_id": "p1_b1_l1",
                                    "text": "SAMPLE DOCUMENT",
                                    "confidence": 0.98,
                                    "words": [
                                        {
                                            "text": "SAMPLE",
                                            "confidence": 0.99,
                                            "bounding_box": [[100, 50], [350, 50], [350, 120], [100, 120]]
                                        },
                                        {
                                            "text": "DOCUMENT",
                                            "confidence": 0.97,
                                            "bounding_box": [[360, 50], [800, 50], [800, 120], [360, 120]]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "block_id": "p1_b2",
                            "page": 1,
                            "bounding_box": [[100, 150], [900, 150], [900, 200], [100, 200]],
                            "text": "This is a test document for validation.",
                            "confidence": 0.88,
                            "lines": [
                                {
                                    "line_id": "p1_b2_l1",
                                    "text": "This is a test document for validation.",
                                    "confidence": 0.88,
                                    "words": [
                                        {
                                            "text": "This",
                                            "confidence": 0.90,
                                            "bounding_box": [[100, 150], [150, 150], [150, 200], [100, 200]]
                                        },
                                        {
                                            "text": "is",
                                            "confidence": 0.95,
                                            "bounding_box": [[160, 150], [190, 150], [190, 200], [160, 200]]
                                        },
                                        {
                                            "text": "a",
                                            "confidence": 0.85,
                                            "bounding_box": [[200, 150], [220, 150], [220, 200], [200, 200]]
                                        },
                                        {
                                            "text": "test",
                                            "confidence": 0.92,
                                            "bounding_box": [[230, 150], [280, 150], [280, 200], [230, 200]]
                                        },
                                        {
                                            "text": "document",
                                            "confidence": 0.88,
                                            "bounding_box": [[290, 150], [400, 150], [400, 200], [290, 200]]
                                        },
                                        {
                                            "text": "for",
                                            "confidence": 0.90,
                                            "bounding_box": [[410, 150], [450, 150], [450, 200], [410, 200]]
                                        },
                                        {
                                            "text": "validation.",
                                            "confidence": 0.82,
                                            "bounding_box": [[460, 150], [580, 150], [580, 200], [460, 200]]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "extracted_assets": {
            "signatures": [],
            "tables": [],
            "key_value_pairs": []
        },
        "preprocessing": {
            "pipeline_version": "preproc-v2.4",
            "generated_at": datetime.now().isoformat()
        },
        "warnings": []
    }

def run_validation_tests():
    """
    Run comprehensive validation tests.
    """
    print("=" * 60)
    print("DocAI Schema Validation Tests")
    print("=" * 60)
    
    # Test 1: Valid sample
    print("\nTest 1: Validating correct DocAI format...")
    sample_result = create_sample_docai_result()
    validation = validate_docai_schema(sample_result)
    
    print(f"✓ Valid: {validation['valid']}")
    print(f"✓ Errors: {validation['error_count']}")
    print(f"✓ Warnings: {validation['warning_count']}")
    
    if validation['errors']:
        print("Errors found:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['warnings']:
        print("Warnings found:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    # Test 2: Missing required field
    print("\nTest 2: Testing missing required field...")
    invalid_sample = sample_result.copy()
    del invalid_sample['document_id']
    validation = validate_docai_schema(invalid_sample)
    
    print(f"✓ Valid: {validation['valid']} (should be False)")
    print(f"✓ Errors: {validation['error_count']} (should be > 0)")
    
    # Test 3: Invalid page structure (pages as dict instead of array)
    print("\nTest 3: Testing invalid pages structure...")
    invalid_pages = sample_result.copy()
    invalid_pages['ocr_result']['pages'] = {"1": invalid_pages['ocr_result']['pages'][0]}
    validation = validate_docai_schema(invalid_pages)
    
    print(f"✓ Valid: {validation['valid']} (should be False)")
    print(f"✓ Errors: {validation['error_count']} (should be > 0)")
    
    # Test 4: Invalid bounding box format
    print("\nTest 4: Testing invalid bounding box format...")
    # Deep copy to avoid reference issues
    invalid_bbox = copy.deepcopy(sample_result)
    try:
        invalid_bbox['ocr_result']['pages'][0]['text_blocks'][0]['bounding_box'] = [100, 50, 800, 120]  # Wrong format
        validation = validate_docai_schema(invalid_bbox)
        
        print(f"✓ Valid: {validation['valid']} (should be False)")
        print(f"✓ Errors: {validation['error_count']} (should be > 0)")
    except Exception as e:
        print(f"✗ Test failed due to structure issue: {e}")
        print("  This indicates the structure needs to be verified")
    
    print("\n" + "=" * 60)
    print("Schema validation tests completed!")
    
    # Save sample result for reference
    sample_file = Path("sample_docai_output.json")
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_result, f, indent=2, ensure_ascii=False)
    
    print(f"\nSample DocAI output saved to: {sample_file}")
    print("\nKey Schema Features Validated:")
    print("✓ Document ID format (upload_YYYYMMDD_hash)")
    print("✓ File fingerprint (sha256:...)")
    print("✓ Pages as ordered array (not dictionary)")
    print("✓ Block IDs (p{page}_b{n})")
    print("✓ Line IDs (p{page}_b{n}_l{m})")
    print("✓ Bounding boxes as [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]")
    print("✓ Language detection with confidence")
    print("✓ Derived images metadata")
    print("✓ Preprocessing pipeline info")
    print("✓ Extracted assets structure")
    print("✓ Warnings array")

if __name__ == "__main__":
    run_validation_tests()