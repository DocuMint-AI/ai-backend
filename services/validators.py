"""
Validation utilities for document processing pipeline.

This module provides validation functions for offset validation,
KV presence checking, and data quality assessment.
"""

import re
from typing import List, Dict, Any, Tuple, Optional


def validate_offsets(entities: List[Dict[str, Any]], full_text: str) -> Dict[str, Any]:
    """
    Validate that entity offsets correctly map to full text.
    
    Args:
        entities: List of entities with start_offset and end_offset
        full_text: Full document text
        
    Returns:
        Validation report with failures and statistics
    """
    validation_result = {
        "all_valid": True,
        "total_entities": len(entities),
        "valid_offsets": 0,
        "invalid_offsets": 0,
        "failures": []
    }
    
    for i, entity in enumerate(entities):
        entity_id = entity.get("id", f"entity_{i}")
        start_offset = entity.get("start_offset")
        end_offset = entity.get("end_offset")
        expected_text = entity.get("text", entity.get("mention_text", ""))
        
        if start_offset is not None and end_offset is not None:
            # Check bounds
            if start_offset >= 0 and end_offset <= len(full_text) and start_offset < end_offset:
                actual_text = full_text[start_offset:end_offset]
                
                # Normalize both texts for comparison
                expected_normalized = " ".join(expected_text.split())
                actual_normalized = " ".join(actual_text.split())
                
                if expected_normalized == actual_normalized:
                    validation_result["valid_offsets"] += 1
                else:
                    validation_result["invalid_offsets"] += 1
                    validation_result["all_valid"] = False
                    validation_result["failures"].append({
                        "entity_id": entity_id,
                        "start_offset": start_offset,
                        "end_offset": end_offset,
                        "expected_text": expected_text,
                        "actual_text": actual_text,
                        "issue": "text_mismatch"
                    })
            else:
                validation_result["invalid_offsets"] += 1
                validation_result["all_valid"] = False
                validation_result["failures"].append({
                    "entity_id": entity_id,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "issue": "invalid_range",
                    "full_text_length": len(full_text)
                })
        else:
            validation_result["failures"].append({
                "entity_id": entity_id,
                "issue": "missing_offsets"
            })
    
    return validation_result


def check_mandatory_kv_presence(kvs: List[Dict[str, Any]], mandatory_fields: List[str]) -> Dict[str, Any]:
    """
    Check presence of mandatory key-value pairs.
    
    Args:
        kvs: List of extracted key-value pairs
        mandatory_fields: List of mandatory field names
        
    Returns:
        Presence report with found/missing fields
    """
    presence_report = {
        "total_mandatory": len(mandatory_fields),
        "found_mandatory": 0,
        "missing_mandatory": [],
        "found_fields": {},
        "coverage_ratio": 0.0
    }
    
    # Normalize KV keys for matching
    normalized_kvs = []
    for kv in kvs:
        key = kv.get("key", "").lower()
        value = kv.get("value", "")
        normalized_kvs.append({"key": key, "value": value, "original": kv})
    
    # Check each mandatory field
    for field in mandatory_fields:
        field_lower = field.lower()
        found = False
        
        for kv in normalized_kvs:
            # Check for partial matches (handle variations in field names)
            if field_lower in kv["key"] or any(word in kv["key"] for word in field_lower.split("_")):
                presence_report["found_fields"][field] = {
                    "value": kv["value"],
                    "key_matched": kv["key"],
                    "original_kv": kv["original"]
                }
                found = True
                break
        
        if found:
            presence_report["found_mandatory"] += 1
        else:
            presence_report["missing_mandatory"].append(field)
    
    # Calculate coverage ratio
    if presence_report["total_mandatory"] > 0:
        presence_report["coverage_ratio"] = presence_report["found_mandatory"] / presence_report["total_mandatory"]
    
    return presence_report


