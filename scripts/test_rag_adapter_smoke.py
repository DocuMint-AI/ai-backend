#!/usr/bin/env python3
"""
Comprehensive smoke tests for RAG adapter integration.

Tests the complete integration between KAG input format and the RAG system,
verifying that KAG documents can be properly loaded, normalized, chunked,
and processed by the existing RAG infrastructure.

Usage:
    python scripts/test_rag_adapter_smoke.py
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.rag_adapter import load_and_normalize, create_chunks_for_embeddings
import importlib.util

# Import the RAG module with special characters in filename
spec = importlib.util.spec_from_file_location(
    "rag_qa_insights", 
    project_root / "routers" / "rag_(qa_&_insights).py"
)
rag_qa_insights = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag_qa_insights)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_kag_input():
    """Create a test KAG input file for validation."""
    kag_data = {
        "parsed_document": {
            "full_text": "This is a legal contract for employment services. The contractor agrees to provide professional services for a period of 12 months. Termination notice period is 30 days for either party. Payment terms are Net 30 days from invoice date.",
            "clauses": [
                {
                    "clause_type": "termination",
                    "content": "Termination notice period is 30 days for either party.",
                    "confidence": 0.92
                },
                {
                    "clause_type": "payment",
                    "content": "Payment terms are Net 30 days from invoice date.",
                    "confidence": 0.87
                }
            ],
            "entities": [
                {"type": "duration", "value": "12 months", "confidence": 0.95},
                {"type": "notice_period", "value": "30 days", "confidence": 0.90},
                {"type": "payment_terms", "value": "Net 30 days", "confidence": 0.88}
            ]
        },
        "classifier_verdict": {
            "label": "Employment_Contract",
            "confidence": 0.89,
            "subcategory": "Service_Agreement"
        },
        "metadata": {
            "document_id": "test_contract_001.pdf",
            "processing_timestamp": "2024-01-15T10:30:00Z",
            "vision_confidence": 0.83,
            "source": "vision_api"
        }
    }
    return kag_data


def create_test_legacy_input():
    """Create a test legacy format file for compatibility validation."""
    legacy_data = {
        "content": "This is a legacy format document. It contains important legal clauses about termination and payment. The notice period for termination is specified as 60 days.",
        "extracted_data": {
            "text_content": "Additional text content from legacy extraction. Payment must be made within 15 days of invoice.",
            "metadata": {
                "source": "legacy_extractor"
            }
        }
    }
    return legacy_data


def test_kag_format_detection():
    """Test 1: Verify KAG format detection works correctly."""
    logger.info("🧪 Test 1: KAG Format Detection")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create KAG format file
        kag_file = Path(temp_dir) / "kag_input.json"
        with open(kag_file, 'w') as f:
            json.dump(create_test_kag_input(), f, indent=2)
        
        # Test KAG format loading
        try:
            docs = load_and_normalize(temp_dir, chunk_size=200, chunk_overlap=20)
            
            assert len(docs) == 1, f"Expected 1 document, got {len(docs)}"
            assert docs[0]["format"] == "kag", f"Expected KAG format, got {docs[0]['format']}"
            assert "full_text" in docs[0], "Missing full_text in normalized KAG document"
            assert "classifier_verdict" in docs[0], "Missing classifier_verdict in normalized KAG document"
            
            logger.info("✅ KAG format detection: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ KAG format detection: FAILED - {e}")
            return False


def test_legacy_format_compatibility():
    """Test 2: Verify legacy format compatibility."""
    logger.info("🧪 Test 2: Legacy Format Compatibility")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create legacy format file
        legacy_file = Path(temp_dir) / "legacy_input.json"
        with open(legacy_file, 'w') as f:
            json.dump(create_test_legacy_input(), f, indent=2)
        
        # Test legacy format loading
        try:
            docs = load_and_normalize(temp_dir, chunk_size=200, chunk_overlap=20)
            
            assert len(docs) == 1, f"Expected 1 document, got {len(docs)}"
            assert docs[0]["format"] == "legacy", f"Expected legacy format, got {docs[0]['format']}"
            assert "full_text" in docs[0], "Missing full_text in normalized legacy document"
            
            logger.info("✅ Legacy format compatibility: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Legacy format compatibility: FAILED - {e}")
            return False


def test_chunking_functionality():
    """Test 3: Verify chunking produces correct output."""
    logger.info("🧪 Test 3: Chunking Functionality")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create KAG format file
        kag_file = Path(temp_dir) / "kag_input.json"
        with open(kag_file, 'w') as f:
            json.dump(create_test_kag_input(), f, indent=2)
        
        try:
            docs = load_and_normalize(temp_dir, chunk_size=100, chunk_overlap=10)
            doc = docs[0]
            
            chunks = create_chunks_for_embeddings(doc)
            
            assert len(chunks) > 0, "No chunks generated"
            
            # Verify chunk structure
            for chunk in chunks:
                assert "text" in chunk, "Missing text in chunk"
                assert "chunk_id" in chunk, "Missing chunk_id in chunk"
                assert "metadata" in chunk, "Missing metadata in chunk"
                assert "classifier_label" in chunk["metadata"], "Missing classifier_label in chunk metadata"
                assert "document_confidence" in chunk["metadata"], "Missing document_confidence in chunk metadata"
            
            logger.info(f"✅ Chunking functionality: PASSED - Generated {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Chunking functionality: FAILED - {e}")
            return False


def test_rag_integration():
    """Test 4: Verify RAG system integration."""
    logger.info("🧪 Test 4: RAG System Integration")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create both KAG and legacy files
        kag_file = Path(temp_dir) / "kag_input.json"
        with open(kag_file, 'w') as f:
            json.dump(create_test_kag_input(), f, indent=2)
        
        legacy_file = Path(temp_dir) / "legacy_input.json"
        with open(legacy_file, 'w') as f:
            json.dump(create_test_legacy_input(), f, indent=2)
        
        try:
            # Test RAG integration
            chunks = rag_qa_insights.get_chunks_from_json(temp_dir)
            
            assert len(chunks) > 0, "No chunks returned from RAG integration"
            
            # Verify chunk format expected by RAG system
            for chunk in chunks:
                assert "text" in chunk, "Missing text in RAG chunk"
                assert "chunk_id" in chunk, "Missing chunk_id in RAG chunk"
                assert "document_id" in chunk, "Missing document_id in RAG chunk"
                assert "classifier_label" in chunk, "Missing classifier_label in RAG chunk"
                assert "source_format" in chunk, "Missing source_format in RAG chunk"
            
            # Test QA prompt preparation
            qa_prompt = rag_qa_insights.prepare_rag_prompt_QA(chunks[:3], "What is the termination notice period?")
            assert "Context 1" in qa_prompt, "QA prompt missing context numbering"
            assert "Employment_Contract" in qa_prompt or "legacy" in qa_prompt, "QA prompt missing classifier info"
            
            # Test risk insights prompt preparation
            risk_prompt = rag_qa_insights.prepare_rag_prompt_risk_insights(chunks[:3])
            assert "legal risk evaluator" in risk_prompt, "Risk prompt missing evaluator instructions"
            assert "confidence" in risk_prompt.lower(), "Risk prompt missing confidence information"
            
            logger.info(f"✅ RAG system integration: PASSED - Processed {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ RAG system integration: FAILED - {e}")
            return False


def test_metadata_preservation():
    """Test 5: Verify metadata preservation through pipeline."""
    logger.info("🧪 Test 5: Metadata Preservation")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create KAG format file with rich metadata
        kag_data = create_test_kag_input()
        kag_file = Path(temp_dir) / "kag_input.json"
        with open(kag_file, 'w') as f:
            json.dump(kag_data, f, indent=2)
        
        try:
            # Load through adapter
            docs = load_and_normalize(temp_dir)
            doc = docs[0]
            
            # Verify metadata preservation
            assert doc["classifier_verdict"]["label"] == "Employment_Contract", "Classifier label not preserved"
            assert doc["classifier_verdict"]["confidence"] == 0.89, "Classifier confidence not preserved"
            assert doc["metadata"]["vision_confidence"] == 0.83, "Vision confidence not preserved"
            
            # Verify metadata flows to chunks
            chunks = create_chunks_for_embeddings(doc)
            chunk = chunks[0]
            
            assert chunk["metadata"]["classifier_label"] == "Employment_Contract", "Classifier label not in chunk metadata"
            assert chunk["metadata"]["document_confidence"] == 0.89, "Document confidence not in chunk metadata"
            assert chunk["metadata"]["source_format"] == "kag", "Source format not in chunk metadata"
            
            logger.info("✅ Metadata preservation: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Metadata preservation: FAILED - {e}")
            return False


def test_error_handling():
    """Test 6: Verify error handling and fallback behavior."""
    logger.info("🧪 Test 6: Error Handling")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create invalid JSON file
        invalid_file = Path(temp_dir) / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json content")
        
        try:
            # Test graceful error handling
            chunks = rag_qa_insights.get_chunks_from_json(temp_dir)
            
            # Should handle errors gracefully and return empty list or fallback
            assert isinstance(chunks, list), "Error handling should return list"
            
            logger.info("✅ Error handling: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling: FAILED - {e}")
            return False


def main():
    """Run all RAG adapter smoke tests."""
    print("🚀 Starting RAG Adapter Smoke Tests")
    print("=" * 50)
    
    tests = [
        test_kag_format_detection,
        test_legacy_format_compatibility,
        test_chunking_functionality,
        test_rag_integration,
        test_metadata_preservation,
        test_error_handling
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
            logger.error(f"Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 RAG Adapter Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed}/{passed+failed} ({100*passed/(passed+failed):.1f}%)")
    
    if failed == 0:
        print("🎉 All RAG adapter tests passed! KAG integration ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Review integration before production deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())