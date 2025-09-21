# Template Matching System Documentation

This directory contains the production-ready weighted regex document classifier for the AI Backend system. The classifier provides deterministic, explainable document classification using legal keyword patterns with advanced scoring and confidence mapping.

## Overview

The template matching system consists of three main components:

1. **Keywords Loader** (`keywords_loader.py`) - Dynamic keyword loading from Python dict or JSON files
2. **Weighted Regex Classifier** (`regex_classifier.py`) - Production-ready classification engine with weighted patterns
3. **Legal Keywords** (`legal_keywords.py`) - Comprehensive Indian legal document keyword database

## Quick Start

```python
from services.template_matching.regex_classifier import create_classifier

# Create classifier with default settings
classifier = create_classifier()

# Classify a document
result = classifier.classify_document(text)
verdict = classifier.export_classification_verdict(result)

print(f"Classification: {verdict['label']} ({verdict['confidence']})")
print(f"Score: {verdict['score']:.3f}")
```

## Features

### ✅ **Weighted Pattern Matching**
- Per-pattern weights for importance tuning
- Regex and string pattern support
- Backward compatible with legacy keyword lists

### ✅ **Advanced Scoring**
- Weighted frequency scoring (60%)
- Diversity coverage scoring (40%)
- Text length normalization
- Configurable confidence thresholds

### ✅ **Comprehensive Output**
- Matched patterns with context snippets
- Category scores and diversity metrics
- Processing metadata and timestamps
- Summary statistics for easy consumption

### ✅ **Dynamic Configuration**
- Auto-detect keywords from Python dict or JSON files
- Environment-based debug mode (`CLASSIFIER_DEBUG=true`)
- Custom confidence threshold configuration
- Hot-swappable keyword sources

## Classification Categories

The system classifies documents into 9 major categories:

1. **Constitutional_and_Legislative** - Constitution, acts, statutes, rules
2. **Judicial_Documents** - Judgments, orders, court proceedings
3. **Personal_and_Family** - Marriage, divorce, adoption documents
4. **Property_and_Real_Estate** - Sale deeds, leases, mortgages
5. **Business_and_Corporate** - Company documents, contracts
6. **Intellectual_Property** - Patents, trademarks, copyrights
7. **Financial_and_Security** - Loans, banking, insurance documents
8. **Licenses_Permits_Certificates** - Professional and business licenses
9. **Specialized_Documents** - Trusts, employment, immigration docs

## Configuration

### Basic Configuration

```python
from services.template_matching.regex_classifier import create_weighted_classifier

# Enable debug logging
classifier = create_weighted_classifier(debug=True)

# Custom confidence thresholds
custom_thresholds = {
    "very_low": 0.0,
    "low": 0.2,     # Default: 0.1
    "medium": 0.5,  # Default: 0.4  
    "high": 0.8     # Default: 0.7
}

classifier = create_weighted_classifier(confidence_thresholds=custom_thresholds)
```

### Environment Variables

```bash
# Enable debug logging for detailed pattern matching logs
CLASSIFIER_DEBUG=true

# Configure Google Cloud Vision OCR (if using pipeline)
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## Keyword Management

### Current Format (Python Dict)

Keywords are stored in `legal_keywords.py` as string arrays:

```python
INDIAN_LEGAL_DOCUMENT_KEYWORDS = {
    "judgments_orders": [
        "judgment", "order", "decree", "interim order",
        "hon'ble justice", "ratio decidendi", "disposed of"
    ],
    # ... more subcategories
}
```

### Extended Format (Future Enhancement)

For advanced pattern control, you can use the extended JSON format:

```json
{
  "keywords": {
    "judgments_orders": [
      "judgment",
      {"pattern": "hon'?ble\\s+justice", "weight": 3.0, "is_regex": true},
      {"pattern": "ratio decidendi", "weight": 2.5},
      "order"
    ]
  },
  "category_mapping": {
    "Judicial_Documents": ["judgments_orders", "court_proceedings"]
  }
}
```

### Weight Guidelines

- **High Weight (2.5-5.0)**: Strong discriminative patterns
  - `"hon'ble justice"` (3.0) - Strong judicial indicator
  - `"ratio decidendi"` (2.5) - Legal reasoning marker
  - `"sale deed"` (3.0) - Clear property document marker

- **Medium Weight (1.5-2.4)**: Moderately specific patterns
  - `"writ petition"` (2.0) - Common judicial filing
  - `"mortgage deed"` (2.0) - Property document type

- **Default Weight (1.0)**: General patterns
  - `"section"`, `"act"`, `"court"` - Common legal terms
  - Most existing keywords use default weight

- **Low Weight (0.5-0.9)**: Weak but relevant patterns
  - Very common terms that appear across categories
  - Boilerplate language indicators

## Tuning Performance

### 1. Analyzing Classification Results

Enable debug mode to see detailed pattern matching:

```python
import os
os.environ["CLASSIFIER_DEBUG"] = "true"

