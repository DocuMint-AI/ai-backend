"""
Production-Ready Weighted Regex Document Classifier

This module provides a sophisticated regex-based document classification system with:
- Dynamic keyword loading from Python dict or JSON files
- Weighted pattern matching with per-pattern weights and regex support
- Comprehensive match extraction with context and position tracking
- Advanced scoring with weighted frequency and diversity coverage
- Configurable confidence thresholds and debug logging
- Full compatibility with orchestration pipeline

Features:
- Supports legacy string arrays and extended pattern objects
- Compiles regex patterns once for performance
- Extracts matched patterns with frequency, positions, context snippets
- Computes category scores using weighted frequency + diversity coverage
- Maps scores to confidence levels: very_low, low, medium, high
- Exports complete classification_verdict.json for pipeline
- Deterministic results for consistent testing
"""

import re
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict

from .keywords_loader import create_keywords_loader, KeywordEntry

logger = logging.getLogger(__name__)


@dataclass
class MatchedPattern:
    """Represents a matched pattern in the document text with enhanced metadata."""
    keyword: str
    category: str
    subcategory: str
    frequency: int
    weight: float
    weighted_score: float  # frequency * weight
    positions: List[int]
    context_snippets: List[str]
    is_regex: bool
    pattern_type: str  # "string" or "regex"


@dataclass
class ClassificationResult:
    """Complete classification result for a document with enhanced scoring."""
    label: str
    score: float
    confidence: str
    matched_patterns: List[MatchedPattern]
    text_length: int
    total_matches: int
    total_weighted_score: float
    category_scores: Dict[str, float]
    diversity_scores: Dict[str, float]  # Coverage of unique patterns per category
    processing_metadata: Dict[str, Any]
    summary: Dict[str, Any]  # Primary label, confidence, score, top keywords


