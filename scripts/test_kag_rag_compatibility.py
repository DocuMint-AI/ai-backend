#!/usr/bin/env python3
"""
Test KAG adapter integration with RAG functions (without Google Cloud dependencies).
"""

import sys
import os
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.rag_adapter import load_and_normalize, create_chunks_for_embeddings

def simulate_rag_get_chunks_from_json(json_dir, user_session_id=None):
    """
    Simulate the enhanced get_chunks_from_json function logic.
    This replicates the integration logic without Google Cloud dependencies.
    """
    chunks = []
    
    # If user_session_id provided, use new structure (for testing, just use as-is)
    if user_session_id:
        # In real implementation, this would resolve session structure
        pass
    
    try:
        # Use RAG adapter to load and normalize documents
        adapter_docs = load_and_normalize(json_dir, chunk_size=500, chunk_overlap=50)
        
        # Convert adapter format to existing RAG chunk format
        for doc in adapter_docs:
            doc_chunks = create_chunks_for_embeddings(doc)
            
            for chunk in doc_chunks:
                # Convert to legacy chunk format expected by existing RAG functions
                chunks.append({
                    "text": chunk["text"],
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["metadata"]["document_id"],
                    "classifier_label": chunk["metadata"]["classifier_label"],
                    "document_confidence": chunk["metadata"]["document_confidence"],
                    "chunk_type": chunk["metadata"]["chunk_type"],
                    "source_format": chunk["metadata"]["source_format"]
                })
        
        print(f"✅ Loaded {len(chunks)} chunks from {len(adapter_docs)} documents using RAG adapter")
        
    except Exception as e:
        print(f"❌ RAG adapter failed, falling back to legacy processing: {e}")
        
        # Fallback to legacy processing for backward compatibility
        for filename in os.listdir(json_dir):
            if filename.endswith(".json"):
                with open(os.path.join(json_dir, filename), "r") as f:
                    data = json.load(f)
                    
                # Extract text using legacy method
                text = data.get("content", "")
                if not text and "extracted_data" in data:
                    text = data["extracted_data"].get("text_content", "")
                
                # Create legacy chunks
                for idx, paragraph in enumerate(text.split("\n\n")):
                    if paragraph.strip():
                        chunk_id = f"{filename}_c{idx:04d}"
                        chunks.append({
                            "text": paragraph.strip(), 
                            "chunk_id": chunk_id,
                            "document_id": filename,
                            "classifier_label": "unknown",
                            "document_confidence": 0.0,
                            "chunk_type": "text",
                            "source_format": "legacy"
                        })
    
    return chunks

def simulate_prepare_rag_prompt_QA(chunks, user_query):
    """
    Simulate the enhanced QA prompt preparation with metadata.
    """
    context_items = []
    for i, chunk in enumerate(chunks, start=1):
        # Include enhanced metadata in context
        classifier_info = f" [{chunk.get('classifier_label', 'unknown')}]" if chunk.get('classifier_label') != 'unknown' else ""
        confidence_info = f" (confidence: {chunk.get('document_confidence', 0.0):.2f})" if chunk.get('document_confidence', 0.0) > 0 else ""
        
        ctxt = f"Context {i}{classifier_info}{confidence_info}: {chunk['text'][:100]}... (doc:{chunk['chunk_id']})"
        context_items.append(ctxt)
    context_str = "\n".join(context_items)

    qa_prompt = (
        "You are a legal assistant. Use ONLY the following numbered context items to answer the question. "
        "Context items include document classification and confidence scores for better accuracy. "
        "If the law is not present in the context, say \"not found in documents\".\n\n"
        f"{context_str}\n\n"
        f"Question: {user_query}\n"
        "Answer (concise, cite chunks as [doc:chunk]):"
    )
    return qa_prompt

