#!/usr/bin/env python3
"""
Test complete RAG system integration with KAG adapter.
"""

import sys
from pathlib import Path
import importlib.util

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the RAG module with special characters in filename
spec = importlib.util.spec_from_file_location(
    "rag_qa_insights", 
    project_root / "routers" / "rag_(qa_&_insights).py"
)
rag_qa_insights = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag_qa_insights)

from services.rag_adapter import load_and_normalize

def test_rag_system_integration():
    """Test complete RAG system with KAG adapter integration."""
    
    print('🧪 Testing Complete RAG System Integration...')
    
    # Test with real KAG input directory
    test_dir = 'artifacts/single_test'
    
    try:
        # Test the enhanced get_chunks_from_json function
        print(f'📄 Loading chunks from: {test_dir}')
        chunks = rag_qa_insights.get_chunks_from_json(test_dir)
        
        if not chunks:
            print('❌ No chunks returned from RAG system')
            return False
        
        print(f'✅ RAG system loaded {len(chunks)} chunks')
        
        # Verify chunk format
        sample_chunk = chunks[0]
        required_fields = ['text', 'chunk_id', 'document_id', 'classifier_label', 'source_format']
        missing_fields = [field for field in required_fields if field not in sample_chunk]
        
        if missing_fields:
            print(f'❌ Missing required fields in chunk: {missing_fields}')
            return False
        
        print(f'✅ Chunk format validation passed')
        print(f'   Sample chunk ID: {sample_chunk["chunk_id"]}')
        print(f'   Document ID: {sample_chunk["document_id"]}')
        print(f'   Classifier: {sample_chunk["classifier_label"]}')
        print(f'   Confidence: {sample_chunk.get("document_confidence", "N/A")}')
        print(f'   Source format: {sample_chunk["source_format"]}')
        
        # Test QA prompt preparation
        print(f'\n🧪 Testing QA prompt preparation...')
        test_query = "What type of insurance policy is this?"
        qa_prompt = rag_qa_insights.prepare_rag_prompt_QA(chunks[:3], test_query)
        
        # Verify enhanced prompt includes classifier info
        if "Financial_and_Security" in qa_prompt:
            print(f'✅ QA prompt includes classifier information')
        else:
            print(f'⚠️  QA prompt may be missing classifier information')
        
        if "confidence:" in qa_prompt:
            print(f'✅ QA prompt includes confidence scores')
        else:
            print(f'⚠️  QA prompt may be missing confidence scores')
        
        # Test risk insights prompt preparation
        print(f'\n🧪 Testing risk insights prompt preparation...')
        risk_prompt = rag_qa_insights.prepare_rag_prompt_risk_insights(chunks[:3])
        
        if "Financial_and_Security" in risk_prompt:
            print(f'✅ Risk prompt includes classifier information')
        else:
            print(f'⚠️  Risk prompt may be missing classifier information')
        
        if "Confidence:" in risk_prompt:
            print(f'✅ Risk prompt includes confidence scores')
        else:
            print(f'⚠️  Risk prompt may be missing confidence scores')
        
        print(f'\n🎉 Complete RAG system integration test PASSED!')
        return True
        
    except Exception as e:
        print(f'❌ RAG integration test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_fallback_behavior():
    """Test RAG system fallback to legacy processing."""
    
    print(f'\n🧪 Testing RAG system fallback behavior...')
    
    # Test with non-existent directory to trigger fallback
    try:
        chunks = rag_qa_insights.get_chunks_from_json('nonexistent_directory')
        print(f'✅ Fallback handled gracefully, returned {len(chunks)} chunks')
        return True
        
    except Exception as e:
        print(f'❌ Fallback test failed: {e}')
        return False

if __name__ == "__main__":
    success1 = test_rag_system_integration()
    success2 = test_fallback_behavior()
    
    if success1 and success2:
        print(f'\n🎉 All RAG system integration tests passed!')
        print(f'🚀 KAG input is fully compatible with RAG system!')
        sys.exit(0)
    else:
        print(f'\n❌ Some integration tests failed')
        sys.exit(1)