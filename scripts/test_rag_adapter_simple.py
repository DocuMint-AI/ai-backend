#!/usr/bin/env python3
"""
Simple test for RAG adapter functionality.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.rag_adapter import load_and_normalize, create_chunks_for_embeddings

def create_test_kag_input():
    """Create a test KAG input file for validation."""
    kag_data = {
        "document_id": "test_contract_001.pdf",
        "parsed_document": {
            "full_text": "This is a legal contract for employment services. The contractor agrees to provide professional services for a period of 12 months. Termination notice period is 30 days for either party. Payment terms are Net 30 days from invoice date.",
            "clauses": [
                {
                    "text": "Termination notice period is 30 days for either party.",
                    "type": "termination",
                    "confidence": 0.92
                },
                {
                    "text": "Payment terms are Net 30 days from invoice date.",
                    "type": "payment", 
                    "confidence": 0.87
                }
            ]
        },
        "classifier_verdict": {
            "label": "Employment_Contract",
            "confidence": 0.89,
            "score": 0.92
        },
        "metadata": {
            "processing_timestamp": "2024-01-15T10:30:00Z",
            "vision_confidence": 0.83
        }
    }
    return kag_data

def main():
    print("🧪 Testing RAG Adapter...")
    
    # Create test KAG input
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create KAG format file
        kag_file = Path(temp_dir) / "kag_input.json"
        with open(kag_file, 'w') as f:
            json.dump(create_test_kag_input(), f, indent=2)
        
        print(f"✅ KAG Input generated -> {kag_file}")
        
        # Test KAG format loading
        try:
            docs = load_and_normalize(str(kag_file), chunk_size=200, chunk_overlap=20)
            print(f"✅ Loaded {len(docs)} documents")
            
            if docs:
                doc = docs[0]
                print(f"✅ Document ID: {doc['document_id']}")
                print(f"✅ Classifier: {doc['classifier']['label']} (confidence: {doc['document_confidence']:.3f})")
                print(f"✅ Chunks: {len(doc['chunks'])}")
                
                # Test chunk creation for embeddings
                chunks = create_chunks_for_embeddings(doc)
                print(f"✅ Embedding chunks: {len(chunks)}")
                
                # Show first chunk
                if chunks:
                    first_chunk = chunks[0]
                    print(f"✅ First chunk: {first_chunk['chunk_id']}")
                    print(f"   Text: {first_chunk['text'][:100]}...")
                    print(f"   Metadata: {first_chunk['metadata']}")
                
                print("🎉 RAG Adapter test PASSED!")
                return 0
            else:
                print("❌ No documents loaded")
                return 1
                
        except Exception as e:
            print(f"❌ RAG Adapter test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(main())