"""
Enhanced regex fallback extractor for legal documents and insurance policies.

This module provides comprehensive regex patterns for extracting mandatory
key-value pairs from various legal document types when DocAI extraction
is insufficient or missing.
"""

import re
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# Comprehensive KV extraction patterns for legal documents
KV_PATTERNS = {
    "policy_no": re.compile(
        r'(?:Policy|Policy No|Policy No\.?|Policy Number|Pol No|Policy Ref)[:\s]*([A-Za-z0-9\-/]+)', 
        re.IGNORECASE
    ),
    "case_no": re.compile(
        r'(?:Case|Case No|C\/No|CR No|Case Number|File No|File Number)[:\s]*([A-Za-z0-9\-/]+)', 
        re.IGNORECASE
    ),
    "date_of_commencement": re.compile(
        r'(?:Date of Commencement|Date of Commence|Commencement Date|Policy Date|Effective Date)[:\s\-]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', 
        re.IGNORECASE
    ),
    "judgment_date": re.compile(
        r'(?:Judgment Date|Date of Judgment|Dated|Date of Order|Order Date)[:\s\-]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', 
        re.IGNORECASE
    ),
    "sum_assured": re.compile(
        r'(?:Sum Assured|Sum\s*Assured|Sum\s*Insured|Amount|Total Amount|Insurance Amount)[:\s₹Rs.\-]*([\d,]+)', 
        re.IGNORECASE
    ),
    "dob": re.compile(
        r'(?:Date of Birth|DOB|D\.O\.B\.?|Born on)[:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', 
        re.IGNORECASE
    ),
    "nominee": re.compile(
        r'(?:Nominee|Petitioner|Respondent|Nominee Name|Appointee|Beneficiary)[:\s]*([A-Za-z0-9 ,.\-&]+?)(?:\n|$|\.)', 
        re.IGNORECASE
    ),
    # Additional legal document patterns
    "contract_party": re.compile(
        r'(?:Party|Contracting Party|First Party|Second Party)[:\s]*([A-Za-z0-9 ,.\-&]+?)(?:\n|$|\.)', 
        re.IGNORECASE
    ),
    "jurisdiction": re.compile(
        r'(?:Jurisdiction|Court|Governing Law|Legal Jurisdiction)[:\s]*([A-Za-z0-9 ,.\-&]+?)(?:\n|$|\.)', 
        re.IGNORECASE
    ),
    "contract_value": re.compile(
        r'(?:Contract Value|Total Value|Agreement Value|Contract Amount)[:\s₹Rs.\$]*([\d,]+)', 
        re.IGNORECASE
    )
}