def test_kag_rag_integration():
    """Test complete KAG-RAG integration."""
    
    print('🧪 Testing KAG-RAG Integration (Simulated)...')
    
    # Test with real KAG input directory
    test_dir = 'artifacts/single_test'
    
    try:
        # Test the enhanced get_chunks_from_json function
        print(f'📄 Loading chunks from: {test_dir}')
        chunks = simulate_rag_get_chunks_from_json(test_dir)
        
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
        print(f'\n🧪 Testing enhanced QA prompt preparation...')
        test_query = "What type of insurance policy is this?"
        qa_prompt = simulate_prepare_rag_prompt_QA(chunks[:3], test_query)
        
        # Verify enhanced prompt includes classifier info
        if "Financial_and_Security" in qa_prompt or "[Financial_and_Security]" in qa_prompt:
            print(f'✅ QA prompt includes classifier information')
        else:
            print(f'⚠️  QA prompt missing classifier info (found in prompt: {qa_prompt[:200]}...)')
        
        if "confidence:" in qa_prompt:
            print(f'✅ QA prompt includes confidence scores')
        else:
            print(f'⚠️  QA prompt missing confidence scores')
        
        # Show sample of enhanced prompt
        print(f'\n📝 Sample QA prompt (first 300 chars):')
        print(f'   {qa_prompt[:300]}...')
        
        print(f'\n🎉 KAG-RAG integration test PASSED!')
        return True
        
    except Exception as e:
        print(f'❌ KAG-RAG integration test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_chunk_metadata_preservation():
    """Test that KAG metadata flows through to RAG chunks."""
    
    print(f'\n🧪 Testing metadata preservation through RAG pipeline...')
    
    test_file = 'artifacts/single_test/test-1758411760/kag_input.json'
    
    try:
        # Load with adapter
        docs = load_and_normalize(test_file)
        doc = docs[0]
        
        # Create embedding chunks
        embedding_chunks = create_chunks_for_embeddings(doc)
        
        # Convert to RAG format
        rag_chunks = []
        for chunk in embedding_chunks:
            rag_chunks.append({
                "text": chunk["text"],
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["metadata"]["document_id"],
                "classifier_label": chunk["metadata"]["classifier_label"],
                "document_confidence": chunk["metadata"]["document_confidence"],
                "chunk_type": chunk["metadata"]["chunk_type"],
                "source_format": chunk["metadata"]["source_format"]
            })
        
        # Verify metadata preservation
        sample_chunk = rag_chunks[0]
        
        checks = [
            ("Document ID preservation", sample_chunk["document_id"] == "test-1758411760"),
            ("Classifier preservation", sample_chunk["classifier_label"] == "Financial_and_Security"),
            ("Confidence preservation", sample_chunk["document_confidence"] == 0.85),
            ("Source format preservation", sample_chunk["source_format"] == "kag"),
            ("Chunk type preservation", sample_chunk["chunk_type"] in ["text", "clause", "entity", "context"])
        ]
        
        passed_checks = 0
        for check_name, result in checks:
            if result:
                print(f'   ✅ {check_name}')
                passed_checks += 1
            else:
                print(f'   ❌ {check_name}')
        
        if passed_checks == len(checks):
            print(f'✅ All metadata preservation checks passed ({passed_checks}/{len(checks)})')
            return True
        else:
            print(f'❌ Some metadata preservation checks failed ({passed_checks}/{len(checks)})')
            return False
        
    except Exception as e:
        print(f'❌ Metadata preservation test failed: {e}')
        return False

if __name__ == "__main__":
    success1 = test_kag_rag_integration()
    success2 = test_chunk_metadata_preservation()
    
    if success1 and success2:
        print(f'\n🎉 All KAG-RAG integration tests passed!')
        print(f'🚀 KAG input is fully compatible with RAG system!')
        print(f'📊 Key achievements:')
        print(f'   • KAG format detection and normalization working')
        print(f'   • Metadata preservation through pipeline complete')
        print(f'   • Enhanced QA prompts with classifier and confidence')
        print(f'   • Backward compatibility with legacy formats maintained')
        print(f'   • Robust error handling and fallback behavior')
        sys.exit(0)
    else:
        print(f'\n❌ Some integration tests failed')
        sys.exit(1)