from services.template_matching.regex_classifier import create_weighted_classifier

classifier = create_weighted_classifier(debug=True)
result = classifier.classify_document(text)

# Check debug logs for:
# - Which patterns matched
# - Pattern frequencies and weights
# - Category score calculations
```

### 2. Adjusting Confidence Thresholds

Monitor classification confidence distribution:

```python
# Collect classification results
results = []
for document in documents:
    result = classifier.classify_document(document.text)
    results.append(result)

# Analyze confidence distribution
confidence_dist = {}
for result in results:
    conf = result.confidence
    confidence_dist[conf] = confidence_dist.get(conf, 0) + 1

print("Confidence Distribution:", confidence_dist)

# Adjust thresholds based on distribution
# Lower thresholds if too many "very_low" classifications
# Raise thresholds if too many "high" classifications without clear patterns
```

### 3. Adding New Keywords

To add keywords for better classification:

1. **Identify misclassified documents**:
   ```python
   # Find documents with low confidence or wrong classification
   low_confidence = [r for r in results if r.confidence in ["very_low", "low"]]
   ```

2. **Analyze text for distinctive patterns**:
   ```python
   # Look for distinctive phrases in misclassified documents
   for result in low_confidence:
       print(f"Document classified as: {result.label}")
       print(f"Text sample: {result.text[:500]}...")
       print(f"Matched patterns: {[p.keyword for p in result.matched_patterns]}")
   ```

3. **Add new keywords to appropriate subcategories**:
   ```python
   # Example: Adding bankruptcy-related terms
   INDIAN_LEGAL_DOCUMENT_KEYWORDS["recovery_documents"].extend([
       "bankruptcy petition", "insolvency proceedings", "liquidation order"
   ])
   ```

### 4. Creating Regex Patterns

For complex pattern matching, use regex patterns:

```python
# Pattern for case numbers with regex
case_number_patterns = [
    {"pattern": r"\b(civil|criminal)\s+appeal\s+no\.?\s*\d+", "weight": 2.5, "is_regex": True},
    {"pattern": r"\bw\.?p\.?\s*\(c\)\s*no\.?\s*\d+", "weight": 2.0, "is_regex": True},  # Writ petition
    {"pattern": r"\bslp\s*\(c\)\s*no\.?\s*\d+", "weight": 2.0, "is_regex": True},      # Special Leave Petition
]
```

**Regex Best Practices**:
- Use word boundaries (`\b`) to avoid partial matches
- Make whitespace flexible with `\s+` or `\s*`
- Use non-capturing groups `(?:...)` when grouping without capturing
- Test patterns thoroughly with real document text
- Start with weight 1.0 and adjust based on performance

## Debugging and Troubleshooting

### Common Issues

1. **Low Classification Scores**
   - **Cause**: Insufficient keywords for document type
   - **Solution**: Add more specific keywords for the category
   - **Debug**: Check `matched_patterns` in classification result

2. **Wrong Classifications**
   - **Cause**: Overlapping keywords between categories
   - **Solution**: Increase weights for distinctive patterns
   - **Debug**: Compare `category_scores` across categories

3. **Inconsistent Results**
   - **Cause**: Borderline documents with similar scores across categories
   - **Solution**: Add more distinctive patterns or adjust confidence thresholds
   - **Debug**: Enable debug logging to see score calculations

### Debug Log Analysis

When `CLASSIFIER_DEBUG=true`, logs show:

```
DEBUG - Matched 'hon'ble justice' in Judicial_Documents/judgments_orders: freq=2, weight=3.0, score=6.00
DEBUG - Category 'Judicial_Documents': score=8.500, diversity=0.750
DEBUG - Category 'Constitutional_and_Legislative': score=2.100, diversity=0.333
```

**Interpreting Logs**:
- `freq=2`: Pattern appears 2 times in text
- `weight=3.0`: Pattern has high importance weight
- `score=6.00`: Weighted score (freq × weight)
- `diversity=0.750`: 75% of possible pattern types found in category

### Testing New Configurations

Use the smoke test to validate changes:

```bash
# Test basic functionality
python scripts/test_regex_classifier_smoke.py

