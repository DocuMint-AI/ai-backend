"""
Text normalization utilities for consistent processing across Vision and DocAI.

This module provides standardized text normalization functions to ensure
consistent text processing and comparison between different OCR/parsing services.
"""

import re
from typing import List, Tuple, Dict


def normalize_text(text: str) -> str:
    """
    Normalize text for consistent processing and comparison.
    
    This function standardizes whitespace, punctuation, and formatting
    to enable reliable text comparison between Vision OCR and DocAI outputs.
    
    Args:
        text: Raw text to normalize
        
    Returns:
        Normalized text string
        
    Example:
        >>> normalize_text("Line 1  \\r\\n\\nLine 2   ,  word")
        "Line 1\\nLine 2, word"
    """
    if not text:
        return ""
    
    # Convert Windows line endings to Unix
    text = text.replace('\r\n', '\n')
    
    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([,.:;?!])', r'\1', text)
    
    # Fix spacing around parentheses and brackets
    text = re.sub(r'\s*\(\s*', '(', text)
    text = re.sub(r'\s*\)\s*', ')', text)
    text = re.sub(r'\s*\[\s*', '[', text)
    text = re.sub(r'\s*\]\s*', ']', text)
    
    # Preserve intentional line breaks but normalize paragraphs
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text specifically for comparison between different sources.
    
    This is more aggressive normalization for comparing Vision OCR
    and DocAI text outputs, removing formatting differences.
    
    Args:
        text: Text to normalize for comparison
        
    Returns:
        Heavily normalized text for comparison
    """
    if not text:
        return ""
    
    # Start with basic normalization
    text = normalize_text(text)
    
    # Remove all line breaks for comparison
    text = text.replace('\n', ' ')
    
    # Normalize multiple spaces again after line break removal
    text = re.sub(r'\s+', ' ', text)
    
    # Convert to lowercase for case-insensitive comparison
    text = text.lower()
    
    return text.strip()


def extract_text_segments(text: str, max_segment_length: int = 1000) -> List[str]:
    """
    Split text into manageable segments for processing.
    
    Args:
        text: Text to segment
        max_segment_length: Maximum length per segment
        
    Returns:
        List of text segments
    """
    if not text or len(text) <= max_segment_length:
        return [text] if text else []
    
    segments = []
    current_pos = 0
    
    while current_pos < len(text):
        end_pos = min(current_pos + max_segment_length, len(text))
        
        # Try to break at sentence boundaries
        if end_pos < len(text):
            # Look for sentence endings within the last 100 characters
            for i in range(end_pos - 100, end_pos):
                if i > current_pos and text[i] in '.!?':
                    end_pos = i + 1
                    break
        
        segments.append(text[current_pos:end_pos])
        current_pos = end_pos
    
    return segments


def validate_text_encoding(text: str) -> Tuple[bool, List[str]]:
    """
    Validate text encoding and identify potential issues.
    
    Args:
        text: Text to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check for common encoding issues
    if '\ufffd' in text:  # Unicode replacement character
        issues.append("Contains Unicode replacement characters (encoding errors)")
    
    # Check for unusual character patterns
    control_chars = re.findall(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', text)
    if control_chars:
        issues.append(f"Contains {len(control_chars)} control characters")
    
    # Check for mixed line endings
    if '\r\n' in text and '\n' in text.replace('\r\n', ''):
        issues.append("Mixed line ending types detected")
    
    # Check for excessive whitespace
    if re.search(r'\s{10,}', text):
        issues.append("Contains excessive whitespace sequences")
    
    return len(issues) == 0, issues


def calculate_text_similarity(text1: str, text2: str) -> Dict[str, float]:
    """
    Calculate various similarity metrics between two texts.
    
    Args:
        text1: First text for comparison
        text2: Second text for comparison
        
    Returns:
        Dictionary with similarity metrics
    """
    from difflib import SequenceMatcher
    
    # Normalize texts for comparison
    norm1 = normalize_for_comparison(text1)
    norm2 = normalize_for_comparison(text2)
    
    # Calculate different similarity metrics
    similarity_metrics = {}
    
    # Character-level similarity
    similarity_metrics["character_similarity"] = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Word-level similarity
    words1 = norm1.split()
    words2 = norm2.split()
    similarity_metrics["word_similarity"] = SequenceMatcher(None, words1, words2).ratio()
    
    # Length-based similarity
    if max(len(norm1), len(norm2)) > 0:
        length_ratio = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
        similarity_metrics["length_similarity"] = length_ratio
    else:
        similarity_metrics["length_similarity"] = 1.0
    
    # Combined similarity score
    similarity_metrics["combined_similarity"] = (
        similarity_metrics["character_similarity"] * 0.5 +
        similarity_metrics["word_similarity"] * 0.3 +
        similarity_metrics["length_similarity"] * 0.2
    )
    
    return similarity_metrics