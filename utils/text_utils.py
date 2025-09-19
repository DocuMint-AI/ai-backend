"""
Canonical text normalization utilities for consistent processing across Vision and DocAI.

This module provides standardized text normalization functions to ensure
consistent text processing between different OCR sources and document processing
services, improving text similarity matching and offset calculations.
"""

import re
from typing import Optional


def normalize_text(s: str) -> str:
    """
    Canonical text normalization for consistent processing.
    
    This function applies standardized normalization rules to ensure
    text from different sources (Vision API, DocAI) can be compared
    accurately and consistently.
    
    Args:
        s: Input text string to normalize
        
    Returns:
        Normalized text string
        
    Example:
        >>> normalize_text("Hello   world\r\n\tMore text  .")
        "Hello world More text."
    """
    if not s:
        return ""
    
    # Convert Windows line endings to Unix
    s = s.replace('\r\n', '\n')
    
    # Normalize whitespace - collapse multiple spaces/tabs/newlines to single space
    s = re.sub(r'\s+', ' ', s)
    
    # Remove spaces before punctuation
    s = re.sub(r'\s+([,.:;?!])', r'\1', s)
    
    # Normalize common spacing patterns
    s = re.sub(r'\(\s+', '(', s)  # "( text" -> "(text"
    s = re.sub(r'\s+\)', ')', s)  # "text )" -> "text)"
    
    return s.strip()


def normalize_for_comparison(s: str) -> str:
    """
    Enhanced normalization for text comparison between Vision and DocAI.
    
    Applies more aggressive normalization for similarity calculations
    while preserving semantic meaning.
    
    Args:
        s: Input text string
        
    Returns:
        Heavily normalized text for comparison
    """
    if not s:
        return ""
    
    # Start with basic normalization
    s = normalize_text(s)
    
    # Additional normalization for comparison
    s = s.lower()  # Case insensitive
    
    # Remove extra punctuation variations
    s = re.sub(r'[""''„"‚'']', '"', s)  # Normalize quotes
    s = re.sub(r'[–—−]', '-', s)  # Normalize dashes
    
    # Normalize common abbreviations
    s = re.sub(r'\bno\.\s*', 'number ', s, flags=re.IGNORECASE)
    s = re.sub(r'\buin\s*:\s*', 'uin: ', s, flags=re.IGNORECASE)
    
    return s.strip()


def calculate_text_similarity(text1: str, text2: str) -> dict:
    """
    Calculate similarity between two text strings using multiple metrics.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Dictionary with similarity metrics
    """
    from difflib import SequenceMatcher
    
    # Normalize both texts
    norm1 = normalize_for_comparison(text1)
    norm2 = normalize_for_comparison(text2)
    
    # Character-level similarity
    char_similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Word-level similarity
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    word_similarity = len(words1 & words2) / len(words1 | words2) if (words1 | words2) else 1.0
    
    # Combined similarity (weighted average)
    combined_similarity = (char_similarity * 0.7) + (word_similarity * 0.3)
    
    return {
        "character_similarity": char_similarity,
        "word_similarity": word_similarity,
        "combined_similarity": combined_similarity,
        "normalized_lengths": {
            "text1": len(norm1),
            "text2": len(norm2)
        }
    }


def extract_policy_number(text: str) -> Optional[str]:
    """
    Extract policy number from text using refined patterns.
    
    Args:
        text: Text to search for policy number
        
    Returns:
        Policy number if found, None otherwise
    """
    patterns = [
        r'Policy\s+No\.?\s*:?\s*([A-Z0-9\-/]+)',
        r'Policy\s+Number\s*:?\s*([A-Z0-9\-/]+)',
        r'Pol\.?\s*No\.?\s*:?\s*([A-Z0-9\-/]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None