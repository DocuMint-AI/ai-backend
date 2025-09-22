"""
Keywords Loader for Dynamic Classifier Configuration

This module provides dynamic loading capabilities for legal document keywords
supporting both Python dict format and JSON files. It normalizes different
keyword entry formats into a unified structure for the classifier.

Features:
- Loads from Python dict (INDIAN_LEGAL_DOCUMENT_KEYWORDS, CATEGORY_MAPPING)
- Loads from JSON files (legal_keywords.json)
- Supports both legacy string arrays and extended pattern objects
- Normalizes to unified format with weights and regex flags
- Provides validation and error handling
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Union, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class KeywordEntry:
    """
    Normalized keyword entry with weight and regex support.
    
    Supports both legacy string format and extended pattern objects:
    - Legacy: "keyword string"
    - Extended: {"pattern": "regex", "weight": 2.5, "is_regex": true}
    """
    
    def __init__(self, pattern: str, weight: float = 1.0, is_regex: bool = False):
        self.pattern = pattern
        self.weight = weight
        self.is_regex = is_regex
    
    @classmethod
    def from_entry(cls, entry: Union[str, Dict[str, Any]]) -> "KeywordEntry":
        """
        Create KeywordEntry from various input formats.
        
        Args:
            entry: String or dict with pattern definition
            
        Returns:
            Normalized KeywordEntry instance
            
        Examples:
            >>> KeywordEntry.from_entry("simple keyword")
            KeywordEntry(pattern="simple keyword", weight=1.0, is_regex=False)
            
            >>> KeywordEntry.from_entry({
            ...     "pattern": "hon'?ble\\s+justice", 
            ...     "weight": 3.0, 
            ...     "is_regex": True
            ... })
            KeywordEntry(pattern="hon'?ble\\s+justice", weight=3.0, is_regex=True)
        """
        if isinstance(entry, str):
            return cls(pattern=entry, weight=1.0, is_regex=False)
        
        elif isinstance(entry, dict):
            pattern = entry.get("pattern", "")
            weight = float(entry.get("weight", 1.0))
            is_regex = bool(entry.get("is_regex", False))
            
            if not pattern:
                raise ValueError(f"Pattern is required in keyword entry: {entry}")
            
            return cls(pattern=pattern, weight=weight, is_regex=is_regex)
        
        else:
            raise ValueError(f"Invalid keyword entry format: {type(entry)} - {entry}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pattern": self.pattern,
            "weight": self.weight,
            "is_regex": self.is_regex
        }
    
    def __repr__(self) -> str:
        return f"KeywordEntry(pattern='{self.pattern}', weight={self.weight}, is_regex={self.is_regex})"


class KeywordsLoader:
    """
    Dynamic keyword loader supporting multiple sources and formats.
    
    Loads legal document keywords from:
    1. Python dict format (legacy compatibility)
    2. JSON files with extended pattern support
    3. Environment variable configuration
    
    Normalizes all formats into unified KeywordEntry structure.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize keywords loader.
        
        Args:
            debug: Enable debug logging for keyword loading
        """
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
    
    def load_from_python_dict(
        self, 
        keywords_dict: Dict[str, List[Union[str, Dict[str, Any]]]], 
        category_mapping: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Load keywords from Python dictionary format.
        
        Args:
            keywords_dict: Dictionary mapping subcategories to keyword lists
            category_mapping: Dictionary mapping major categories to subcategories
            
        Returns:
            Unified format: {"keywords": {...}, "category_mapping": {...}}
        """
        logger.debug(f"Loading keywords from Python dict: {len(keywords_dict)} subcategories")
        
        normalized_keywords = {}
        
        for subcategory, entries in keywords_dict.items():
            normalized_entries = []
            
            for entry in entries:
                try:
                    keyword_entry = KeywordEntry.from_entry(entry)
                    normalized_entries.append(keyword_entry)
                    
                except ValueError as e:
                    logger.warning(f"Skipping invalid keyword entry in '{subcategory}': {e}")
                    continue
            
            normalized_keywords[subcategory] = normalized_entries
            logger.debug(f"Loaded {len(normalized_entries)} keywords for '{subcategory}'")
        
        total_keywords = sum(len(entries) for entries in normalized_keywords.values())
        logger.info(f"Loaded {total_keywords} keywords across {len(normalized_keywords)} subcategories from Python dict")
        
        return {
            "keywords": normalized_keywords,
            "category_mapping": category_mapping
        }
    
    def load_from_json_file(self, json_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load keywords from JSON file.
        
        Expected JSON format:
        {
            "keywords": {
                "subcategory": [
                    "simple keyword",
                    {"pattern": "regex", "weight": 2.0, "is_regex": true}
                ]
            },
            "category_mapping": {
                "Major_Category": ["subcategory1", "subcategory2"]
            }
        }
        
        Args:
            json_path: Path to JSON keywords file
            
        Returns:
            Unified format: {"keywords": {...}, "category_mapping": {...}}
            
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON format is invalid
        """
        json_path = Path(json_path)
        
        if not json_path.exists():
            raise FileNotFoundError(f"Keywords JSON file not found: {json_path}")
        
        logger.debug(f"Loading keywords from JSON file: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {json_path}: {e}")
        
        # Validate required structure
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be an object in {json_path}")
        
        if "keywords" not in data or "category_mapping" not in data:
            raise ValueError(f"JSON must contain 'keywords' and 'category_mapping' in {json_path}")
        
        keywords_dict = data["keywords"]
        category_mapping = data["category_mapping"]
        
        # Normalize keywords using the same logic as Python dict loading
        return self.load_from_python_dict(keywords_dict, category_mapping)
    
    def load_keywords(self, source: Optional[Union[str, Path, Tuple[Dict, Dict]]] = None) -> Dict[str, Any]:
        """
        Load keywords from specified source or auto-detect.
        
        Args:
            source: One of:
                - None: Auto-detect (Python dict > JSON file)
                - str/Path: JSON file path
                - Tuple[Dict, Dict]: (keywords_dict, category_mapping)
                
        Returns:
            Unified format: {"keywords": {...}, "category_mapping": {...}}
            
        Examples:
            >>> loader = KeywordsLoader()
            
            # Auto-detect (uses Python dict if available)
            >>> data = loader.load_keywords()
            
            # Load from JSON file
            >>> data = loader.load_keywords("legal_keywords.json")
            
            # Load from Python dicts
            >>> data = loader.load_keywords((keywords_dict, category_mapping))
        """
        if source is None:
            # Auto-detect: Try Python dict first, then JSON file
            return self._auto_detect_source()
        
        elif isinstance(source, (str, Path)):
            # Load from JSON file
            return self.load_from_json_file(source)
        
        elif isinstance(source, tuple) and len(source) == 2:
            # Load from Python dicts
            keywords_dict, category_mapping = source
            return self.load_from_python_dict(keywords_dict, category_mapping)
        
        else:
            raise ValueError(f"Invalid source type: {type(source)} - {source}")
    
    def _auto_detect_source(self) -> Dict[str, Any]:
        """
        Auto-detect keywords source: Python dict > JSON file > error.
        
        Returns:
            Unified keyword data
            
        Raises:
            ImportError: If Python dict not available and no JSON file found
        """
        # Try to import Python dict format
        try:
            from .legal_keywords import INDIAN_LEGAL_DOCUMENT_KEYWORDS, CATEGORY_MAPPING
            logger.info("Auto-detected: Using Python dict keywords (legal_keywords.py)")
            return self.load_from_python_dict(INDIAN_LEGAL_DOCUMENT_KEYWORDS, CATEGORY_MAPPING)
        
        except ImportError:
            logger.debug("Python dict keywords not available, trying JSON file")
        
        # Try JSON file in same directory
        json_file = Path(__file__).parent / "legal_keywords.json"
        if json_file.exists():
            logger.info(f"Auto-detected: Using JSON keywords file ({json_file})")
            return self.load_from_json_file(json_file)
        
        # Try JSON file in project root
        project_root = Path(__file__).parent.parent.parent
        json_file = project_root / "legal_keywords.json"
        if json_file.exists():
            logger.info(f"Auto-detected: Using JSON keywords file ({json_file})")
            return self.load_from_json_file(json_file)
        
        raise ImportError(
            "No keywords source found. Please either:\n"
            "1. Ensure legal_keywords.py is available with INDIAN_LEGAL_DOCUMENT_KEYWORDS\n"
            "2. Provide legal_keywords.json file\n"
            "3. Specify source explicitly"
        )
    
    def validate_keywords_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate keywords data structure.
        
        Args:
            data: Keywords data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check top-level structure
            if not isinstance(data, dict):
                logger.error("Keywords data must be a dictionary")
                return False
            
            if "keywords" not in data or "category_mapping" not in data:
                logger.error("Keywords data must contain 'keywords' and 'category_mapping'")
                return False
            
            keywords = data["keywords"]
            category_mapping = data["category_mapping"]
            
            # Validate keywords structure
            if not isinstance(keywords, dict):
                logger.error("'keywords' must be a dictionary")
                return False
            
            for subcategory, entries in keywords.items():
                if not isinstance(entries, list):
                    logger.error(f"Keywords for '{subcategory}' must be a list")
                    return False
                
                for entry in entries:
                    if not isinstance(entry, KeywordEntry):
                        logger.error(f"Invalid keyword entry type in '{subcategory}': {type(entry)}")
                        return False
            
            # Validate category mapping
            if not isinstance(category_mapping, dict):
                logger.error("'category_mapping' must be a dictionary")
                return False
            
            for category, subcategories in category_mapping.items():
                if not isinstance(subcategories, list):
                    logger.error(f"Subcategories for '{category}' must be a list")
                    return False
                
                # Check that all subcategories exist in keywords
                for subcategory in subcategories:
                    if subcategory not in keywords:
                        logger.warning(f"Subcategory '{subcategory}' in category '{category}' not found in keywords")
            
            logger.debug("Keywords data validation passed")
            return True
        
        except Exception as e:
            logger.error(f"Error validating keywords data: {e}")
            return False
    
    def get_keywords_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary statistics for loaded keywords.
        
        Args:
            data: Keywords data
            
        Returns:
            Summary statistics
        """
        keywords = data["keywords"]
        category_mapping = data["category_mapping"]
        
        total_keywords = sum(len(entries) for entries in keywords.values())
        total_subcategories = len(keywords)
        total_categories = len(category_mapping)
        
        # Weight statistics
        all_weights = []
        regex_count = 0
        
        for entries in keywords.values():
            for entry in entries:
                all_weights.append(entry.weight)
                if entry.is_regex:
                    regex_count += 1
        
        avg_weight = sum(all_weights) / len(all_weights) if all_weights else 0
        
        summary = {
            "total_keywords": total_keywords,
            "total_subcategories": total_subcategories,
            "total_categories": total_categories,
            "regex_patterns": regex_count,
            "string_patterns": total_keywords - regex_count,
            "average_weight": round(avg_weight, 2),
            "weight_range": [min(all_weights), max(all_weights)] if all_weights else [0, 0]
        }
        
        return summary


def create_keywords_loader(debug: Optional[bool] = None) -> KeywordsLoader:
    """
    Factory function to create keywords loader with environment configuration.
    
    Args:
        debug: Enable debug mode (defaults to CLASSIFIER_DEBUG env var)
        
    Returns:
        Configured KeywordsLoader instance
    """
    if debug is None:
        debug = os.getenv("CLASSIFIER_DEBUG", "false").lower() in ("true", "1", "yes", "on")
    
    return KeywordsLoader(debug=debug)


def load_keywords(source: Optional[Union[str, Path, Tuple[Dict, Dict]]] = None) -> Dict[str, Any]:
    """
    Convenience function to load keywords with default configuration.
    
    Args:
        source: Keywords source (auto-detect if None)
        
    Returns:
        Unified keywords data
        
    Example:
        >>> data = load_keywords()  # Auto-detect
        >>> print(f"Loaded {data['total_keywords']} keywords")
    """
    loader = create_keywords_loader()
    return loader.load_keywords(source)


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test loading keywords
    try:
        loader = create_keywords_loader(debug=True)
        data = loader.load_keywords()
        
        # Validate and summarize
        is_valid = loader.validate_keywords_data(data)
        if is_valid:
            summary = loader.get_keywords_summary(data)
            print(f"Keywords loaded successfully: {summary}")
        else:
            print("Keywords validation failed")
    
    except Exception as e:
        logger.error(f"Failed to load keywords: {e}")