def extract_policy_no(text: str) -> Optional[str]:
    """
    Extract policy number from text using regex patterns.
    
    Args:
        text: Text to search
        
    Returns:
        Policy number if found, None otherwise
    """
    patterns = [
        r'Policy\s*No[:\s.]*([A-Za-z0-9\-/]+)',
        r'Policy\s*Number[:\s.]*([A-Za-z0-9\-/]+)',
        r'Policy\s*ID[:\s.]*([A-Za-z0-9\-/]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Validate policy number format (basic check)
            if len(value) >= 3 and re.match(r'^[A-Za-z0-9\-/]+$', value):
                return value
    
    return None


def extract_dates(text: str) -> List[Tuple[str, str, int, int]]:
    """
    Extract dates from text with their positions.
    
    Args:
        text: Text to search
        
    Returns:
        List of tuples (date_text, date_type, start_offset, end_offset)
    """
    date_patterns = [
        (r'Date\s+of\s+Birth[:\s.]*([0-9\-/\.]+)', "date_of_birth"),
        (r'Date\s+of\s+Commencement[:\s.]*([0-9\-/\.]+)', "commencement_date"),
        (r'Date\s+of\s+Maturity[:\s.]*([0-9\-/\.]+)', "maturity_date"),
        (r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', "generic_date"),
        (r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', "generic_date")
    ]
    
    extracted_dates = []
    
    for pattern, date_type in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_text = match.group(1).strip()
            start_offset = match.start(1)
            end_offset = match.end(1)
            
            # Basic date validation
            if re.match(r'^\d+[/-]\d+[/-]\d+$', date_text):
                extracted_dates.append((date_text, date_type, start_offset, end_offset))
    
    return extracted_dates


def calculate_clause_coverage(clauses: List[Dict[str, Any]], full_text_length: int) -> float:
    """
    Calculate what percentage of the document is covered by extracted clauses.
    
    Args:
        clauses: List of extracted clauses with offsets
        full_text_length: Total length of document text
        
    Returns:
        Coverage ratio (0.0 to 1.0)
    """
    if full_text_length == 0:
        return 0.0
    
    covered_characters = set()
    
    for clause in clauses:
        start = clause.get("start_offset", 0)
        end = clause.get("end_offset", 0)
        
        if isinstance(start, int) and isinstance(end, int) and start < end:
            # Add all character positions in this clause to the set
            for pos in range(start, min(end, full_text_length)):
                covered_characters.add(pos)
    
    coverage_ratio = len(covered_characters) / full_text_length
    return min(coverage_ratio, 1.0)  # Cap at 1.0


def validate_document_structure(parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate overall document structure and extraction quality.
    
    Args:
        parsed_doc: Parsed document dictionary
        
    Returns:
        Structure validation report
    """
    validation = {
        "structure_valid": True,
        "issues": [],
        "recommendations": [],
        "quality_score": 0.0
    }
    
    # Check required fields
    required_fields = ["full_text", "clauses", "named_entities", "key_value_pairs"]
    for field in required_fields:
        if field not in parsed_doc:
            validation["structure_valid"] = False
            validation["issues"].append(f"Missing required field: {field}")
    
    # Check data quality
    full_text = parsed_doc.get("full_text", "")
    clauses = parsed_doc.get("clauses", [])
    entities = parsed_doc.get("named_entities", [])
    kvs = parsed_doc.get("key_value_pairs", [])
    
    # Calculate quality metrics
    metrics = {
        "text_length": len(full_text),
        "clause_count": len(clauses),
        "entity_count": len(entities),
        "kv_count": len(kvs)
    }
    
    # Quality scoring
    quality_points = 0
    max_points = 100
    
    # Text extraction (30 points)
    if metrics["text_length"] > 100:
        quality_points += 30
    elif metrics["text_length"] > 50:
        quality_points += 15
    
    # Entity extraction (25 points)
    if metrics["entity_count"] >= 5:
        quality_points += 25
    elif metrics["entity_count"] >= 2:
        quality_points += 15
    elif metrics["entity_count"] >= 1:
        quality_points += 5
    
    # Clause extraction (25 points)
    if metrics["clause_count"] >= 5:
        quality_points += 25
    elif metrics["clause_count"] >= 3:
        quality_points += 15
    elif metrics["clause_count"] >= 1:
        quality_points += 5
    
    # KV extraction (20 points)
    if metrics["kv_count"] >= 5:
        quality_points += 20
    elif metrics["kv_count"] >= 3:
        quality_points += 12
    elif metrics["kv_count"] >= 1:
        quality_points += 5
    
    validation["quality_score"] = quality_points / max_points
    
    # Generate recommendations
    if metrics["entity_count"] < 3:
        validation["recommendations"].append("Consider using specialized DocAI processor for better entity extraction")
    
    if metrics["clause_count"] < 3:
        validation["recommendations"].append("Improve clause detection patterns or use document structure analysis")
    
    if metrics["kv_count"] < 2:
        validation["recommendations"].append("Implement more comprehensive regex patterns for key-value extraction")
    
    validation["metrics"] = metrics
    
    return validation