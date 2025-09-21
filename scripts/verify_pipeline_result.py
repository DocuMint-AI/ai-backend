#!/usr/bin/env python3
"""
Verify the pipeline result includes RAG integration data.
"""

import json
from pathlib import Path

def verify_pipeline_result():
    """Verify the pipeline result includes KAG-RAG integration data."""
    
    result_file = Path("artifacts/single_test/077-NLR-NLR-V-72-T.-P.-VEERAPPEN-Appellant-and-THE-ATTORNEY-GENERAL-Respondent_pipeline_result.json")
    
    if not result_file.exists():
        print(f"❌ Pipeline result file not found: {result_file}")
        return False
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        print('📊 Pipeline Result Verification:')
        print(f'✅ Success: {result.get("success", False)}')
        print(f'📄 Document: {result.get("pipeline_id", "N/A")}')
        print(f'🏷️  Classification: {result.get("classification", {}).get("label", "N/A")}')
        
        rag_integration = result.get("rag_integration", {})
        if rag_integration and "error" not in rag_integration:
            print(f'🔗 RAG Integration Results:')
            print(f'   adapter_loaded_docs: {rag_integration.get("adapter_loaded_docs", 0)}')
            print(f'   embedding_chunks_created: {rag_integration.get("embedding_chunks_created", 0)}')
            print(f'   rag_chunks_converted: {rag_integration.get("rag_chunks_converted", 0)}')
            print(f'   enhanced_qa_validated: {rag_integration.get("enhanced_qa_validated", False)}')
            
            sample_context = rag_integration.get("sample_qa_context", "")
            if sample_context:
                print(f'📝 Sample QA Context:')
                print(f'   {sample_context[:150]}...')
            
            print(f'\n🎉 KAG-RAG integration successfully validated in pipeline result!')
            return True
        else:
            print(f'❌ RAG integration failed or missing in pipeline result')
            if "error" in rag_integration:
                print(f'   Error: {rag_integration["error"]}')
            return False
            
    except Exception as e:
        print(f'❌ Error reading pipeline result: {e}')
        return False

if __name__ == "__main__":
    if verify_pipeline_result():
        print('\n🏆 Pipeline result verification successful!')
    else:
        print('\n❌ Pipeline result verification failed!')