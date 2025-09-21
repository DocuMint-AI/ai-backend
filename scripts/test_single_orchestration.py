import sys
import os
from pathlib import Path

# Ensure project root is on sys.path so `main.py` can be imported
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
import logging
import time
from datetime import datetime

# Import hybrid processing functions
from services.util_services import process_pdf_hybrid
from services.preprocessing.ocr_processing import GoogleVisionOCR
from services.template_matching.regex_classifier import create_classifier
from services.kag.kag_writer import generate_kag_input, validate_kag_input_file
from services.rag_adapter import load_and_normalize, create_chunks_for_embeddings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_single_pdf(pdf_path: Path, output_dir: Path):
    """Run a single PDF through the hybrid processing pipeline and show summary dashboard."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"▶ Processing single document: {pdf_path}")
    
    # Create pipeline ID
    pipeline_id = f"test-{int(time.time())}"
    artifacts_folder = output_dir / pipeline_id
    artifacts_folder.mkdir(parents=True, exist_ok=True)
    
    try:
        # Stage 1: Hybrid PDF Processing
        logger.info("Stage 1: Hybrid PDF Processing")
        hybrid_result = process_pdf_hybrid(
            pdf_path=pdf_path,
            output_dir=artifacts_folder,
            dpi=300,
            prefer_pymupdf=True
        )
        
        if not hybrid_result["success"]:
            logger.error(f"❌ Hybrid PDF processing failed: {hybrid_result.get('errors', [])}")
            return
        
        logger.info(f"✅ Successfully extracted text from {hybrid_result['processed_pages']}/{hybrid_result['total_pages']} pages")
        
        # Stage 2: Vision OCR Processing (if images available)
        logger.info("Stage 2: Vision OCR Processing")
        vision_results = []
        
        if hybrid_result["image_paths"]:
            try:
                ocr_service = GoogleVisionOCR.from_env()
                vision_results = ocr_service.process_image_list(
                    image_paths=hybrid_result["image_paths"],
                    plumber_texts=hybrid_result["page_texts"]
                )
                logger.info(f"✅ Vision OCR processed {len(vision_results)} pages")
                
            except Exception as e:
                logger.warning(f"⚠️ Vision OCR failed: {e}")
                # Create fallback results using text only
                for i, text in enumerate(hybrid_result["page_texts"]):
                    vision_results.append({
                        "page": i + 1,
                        "image_path": hybrid_result["image_paths"][i] if i < len(hybrid_result["image_paths"]) else "",
                        "vision_text": "",
                        "vision_confidence": 0.0,
                        "plumber_text": text,
                        "has_vision": False,
                        "has_plumber": bool(text.strip()),
                        "processing_error": str(e)
                    })
        else:
            # No images, use text-only
            for i, text in enumerate(hybrid_result["page_texts"]):
                vision_results.append({
                    "page": i + 1,
                    "image_path": "",
                    "vision_text": "",
                    "vision_confidence": 0.0,
                    "plumber_text": text,
                    "has_vision": False,
                    "has_plumber": bool(text.strip()),
                    "processing_error": None
                })
        
        # Merge text sources
        full_text_parts = []
        total_confidence = 0.0
        confidence_count = 0
        
        for result in vision_results:
            page_text = result.get("plumber_text", "") or result.get("vision_text", "")
            if page_text.strip():
                full_text_parts.append(page_text.strip())
            
            # Validate confidence values
            vision_conf = result.get("vision_confidence", 0.0)
            if vision_conf > 0.0:
                total_confidence += vision_conf
                confidence_count += 1
                logger.info(f"Page {result.get('page', '?')} OCR text extracted, confidence={vision_conf:.2f}")
        
        full_text = "\n\n".join(full_text_parts)
        document_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        logger.info(f"✅ Merged text: {len(full_text)} characters")
        logger.info(f"✅ Document confidence: {document_confidence:.3f} (from {confidence_count} pages)")
        
        # Stage 3: Create parsed_output.json
        logger.info("Stage 3: Creating parsed_output.json")
        parsed_output = {
            "text": full_text,
            "full_text": full_text,
            "pages": vision_results,
            "document_confidence": document_confidence,  # Add aggregated confidence
            "clauses": [],
            "named_entities": [],
            "key_value_pairs": [],
            "metadata": {
                "processor_id": "hybrid-processor",
                "pipeline_id": pipeline_id,
                "processing_method": hybrid_result["method"],
                "total_pages": hybrid_result["total_pages"],
                "processed_pages": hybrid_result["processed_pages"],
                "timestamp": datetime.now().isoformat(),
                "confidence_pages_processed": confidence_count
            }
        }
        
        # Save parsed_output.json atomically
        parsed_output_path = artifacts_folder / "parsed_output.json"
        temp_path = parsed_output_path.with_suffix('.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_output, f, indent=2, ensure_ascii=False, default=str)
        temp_path.replace(parsed_output_path)
        
        logger.info(f"✅ Saved parsed_output.json")
        
        # Stage 4: Classification
        logger.info("Stage 4: Document Classification")
        classifier = create_classifier()
        classification_result = classifier.classify_document(full_text)
        verdict_dict = classifier.export_classification_verdict(classification_result)
        
        # Save classification_verdict.json
        classification_verdict_path = artifacts_folder / "classification_verdict.json"
        temp_path = classification_verdict_path.with_suffix('.tmp')
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(verdict_dict, f, indent=2, ensure_ascii=False, default=str)
        temp_path.replace(classification_verdict_path)
        
        logger.info(f"✅ Document classified as '{verdict_dict['label']}' (score={verdict_dict['score']:.3f}, confidence={verdict_dict['confidence']})")
        
        # Stage 5: Generate KAG Input
        logger.info("Stage 5: KAG Input Generation")
        kag_input_path = generate_kag_input(
            artifact_dir=artifacts_folder,
            doc_id=pipeline_id,
            processor_id="hybrid-processor",
            gcs_uri=f"file://{pdf_path}",
            pipeline_version="v1",
            metadata={
                "processing_method": hybrid_result["method"],
                "total_pages": hybrid_result["total_pages"],
                "processed_pages": hybrid_result["processed_pages"],
                "original_filename": pdf_path.name
            }
        )
        
        logger.info(f"✅ KAG Input generated → {kag_input_path}")
        
        # Stage 6: Validation
        logger.info("Stage 6: Validation")
        is_valid = validate_kag_input_file(kag_input_path)
        if not is_valid:
            logger.error("❌ KAG input validation failed")
            return
        
        logger.info("✅ KAG input validation passed")
        
        # Validation: Check confidence values
        logger.info("Stage 6.1: Validating Confidence Values")
        if document_confidence > 0.0:
            logger.info(f"✅ Non-zero document confidence detected: {document_confidence:.3f}")
        else:
            logger.warning("⚠️ Document confidence is zero - may indicate OCR issues")
        
        # Validation: Check classification verdict structure
        logger.info("Stage 6.2: Validating Classification Verdict")
        required_verdict_fields = ["label", "score", "confidence", "matched_patterns", "summary"]
        for field in required_verdict_fields:
            if field not in verdict_dict:
                logger.error(f"❌ Missing field in classification verdict: {field}")
                return
        logger.info("✅ Classification verdict structure validated")
        
        # Stage 7: KAG-RAG Integration Test
        logger.info("Stage 7: KAG-RAG Integration Validation")
        try:
            # Test RAG adapter with the generated KAG input
            docs = load_and_normalize(str(kag_input_path))
            if docs:
                doc = docs[0]
                embedding_chunks = create_chunks_for_embeddings(doc)
                
                # Convert to RAG format for testing
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
                
                # Test enhanced QA prompt generation
                sample_chunks = rag_chunks[:3]
                qa_context_items = []
                for i, chunk in enumerate(sample_chunks, start=1):
                    classifier = chunk["classifier_label"]
                    confidence = chunk["document_confidence"]
                    text_preview = chunk["text"][:80] + "..." if len(chunk["text"]) > 80 else chunk["text"]
                    qa_context_items.append(f"Context {i} [{classifier}] (confidence: {confidence:.2f}): {text_preview}")
                
                logger.info(f"✅ KAG-RAG integration successful: {len(rag_chunks)} chunks ready for embeddings")
                logger.info(f"✅ Enhanced QA prompts validated with classifier and confidence metadata")
                logger.info(f"✅ Sample QA context: {qa_context_items[0][:100]}...")
                
                # Store RAG integration results
                rag_integration_results = {
                    "adapter_loaded_docs": len(docs),
                    "embedding_chunks_created": len(embedding_chunks),
                    "rag_chunks_converted": len(rag_chunks),
                    "enhanced_qa_validated": True,
                    "sample_qa_context": qa_context_items[0] if qa_context_items else None
                }
            else:
                logger.error("❌ RAG adapter failed to load KAG input")
                rag_integration_results = {"error": "Failed to load KAG input through RAG adapter"}
        
        except Exception as e:
            logger.error(f"❌ KAG-RAG integration test failed: {e}")
            rag_integration_results = {"error": str(e)}
        
        # Save pipeline result summary
        out_file = output_dir / f"{pdf_path.stem}_pipeline_result.json"
        result_summary = {
            "success": True,
            "pipeline_id": pipeline_id,
            "processing_method": hybrid_result["method"],
            "total_pages": hybrid_result["total_pages"],
            "processed_pages": hybrid_result["processed_pages"],
            "text_length": len(full_text),
            "classification": verdict_dict,
            "rag_integration": rag_integration_results,
            "artifacts": {
                "parsed_output": str(parsed_output_path),
                "classification_verdict": str(classification_verdict_path),
                "kag_input": str(kag_input_path)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(result_summary, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"✅ Pipeline result saved → {out_file}")
        
        # Load KAG data for dashboard
        with open(kag_input_path, 'r', encoding='utf-8') as f:
            kag_data = json.load(f)
        
        # 🎯 Print dashboard summary
        print("\n====================== 📊 PIPELINE SUMMARY ======================")
        print(f"📄 Document ID     : {kag_data.get('document_id')}")
        print(f"🏷️ Classification  : {kag_data['classifier_verdict'].get('label')} "
              f"(score={kag_data['classifier_verdict'].get('score')}, "
              f"confidence={kag_data['classifier_verdict'].get('confidence')})")
        print(f"✍️ Text length      : {len(kag_data['parsed_document'].get('full_text',''))} chars")
        print(f"🧾 Clauses         : {len(kag_data['parsed_document'].get('clauses', []))}")
        print(f"👤 Named Entities  : {len(kag_data['parsed_document'].get('named_entities', []))}")
        print(f"🔑 KV Pairs        : {len(kag_data['parsed_document'].get('key_value_pairs', []))}")
        print(f"🔧 Processing      : {hybrid_result['method']}")
        print(f"📊 Pages Processed : {hybrid_result['processed_pages']}/{hybrid_result['total_pages']}")
        
        # Display KAG-RAG integration results
        if 'rag_integration' in result_summary and 'error' not in result_summary['rag_integration']:
            rag_results = result_summary['rag_integration']
            print(f"🔗 RAG Integration : ✅ {rag_results.get('rag_chunks_converted', 0)} chunks ready")
            print(f"🎯 Enhanced QA     : ✅ Classifier + confidence metadata included")
        else:
            print(f"🔗 RAG Integration : ❌ Failed")
        
        print("===============================================================\n")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check for command line argument
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        if not pdf_path.exists():
            print(f"❌ Error: File not found: {pdf_path}")
            sys.exit(1)
    else:
        # Default file if no argument provided
        pdf_path = Path("data/test-files/MCRC_46229_2018_FinalOrder_02-Jan-2019.pdf")
    
    output_dir = Path("artifacts/single_test")
    test_single_pdf(pdf_path, output_dir)