# Test with real documents
python scripts/test_single_orchestration.py
python scripts/test_hybrid_pipeline.py
```

## API Reference

### Core Classes

#### `WeightedRegexDocumentClassifier`

Main classifier class with weighted pattern matching.

```python
classifier = WeightedRegexDocumentClassifier(
    keywords_source=None,           # Auto-detect or specify source
    confidence_thresholds=None,     # Custom thresholds
    debug=False                     # Enable debug logging
)
```

#### `ClassificationResult`

Complete classification result with enhanced metadata.

```python
@dataclass
class ClassificationResult:
    label: str                      # Primary classification label
    score: float                    # Normalized classification score
    confidence: str                 # Confidence level: very_low, low, medium, high
    matched_patterns: List[MatchedPattern]  # All matched patterns
    text_length: int                # Input text length
    total_matches: int              # Total pattern matches
    total_weighted_score: float     # Sum of all weighted scores
    category_scores: Dict[str, float]       # Scores per category
    diversity_scores: Dict[str, float]      # Diversity scores per category
    processing_metadata: Dict[str, Any]     # Processing metadata
    summary: Dict[str, Any]         # Summary for easy consumption
```

#### `MatchedPattern`

Individual pattern match with context.

```python
@dataclass
class MatchedPattern:
    keyword: str                    # Matched keyword/pattern
    category: str                   # Major category
    subcategory: str               # Specific subcategory
    frequency: int                 # Number of matches
    weight: float                  # Pattern weight
    weighted_score: float          # frequency × weight
    positions: List[int]           # Match positions in text
    context_snippets: List[str]    # Context around matches
    is_regex: bool                 # Whether pattern is regex
    pattern_type: str              # "string" or "regex"
```

### Factory Functions

```python
# Legacy compatibility (no arguments)
from services.template_matching.regex_classifier import create_classifier
classifier = create_classifier()

# Enhanced version (with arguments)
from services.template_matching.regex_classifier import create_weighted_classifier
classifier = create_weighted_classifier(debug=True, confidence_thresholds=custom_thresholds)
```

### Keywords Loading

```python
from services.template_matching.keywords_loader import load_keywords

# Auto-detect keywords source
data = load_keywords()

# Load from specific JSON file
data = load_keywords("custom_keywords.json")

# Load from Python dicts
data = load_keywords((keywords_dict, category_mapping))
```

## Pipeline Integration

The classifier integrates seamlessly with the document processing pipeline:

1. **Upload PDF** → Convert to images
2. **Vision OCR** → Extract text from images  
3. **Text Processing** → Merge OCR + fallback text
4. **Classification** → Weighted regex classification ← **This component**
5. **KAG Generation** → Create knowledge graph input

### Pipeline Configuration

```python
# In orchestration pipeline
from services.template_matching.regex_classifier import create_classifier

classifier = create_classifier()
classification_result = classifier.classify_document(full_text)
verdict_dict = classifier.export_classification_verdict(classification_result)

# Save classification verdict
with open("classification_verdict.json", "w") as f:
    json.dump(verdict_dict, f, indent=2)
```

## File Structure

```
services/template_matching/
├── README.md                      # This documentation
├── keywords_loader.py             # Dynamic keyword loading
├── regex_classifier.py            # Main classification engine  
├── legal_keywords.py              # Indian legal keywords database
└── class_template.py              # Legacy template matcher (deprecated)
```

## Performance Considerations

- **Regex Compilation**: Patterns are compiled once during initialization
- **Memory Usage**: ~784 patterns consume minimal memory
- **Processing Speed**: ~1000 documents/second on modern hardware
- **Scalability**: Stateless design enables horizontal scaling

## Version History

- **v2.0.0** (Current) - Weighted regex classifier with dynamic loading
- **v1.0.0** - Basic regex classifier with fixed keywords

## Contributing

When adding new features or keywords:

1. Test with the smoke test suite
2. Update documentation for new configuration options  
3. Add debug logging for new functionality
4. Maintain backward compatibility with existing pipelines
5. Follow the established pattern weight guidelines

---

For more examples and advanced usage, see the test files in `scripts/test_*_classifier*.py`.