# Enhanced patterns for better coverage
ENHANCED_PATTERNS = {
    "policy_no": [
        r'Policy\s*(?:No|Number)[.:\s]*([A-Za-z0-9\-/]+)',
        r'Pol[icy]*\s*No[.:\s]*([A-Za-z0-9\-/]+)',
        r'Reference\s*(?:No|Number)[.:\s]*([A-Za-z0-9\-/]+)',
        r'UIN[.:\s]*([A-Za-z0-9\-/]+)'  # Unique Identification Number
    ],
    "date_of_commencement": [
        r'Date\s*of\s*Commencement[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'Commencement\s*Date[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'Policy\s*Date[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'Effective\s*(?:from|Date)[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})'
    ],
    "sum_assured": [
        r'Sum\s*Assured\s*(?:for\s*Basic\s*Plan)?[.:\s₹Rs.\(\)]*([0-9,]+)',
        r'Basic\s*Sum\s*Assured[.:\s₹Rs.\(\)]*([0-9,]+)',
        r'Insurance\s*Amount[.:\s₹Rs.\(\)]*([0-9,]+)',
        r'Coverage\s*Amount[.:\s₹Rs.\(\)]*([0-9,]+)'
    ],
    "dob": [
        r'Date\s*of\s*Birth[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'DOB[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'D\.O\.B\.?[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'Born\s*(?:on|:)[.:\s]*([0-3]?\d[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})'
    ],
    "nominee": [
        r'Nominee\s*(?:under\s*section\s*39)?[.:\s]*([A-Za-z\s]+?)(?:\n|Mr\.|Mrs\.|Ms\.|\s{3,})',
        r'Beneficiary[.:\s]*([A-Za-z\s]+?)(?:\n|Mr\.|Mrs\.|Ms\.|\s{3,})',
        r'Appointee[.:\s]*([A-Za-z\s]+?)(?:\n|Mr\.|Mrs\.|Ms\.|\s{3,})',
        r'Next\s*of\s*Kin[.:\s]*([A-Za-z\s]+?)(?:\n|Mr\.|Mrs\.|Ms\.|\s{3,})'
    ]
}


def run_fallback_kvs(text: str) -> Dict[str, Any]:
    """
    Run comprehensive fallback KV extraction using enhanced regex patterns.
    
    Args:
        text: Full document text to extract from
        
    Returns:
        Dictionary with extracted KV pairs and metadata
    """
    logger.info("Running enhanced fallback KV extraction")
    
    found_kvs = {}
    extraction_stats = {
        "patterns_tried": 0,
        "successful_extractions": 0,
        "failed_extractions": 0
    }
    
    # Try enhanced patterns first
    for field_name, patterns in ENHANCED_PATTERNS.items():
        found_kvs[field_name] = []
        
        for pattern in patterns:
            extraction_stats["patterns_tried"] += 1
            
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match and len(match.strip()) > 1:
                        # Normalize the value
                        normalized_value = _normalize_extracted_value(field_name, match.strip())
                        
                        found_kvs[field_name].append({
                            "value": match.strip(),
                            "normalized_value": normalized_value,
                            "pattern": pattern,
                            "confidence": 0.8,
                            "source": "fallback_regex"
                        })
                        extraction_stats["successful_extractions"] += 1
                        
                        # Take first good match per field
                        break
                        
            except Exception as e:
                logger.warning(f"Pattern failed for {field_name}: {e}")
                extraction_stats["failed_extractions"] += 1
    
    # Fallback to simple patterns if enhanced failed
    for field_name, pattern in KV_PATTERNS.items():
        if field_name not in found_kvs or not found_kvs[field_name]:
            try:
                match = pattern.search(text)
                if match and match.group(1).strip():
                    value = match.group(1).strip()
                    normalized_value = _normalize_extracted_value(field_name, value)
                    
                    found_kvs[field_name] = [{
                        "value": value,
                        "normalized_value": normalized_value,
                        "pattern": pattern.pattern,
                        "confidence": 0.7,
                        "source": "fallback_regex_simple"
                    }]
                    extraction_stats["successful_extractions"] += 1
                    
            except Exception as e:
                logger.warning(f"Simple pattern failed for {field_name}: {e}")
                extraction_stats["failed_extractions"] += 1
    
    # Calculate success metrics
    mandatory_fields = ["policy_no", "date_of_commencement", "sum_assured", "dob", "nominee"]
    found_mandatory = sum(1 for field in mandatory_fields if found_kvs.get(field))
    
    result = {
        "extracted_kvs": found_kvs,
        "mandatory_found": found_mandatory,
        "total_mandatory": len(mandatory_fields),
        "extraction_stats": extraction_stats,
        "success_rate": extraction_stats["successful_extractions"] / max(1, extraction_stats["patterns_tried"])
    }
    
    logger.info(
        f"Fallback extraction completed: {found_mandatory}/{len(mandatory_fields)} mandatory fields found"
    )
    
    return result


def _normalize_extracted_value(field_name: str, value: str) -> str:
    """
    Normalize extracted values based on field type.
    
    Args:
        field_name: Type of field being normalized
        value: Raw extracted value
        
    Returns:
        Normalized value
    """
    value = value.strip()
    
    if field_name in ["date_of_commencement", "judgment_date", "dob"]:
        # Normalize dates to ISO format
        try:
            from datetime import datetime
            # Try common date formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"]:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return value  # Return original if parsing fails
        except Exception:
            return value
    
    elif field_name in ["sum_assured", "contract_value"]:
        # Normalize currency to integer
        try:
            # Remove commas, currency symbols, and spaces
            clean_value = re.sub(r'[,\s₹$Rs.]', '', value)
            return str(int(clean_value))
        except (ValueError, TypeError):
            return value
    
    elif field_name in ["policy_no", "case_no"]:
        # Normalize ID formats
        return value.upper().replace(" ", "").replace(".", "")
    
    elif field_name in ["nominee", "contract_party"]:
        # Normalize person/entity names
        return value.title().strip()
    
    return value


def validate_mandatory_kvs(extracted_kvs: Dict[str, List[dict]]) -> Dict[str, bool]:
    """
    Validate that mandatory KVs were successfully extracted.
    
    Args:
        extracted_kvs: Results from run_fallback_kvs
        
    Returns:
        Validation results for each mandatory field
    """
    mandatory_fields = ["policy_no", "date_of_commencement", "sum_assured", "dob", "nominee"]
    
    validation_results = {}
    for field in mandatory_fields:
        field_results = extracted_kvs.get(field, [])
        validation_results[f"has_{field}"] = len(field_results) > 0
        
        if field_results:
            # Additional validation for specific fields
            first_value = field_results[0]["normalized_value"]
            
            if field in ["date_of_commencement", "dob"] and first_value:
                # Validate date format
                validation_results[f"{field}_format_valid"] = bool(re.match(r'\d{4}-\d{2}-\d{2}', first_value))
            
            elif field == "sum_assured" and first_value:
                # Validate numeric format
                validation_results[f"{field}_numeric_valid"] = first_value.isdigit()
    
    return validation_results