class WeightedRegexDocumentClassifier:
    """
    Production-ready weighted regex document classifier.
    
    Features:
    - Dynamic keyword loading from multiple sources
    - Per-pattern weights and regex support
    - Advanced scoring with frequency + diversity
    - Comprehensive match extraction and context
    - Configurable confidence thresholds
    - Debug logging and observability
    """
    
    def __init__(
        self, 
        keywords_source: Optional[Any] = None,
        confidence_thresholds: Optional[Dict[str, float]] = None,
        debug: Optional[bool] = None
    ):
        """
        Initialize the weighted regex classifier.
        
        Args:
            keywords_source: Keywords source (auto-detect if None)
            confidence_thresholds: Custom confidence level thresholds
            debug: Enable debug logging (defaults to CLASSIFIER_DEBUG env var)
        """
        # Configure debug mode
        if debug is None:
            debug = os.getenv("CLASSIFIER_DEBUG", "false").lower() in ("true", "1", "yes", "on")
        
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        
        # Load keywords dynamically
        loader = create_keywords_loader(debug=debug)
        self.keywords_data = loader.load_keywords(keywords_source)
        
        self.keywords = self.keywords_data["keywords"]
        self.category_mapping = self.keywords_data["category_mapping"]
        
        # Configure confidence thresholds
        self.confidence_thresholds = confidence_thresholds or {
            "very_low": 0.0,
            "low": 0.1,
            "medium": 0.4,
            "high": 0.7
        }
        
        # Compile regex patterns for performance
        self._compiled_patterns = self._compile_patterns()
        
        # Log initialization
        total_patterns = sum(len(patterns) for patterns in self._compiled_patterns.values())
        logger.info(f"WeightedRegexDocumentClassifier initialized with {total_patterns} patterns across {len(self._compiled_patterns)} subcategories")
        
        if self.debug:
            summary = loader.get_keywords_summary(self.keywords_data)
            logger.debug(f"Keywords summary: {summary}")
    
    def _compile_patterns(self) -> Dict[str, Dict[str, Tuple[re.Pattern, KeywordEntry]]]:
        """
        Compile all keyword patterns for efficient matching.
        
        Returns:
            Dict mapping subcategory -> {pattern_key: (compiled_regex, keyword_entry)}
        """
        compiled = {}
        
        for subcategory, keyword_entries in self.keywords.items():
            compiled_subcategory = {}
            
            for i, entry in enumerate(keyword_entries):
                try:
                    if entry.is_regex:
                        # Compile as regex pattern
                        pattern = re.compile(entry.pattern, re.IGNORECASE | re.MULTILINE)
                        pattern_key = f"regex_{i}_{entry.pattern[:50]}"
                    else:
                        # Escape and compile as literal string with word boundaries
                        escaped_pattern = re.escape(entry.pattern)
                        # Add word boundaries for better matching
                        bounded_pattern = rf"\b{escaped_pattern}\b"
                        pattern = re.compile(bounded_pattern, re.IGNORECASE | re.MULTILINE)
                        pattern_key = f"string_{i}_{entry.pattern[:50]}"
                    
                    compiled_subcategory[pattern_key] = (pattern, entry)
                    
                except re.error as e:
                    logger.warning(f"Failed to compile pattern '{entry.pattern}' in subcategory '{subcategory}': {e}")
                    continue
            
            if compiled_subcategory:
                compiled[subcategory] = compiled_subcategory
                logger.debug(f"Compiled {len(compiled_subcategory)} patterns for subcategory '{subcategory}'")
        
        return compiled
    
    def _find_matches(self, text: str, entry: KeywordEntry, pattern: re.Pattern) -> Tuple[int, List[int], List[str]]:
        """
        Find all matches for a specific keyword pattern in text.
        
        Args:
            text: Text to search in
            entry: KeywordEntry with pattern metadata
            pattern: Compiled regex pattern
        
        Returns:
            Tuple of (frequency, positions, context_snippets)
        """
        matches = list(pattern.finditer(text))
        frequency = len(matches)
        positions = [match.start() for match in matches]
        
        # Extract context snippets (100 chars before and after)
        context_snippets = []
        for match in matches:
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].replace('\n', ' ').replace('\r', ' ')
            context_snippets.append(context.strip())
        
        return frequency, positions, context_snippets
    
    def _calculate_category_scores(
        self, 
        matched_patterns: List[MatchedPattern], 
        text_length: int
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Calculate normalized scores for each major category using weighted frequency + diversity.
        
        Args:
            matched_patterns: List of matched patterns
            text_length: Length of analyzed text
        
        Returns:
            Tuple of (category_scores, diversity_scores)
        """
        category_weighted_scores = {}
        category_unique_patterns = {}
        
        # Group patterns by category and calculate scores
        for category, subcategories in self.category_mapping.items():
            weighted_score = 0.0
            unique_patterns = set()
            
            for pattern in matched_patterns:
                if pattern.subcategory in subcategories:
                    weighted_score += pattern.weighted_score
                    unique_patterns.add(pattern.keyword)
            
            category_weighted_scores[category] = weighted_score
            category_unique_patterns[category] = len(unique_patterns)
        
        # Calculate diversity scores (unique patterns per category)
        max_unique = max(category_unique_patterns.values()) if category_unique_patterns.values() else 1
        diversity_scores = {
            category: count / max_unique if max_unique > 0 else 0.0
            for category, count in category_unique_patterns.items()
        }
        
        # Normalize weighted scores by text length (per 1000 characters)
        text_length_normalized = max(text_length / 1000.0, 1.0)
        
        # Combine weighted frequency + diversity coverage (60% frequency + 40% diversity)
        category_scores = {}
        for category in self.category_mapping.keys():
            frequency_score = category_weighted_scores.get(category, 0.0) / text_length_normalized
            diversity_score = diversity_scores.get(category, 0.0)
            
            # Combined score: 60% weighted frequency + 40% diversity coverage
            combined_score = (0.6 * frequency_score) + (0.4 * diversity_score)
            category_scores[category] = combined_score
        
        return category_scores, diversity_scores
    
    def _determine_final_classification(
        self, 
        category_scores: Dict[str, float], 
        matched_patterns: List[MatchedPattern]
    ) -> Tuple[str, float, str]:
        """
        Determine the final classification label and confidence.
        
        Args:
            category_scores: Calculated category scores
            matched_patterns: List of matched patterns
        
        Returns:
            Tuple of (label, score, confidence)
        """
        if not category_scores or all(score == 0 for score in category_scores.values()):
            return "Unclassified", 0.0, "very_low"
        
        # Find the category with highest score
        best_category = max(category_scores.items(), key=lambda x: x[1])
        label = best_category[0]
        score = best_category[1]
        
        # Determine confidence level based on thresholds
        if score >= self.confidence_thresholds["high"]:
            confidence = "high"
        elif score >= self.confidence_thresholds["medium"]:
            confidence = "medium"
        elif score >= self.confidence_thresholds["low"]:
            confidence = "low"
        else:
            confidence = "very_low"
        
        return label, score, confidence
    
    def classify_document(self, parsed_text: str, document_metadata: Optional[Dict] = None) -> ClassificationResult:
        """
        Classify a document based on its parsed text content.
        
        Args:
            parsed_text: The extracted and parsed text from the document
            document_metadata: Optional metadata about the document
            
        Returns:
            ClassificationResult with label, score, and detailed pattern matches
        """
        if not parsed_text or not isinstance(parsed_text, str):
            logger.warning("Empty or invalid text provided for classification")
            return self._create_empty_result()
        
        text_length = len(parsed_text)
        matched_patterns = []
        
        # Process each subcategory and keyword
        for subcategory, compiled_patterns in self._compiled_patterns.items():
            # Find category for this subcategory
            category = None
            for cat, subcats in self.category_mapping.items():
                if subcategory in subcats:
                    category = cat
                    break
            
            if not category:
                logger.warning(f"No category found for subcategory '{subcategory}'")
                continue
            
            # Match patterns in this subcategory
            for pattern_key, (compiled_pattern, entry) in compiled_patterns.items():
                frequency, positions, context_snippets = self._find_matches(
                    parsed_text, entry, compiled_pattern
                )
                
                if frequency > 0:
                    weighted_score = frequency * entry.weight
                    
                    matched_pattern = MatchedPattern(
                        keyword=entry.pattern,
                        category=category,
                        subcategory=subcategory,
                        frequency=frequency,
                        weight=entry.weight,
                        weighted_score=weighted_score,
                        positions=positions,
                        context_snippets=context_snippets,
                        is_regex=entry.is_regex,
                        pattern_type="regex" if entry.is_regex else "string"
                    )
                    
                    matched_patterns.append(matched_pattern)
                    
                    if self.debug:
                        logger.debug(f"Matched '{entry.pattern}' in {category}/{subcategory}: "
                                   f"freq={frequency}, weight={entry.weight}, score={weighted_score:.2f}")
        
        # Calculate category scores
        category_scores, diversity_scores = self._calculate_category_scores(matched_patterns, text_length)
        
        # Determine final classification
        label, score, confidence = self._determine_final_classification(category_scores, matched_patterns)
        
        # Calculate summary statistics
        total_matches = sum(pattern.frequency for pattern in matched_patterns)
        total_weighted_score = sum(pattern.weighted_score for pattern in matched_patterns)
        
        # Get top keywords for summary
        top_patterns = sorted(matched_patterns, key=lambda x: x.weighted_score, reverse=True)[:5]
        top_keywords = [p.keyword for p in top_patterns]
        
        # Create processing metadata
        processing_metadata = {
            "classifier_version": "2.0.0",
            "classification_method": "weighted_regex_pattern_matching",
            "total_patterns_checked": sum(len(patterns) for patterns in self._compiled_patterns.values()),
            "confidence_thresholds": self.confidence_thresholds,
            "document_metadata": document_metadata or {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Create summary
        summary = {
            "primary_label": label,
            "confidence": confidence,
            "score": round(score, 3),
            "top_keywords": top_keywords,
            "total_matches": total_matches,
            "categories_considered": len([c for c, s in category_scores.items() if s > 0])
        }
        
        result = ClassificationResult(
            label=label,
            score=score,
            confidence=confidence,
            matched_patterns=matched_patterns,
            text_length=text_length,
            total_matches=total_matches,
            total_weighted_score=total_weighted_score,
            category_scores=category_scores,
            diversity_scores=diversity_scores,
            processing_metadata=processing_metadata,
            summary=summary
        )
        
        logger.info(f"Document classified as '{label}' with score {score:.3f} ({confidence} confidence)")
        logger.debug(f"Found {total_matches} total matches with weighted score {total_weighted_score:.2f}")
        
        if self.debug:
            for category, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:3]:
                logger.debug(f"Category '{category}': score={score:.3f}, diversity={diversity_scores.get(category, 0):.3f}")
        
        return result
    
    def _create_empty_result(self) -> ClassificationResult:
        """Create empty classification result for invalid input."""
        return ClassificationResult(
            label="Unclassified",
            score=0.0,
            confidence="very_low",
            matched_patterns=[],
            text_length=0,
            total_matches=0,
            total_weighted_score=0.0,
            category_scores={},
            diversity_scores={},
            processing_metadata={
                "classifier_version": "2.0.0",
                "classification_method": "weighted_regex_pattern_matching",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": "Empty or invalid input text"
            },
            summary={
                "primary_label": "Unclassified",
                "confidence": "very_low",
                "score": 0.0,
                "top_keywords": [],
                "total_matches": 0,
                "categories_considered": 0
            }
        )
    
    def export_classification_verdict(self, result: ClassificationResult) -> Dict[str, Any]:
        """
        Export classification result as a structured dictionary for JSON serialization.
        
        Args:
            result: ClassificationResult to export
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        # Convert dataclass to dict and ensure JSON serializability
        verdict = asdict(result)
        
        # Ensure timestamp is present
        if "timestamp" not in verdict["processing_metadata"]:
            verdict["processing_metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add summary statistics for easier consumption
        verdict["statistics"] = {
            "total_patterns_matched": len(result.matched_patterns),
            "unique_categories_found": len([s for s in result.category_scores.values() if s > 0]),
            "average_pattern_weight": (
                sum(p.weight for p in result.matched_patterns) / len(result.matched_patterns)
                if result.matched_patterns else 0.0
            ),
            "text_coverage_ratio": result.total_matches / result.text_length if result.text_length > 0 else 0.0
        }
        
        return verdict


# Legacy compatibility function (must come first to maintain old API)
def create_classifier() -> WeightedRegexDocumentClassifier:
    """Legacy factory function for backward compatibility."""
    return WeightedRegexDocumentClassifier()


# Enhanced factory function for new features
def create_weighted_classifier(
    keywords_source: Optional[Any] = None,
    confidence_thresholds: Optional[Dict[str, float]] = None,
    debug: Optional[bool] = None
) -> WeightedRegexDocumentClassifier:
    """
    Factory function to create a configured classifier instance with advanced options.
    
    Args:
        keywords_source: Keywords source (auto-detect if None)
        confidence_thresholds: Custom confidence thresholds
        debug: Enable debug mode
    
    Returns:
        Configured WeightedRegexDocumentClassifier instance
    """
    return WeightedRegexDocumentClassifier(
        keywords_source=keywords_source,
        confidence_thresholds=confidence_thresholds,
        debug=debug
    )


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Create classifier with debug enabled
    classifier = create_classifier(debug=True)
    
    # Test with sample legal text
    sample_text = """
    This judgment is delivered by Hon'ble Justice Smith in the matter of ABC vs State.
    The petitioner filed a writ petition under Article 226 of the Constitution of India.
    The matter relates to the interpretation of Section 15 of the Indian Contract Act.
    After hearing the learned counsel for both parties, this Court finds that the 
    plaintiff has made out a prima facie case. The defendant's objections are overruled.
    Accordingly, this writ petition is allowed and the impugned order is set aside.
    """
    
    result = classifier.classify_document(sample_text)
    verdict = classifier.export_classification_verdict(result)
    
    print(json.dumps(verdict, indent=2, default=str))