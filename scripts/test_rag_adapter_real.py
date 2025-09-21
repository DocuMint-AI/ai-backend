#!/usr/bin/env python3
"""
Test RAG adapter with real KAG input files.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.rag_adapter import load_and_normalize, get_chunks_summary, create_chunks_for_embeddings

def test_real_kag_input():
    """Test RAG adapter with real KAG input file."""
    
    # Test with real KAG output
    test_file = 'artifacts/single_test/test-1758411760/kag_input.json'
    
    print('🧪 Testing RAG Adapter with real KAG input...')
    print(f'📄 Loading: {test_file}')
    
    try:
        docs = load_and_normalize(test_file)
        print(f'✅ Loaded {len(docs)} documents')
        
        if docs:
            doc = docs[0]
            print(f'📋 Document ID: {doc["document_id"]}')
            print(f'🏷️  Classifier: {doc["classifier"]["label"]} (confidence: {doc["document_confidence"]:.3f})')
            print(f'📦 Total chunks: {len(doc["chunks"])}')
            
            # Show chunk types
            chunk_types = {}
            for chunk in doc["chunks"]:
                chunk_type = chunk["metadata"]["chunk_type"]
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            print(f'📊 Chunk types: {chunk_types}')
            
            # Test embedding format
            embedding_chunks = create_chunks_for_embeddings(doc)
            print(f'🎯 Embedding-ready chunks: {len(embedding_chunks)}')
            
            # Show sample chunks
            print('\n📝 Sample chunks:')
            for i, chunk in enumerate(embedding_chunks[:3]):
                print(f'  {i+1}. {chunk["chunk_id"]} ({chunk["metadata"]["chunk_type"]})')
                print(f'     Text: {chunk["text"][:80]}...')
                print(f'     Metadata: classifier={chunk["metadata"]["classifier_label"]}, confidence={chunk["metadata"]["document_confidence"]:.3f}')
            
            print('\n🎉 RAG Adapter successfully processed real KAG input!')
            return True
            
        else:
            print('❌ No documents loaded')
            return False
            
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_directory_loading():
    """Test loading multiple KAG files from directory."""
    
    test_dir = 'artifacts/single_test'
    
    print(f'\n🧪 Testing directory loading: {test_dir}')
    
    try:
        docs = load_and_normalize(test_dir)
        print(f'✅ Loaded {len(docs)} documents from directory')
        
        if docs:
            summary = get_chunks_summary(docs)
            print(f'📊 Summary:')
            print(f'   Total documents: {summary["total_documents"]}')
            print(f'   Total chunks: {summary["total_chunks"]}')
            print(f'   Avg chunks per doc: {summary["avg_chunks_per_doc"]:.1f}')
            print(f'   Chunk types: {summary["chunk_types"]}')
            print(f'   Classifiers: {summary["classifiers"]}')
            
            return True
        else:
            print('❌ No documents loaded from directory')
            return False
            
    except Exception as e:
        print(f'❌ Directory test failed: {e}')
        return False

if __name__ == "__main__":
    success1 = test_real_kag_input()
    success2 = test_directory_loading()
    
    if success1 and success2:
        print('\n🎉 All RAG adapter tests passed!')
        sys.exit(0)
    else:
        print('\n❌ Some tests failed')
        sys.exit(1)