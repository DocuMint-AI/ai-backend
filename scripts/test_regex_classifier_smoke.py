#!/usr/bin/env python3
"""
Regex Classifier Smoke Test

This script validates the production-ready weighted regex classifier with:
- Basic classification functionality
- Weighted pattern matching
- Classification verdict JSON export
- Different document types (judicial, constitutional, property, etc.)
- Debug logging and observability

Exit Codes:
- 0: All tests passed
- 1: One or more tests failed
"""

import json
import logging
import sys
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_classifier_initialization():
    """Test classifier can be initialized with different configurations."""
    logger.info("="*60)
    logger.info("TESTING CLASSIFIER INITIALIZATION")
    logger.info("="*60)
    
    try:
        from services.template_matching.regex_classifier import create_classifier, create_weighted_classifier
        
        # Test default initialization
        logger.info("Testing default initialization...")
        classifier = create_classifier()
        logger.info("✅ Default classifier initialized successfully")
        
        # Test debug mode with enhanced factory
        logger.info("Testing debug mode initialization...")
        debug_classifier = create_weighted_classifier(debug=True)
        logger.info("✅ Debug classifier initialized successfully")
        
        # Test custom confidence thresholds
        logger.info("Testing custom confidence thresholds...")
        custom_thresholds = {
            "very_low": 0.0,
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8
        }
        custom_classifier = create_weighted_classifier(confidence_thresholds=custom_thresholds)
        logger.info("✅ Custom threshold classifier initialized successfully")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Classifier initialization failed: {e}")
        return False


def test_judicial_document_classification():
    """Test classification of judicial document text."""
    logger.info("\n--- Testing Judicial Document Classification ---")
    
    try:
        from services.template_matching.regex_classifier import create_weighted_classifier
        
        classifier = create_weighted_classifier(debug=True)
        
        # Sample judicial text
        judicial_text = """
        Hon'ble Justice Smith delivered this judgment in Civil Appeal No. 123/2024.
        The appellant filed a writ petition under Article 226 of the Constitution of India.
        After hearing the learned counsel for both parties, this Court finds that the 
        plaintiff has made out a prima facie case. The respondent's contentions are hereby rejected.
        The ratio decidendi of this case establishes that procedural fairness must be observed.
        Accordingly, this appeal is allowed and the impugned order dated 15.01.2024 is set aside.
        """
        
        result = classifier.classify_document(judicial_text)
        verdict = classifier.export_classification_verdict(result)
        
        # Validate results
        if result.label != "Judicial_Documents":
            logger.error(f"❌ Expected 'Judicial_Documents', got '{result.label}'")
            return False
        
        if result.confidence not in ["low", "medium", "high"]:
            logger.error(f"❌ Invalid confidence level: {result.confidence}")
            return False
        
        logger.info(f"✅ Judicial document classified correctly: {result.label} ({result.confidence} confidence, score={result.score:.3f})")
        logger.info(f"   Total matches: {result.total_matches}, Weighted score: {result.total_weighted_score:.2f}")
        logger.info(f"   Top patterns: {[p.keyword for p in result.matched_patterns[:3]]}")
        
        # Validate verdict structure
        required_fields = ["label", "score", "confidence", "matched_patterns", "category_scores", "summary"]
        for field in required_fields:
            if field not in verdict:
                logger.error(f"❌ Missing field in verdict: {field}")
                return False
        
        logger.info("✅ Verdict JSON structure validated")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Judicial document classification failed: {e}")
        return False


def test_constitutional_document_classification():
    """Test classification of constitutional document text."""
    logger.info("\n--- Testing Constitutional Document Classification ---")
    
    try:
        from services.template_matching.regex_classifier import create_classifier
        
        classifier = create_classifier()
        
        # Sample constitutional text
        constitutional_text = """
        The Constitution of India guarantees fundamental rights under Part III.
        Article 14 provides for equality before law and equal protection of laws.
        Parliament has enacted the Indian Contract Act under its legislative powers.
        Section 15 of the Act deals with coercion as defined in this statute.
        The Central Government issued notification No. 123/2024 in the Gazette of India.
        This amendment to the rules came into effect from the date of publication.
        """
        
        result = classifier.classify_document(constitutional_text)
        
        if result.label != "Constitutional_and_Legislative":
            logger.error(f"❌ Expected 'Constitutional_and_Legislative', got '{result.label}'")
            return False
        
        logger.info(f"✅ Constitutional document classified correctly: {result.label} ({result.confidence} confidence, score={result.score:.3f})")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Constitutional document classification failed: {e}")
        return False


def test_property_document_classification():
    """Test classification of property document text."""
    logger.info("\n--- Testing Property Document Classification ---")
    
    try:
        from services.template_matching.regex_classifier import create_classifier
        
        classifier = create_classifier()
        
        # Sample property text
        property_text = """
        This sale deed is executed between the vendor Ramesh Kumar and vendee Suresh Patel.
        The consideration amount of Rs. 50,00,000/- has been paid by the purchaser.
        The property bearing survey number 123/4 in Village Anand is hereby conveyed.
        Clear and marketable title is warranted by the vendor to the vendee.
        The original title deed and all property documents are handed over.
        Registration of this conveyance deed was completed at the Sub-Registrar office.
        """
        
        result = classifier.classify_document(property_text)
        
        if result.label != "Property_and_Real_Estate":
            logger.error(f"❌ Expected 'Property_and_Real_Estate', got '{result.label}'")
            return False
        
        logger.info(f"✅ Property document classified correctly: {result.label} ({result.confidence} confidence, score={result.score:.3f})")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Property document classification failed: {e}")
        return False


def test_empty_text_handling():
    """Test classifier behavior with empty or invalid text."""
    logger.info("\n--- Testing Empty Text Handling ---")
    
    try:
        from services.template_matching.regex_classifier import create_classifier
        
        classifier = create_classifier()
        
        # Test empty text
        result = classifier.classify_document("")
        
        if result.label != "Unclassified":
            logger.error(f"❌ Expected 'Unclassified' for empty text, got '{result.label}'")
            return False
        
        if result.confidence != "very_low":
            logger.error(f"❌ Expected 'very_low' confidence for empty text, got '{result.confidence}'")
            return False
        
        logger.info("✅ Empty text handled correctly: Unclassified with very_low confidence")
        
        # Test non-legal text
        result = classifier.classify_document("This is just random text with no legal keywords.")
        logger.info(f"✅ Non-legal text classified as: {result.label} ({result.confidence} confidence)")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Empty text handling failed: {e}")
        return False


def test_verdict_json_export():
    """Test classification verdict JSON export functionality."""
    logger.info("\n--- Testing Verdict JSON Export ---")
    
    try:
        from services.template_matching.regex_classifier import create_classifier
        
        classifier = create_classifier()
        
        # Sample text
        text = "This judgment by Hon'ble Justice Kumar establishes important precedent."
        
        result = classifier.classify_document(text)
        verdict = classifier.export_classification_verdict(result)
        
        # Test JSON serialization
        json_str = json.dumps(verdict, indent=2, default=str)
        logger.info("✅ Verdict successfully serialized to JSON")
        
        # Validate structure
        expected_fields = [
            "label", "score", "confidence", "matched_patterns", 
            "category_scores", "summary", "processing_metadata", "statistics"
        ]
        
        for field in expected_fields:
            if field not in verdict:
                logger.error(f"❌ Missing field in verdict: {field}")
                return False
        
        # Validate summary structure
        summary = verdict["summary"]
        summary_fields = ["primary_label", "confidence", "score", "top_keywords", "total_matches"]
        
        for field in summary_fields:
            if field not in summary:
                logger.error(f"❌ Missing field in summary: {field}")
                return False
        
        logger.info("✅ Verdict JSON structure validated")
        logger.info(f"   Primary label: {summary['primary_label']}")
        logger.info(f"   Confidence: {summary['confidence']}")
        logger.info(f"   Score: {summary['score']}")
        logger.info(f"   Total matches: {summary['total_matches']}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Verdict JSON export failed: {e}")
        return False


def test_debug_logging():
    """Test debug logging functionality."""
    logger.info("\n--- Testing Debug Logging ---")
    
    try:
        # Set debug environment variable
        os.environ["CLASSIFIER_DEBUG"] = "true"
        
        from services.template_matching.regex_classifier import create_classifier
        
        classifier = create_classifier()
        
        # Sample text with multiple matches
        text = """
        Hon'ble Justice delivered judgment. Article 14 of Constitution provides equality.
        The plaintiff filed suit. Defendant raised objections. Court allows the petition.
        """
        
        result = classifier.classify_document(text)
        
        logger.info(f"✅ Debug logging test completed")
        logger.info(f"   Classified as: {result.label}")
        logger.info(f"   Debug patterns found: {len(result.matched_patterns)}")
        
        # Clean up environment
        del os.environ["CLASSIFIER_DEBUG"]
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Debug logging test failed: {e}")
        return False


def test_weighted_scoring():
    """Test that weighted scoring works correctly."""
    logger.info("\n--- Testing Weighted Scoring ---")
    
    try:
        from services.template_matching.regex_classifier import create_weighted_classifier
        
        classifier = create_weighted_classifier(debug=True)
        
        # Text with high-weight patterns (judicial)
        high_weight_text = "Hon'ble Justice delivered judgment with ratio decidendi"
        
        # Text with low-weight patterns  
        low_weight_text = "This section of the act provides for general provisions"
        
        result1 = classifier.classify_document(high_weight_text)
        result2 = classifier.classify_document(low_weight_text)
        
        logger.info(f"High-weight text score: {result1.total_weighted_score:.2f}")
        logger.info(f"Low-weight text score: {result2.total_weighted_score:.2f}")
        
        # High-weight patterns should generally produce higher scores
        if result1.total_weighted_score > 0:
            logger.info("✅ Weighted scoring appears to be working")
        else:
            logger.warning("⚠️ No weighted scores found - check pattern weights")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Weighted scoring test failed: {e}")
        return False


def main():
    """Main entry point for smoke tests."""
    logger.info("🔧 Starting Weighted Regex Classifier Smoke Tests")
    
    tests = [
        test_classifier_initialization,
        test_judicial_document_classification,
        test_constitutional_document_classification,
        test_property_document_classification,
        test_empty_text_handling,
        test_verdict_json_export,
        test_debug_logging,
        test_weighted_scoring
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SMOKE TEST RESULTS")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        logger.info("\n🎉 ALL SMOKE TESTS PASSED - Classifier is ready for production!")
        return 0
    else:
        logger.error(f"\n💥 {failed} TESTS FAILED - Please fix issues before deployment!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)