#!/usr/bin/env python3
"""
Batch Pipeline Test for Hybrid PDF Processing

This script processes all PDF files in data/test-files/ using the hybrid approach
and outputs results to artifacts/batch_test/.

Features:
- Processes multiple PDFs in sequence
- Uses hybrid PDF processing (pypdfium2+pdfplumber fallback)
- Generates all required artifacts (parsed_output.json, classification_verdict.json, kag_input.json)
- Creates comprehensive batch report
- Handles individual file failures gracefully
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import processing functions
from services.util_services import process_pdf_hybrid
from services.preprocessing.ocr_processing import GoogleVisionOCR
from services.template_matching.regex_classifier import create_classifier
from services.kag.kag_writer import generate_kag_input, validate_kag_input_file


def process_single_pdf_batch(
    pdf_path: Path, 
    output_dir: Path, 
    ocr_service: Any = None,
    classifier: Any = None
) -> Dict[str, Any]:
    """
    Process a single PDF file and return results summary.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory for this PDF
        ocr_service: Shared OCR service instance
        classifier: Shared classifier instance
        
    Returns:
        Dictionary with processing results and statistics
    """
    start_time = time.time()
    pipeline_id = f"batch-{pdf_path.stem}-{int(start_time)}"
    
    result = {
        "pdf_file": pdf_path.name,
        "pipeline_id": pipeline_id,
        "success": False,
        "start_time": datetime.now().isoformat(),
        "processing_time": 0.0,
        "error_message": None,
        "statistics": {},
        "artifacts": {}
    }
    
    try:
        # Create output directory for this PDF
        pdf_output_dir = output_dir / pipeline_id
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Processing {pdf_path.name} → {pipeline_id}")
        
        # Stage 1: Hybrid PDF Processing
        hybrid_result = process_pdf_hybrid(
            pdf_path=pdf_path,
            output_dir=pdf_output_dir,
            dpi=300,
            prefer_pymupdf=True
        )
        
        if not hybrid_result["success"]:
            raise Exception(f"Hybrid PDF processing failed: {hybrid_result.get('errors', [])}")
        
        logger.info(f"  ✅ {pdf_path.name}: Processed {hybrid_result['processed_pages']}/{hybrid_result['total_pages']} pages")
        
        # Stage 2: Vision OCR Processing (with error handling)
        vision_results = []
        ocr_errors = []
        
        if hybrid_result["image_paths"] and ocr_service:
            try:
                # Process only first 3 pages for batch efficiency
                max_pages = min(3, len(hybrid_result["image_paths"]))
                vision_results = ocr_service.process_image_list(
                    image_paths=hybrid_result["image_paths"][:max_pages],
                    plumber_texts=hybrid_result["page_texts"][:max_pages]
                )
                
                # Add remaining pages as text-only
                for i in range(max_pages, len(hybrid_result["page_texts"])):
                    vision_results.append({
                        "page": i + 1,
                        "image_path": hybrid_result["image_paths"][i] if i < len(hybrid_result["image_paths"]) else "",
                        "vision_text": "",
                        "vision_confidence": 0.0,
                        "plumber_text": hybrid_result["page_texts"][i],
                        "has_vision": False,
                        "has_plumber": bool(hybrid_result["page_texts"][i].strip()),
                        "processing_error": "Skipped for batch efficiency"
                    })
                
                logger.info(f"  ✅ {pdf_path.name}: Vision OCR processed {max_pages}/{len(hybrid_result['page_texts'])} pages")
                
            except Exception as e:
                logger.warning(f"  ⚠️ {pdf_path.name}: Vision OCR failed: {e}")
                ocr_errors.append(str(e))
                # Fallback to text-only
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
            # No OCR service or images, use text-only
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
        for vision_result in vision_results:
            page_text = vision_result.get("plumber_text", "") or vision_result.get("vision_text", "")
            if page_text.strip():
                full_text_parts.append(page_text.strip())
        
        full_text = "\n\n".join(full_text_parts)
        
        if len(full_text) < 50:
            raise Exception("Insufficient text extracted for processing")
        
        # Stage 3: Create parsed_output.json
        parsed_output = {
            "text": full_text,
            "full_text": full_text,
            "pages": vision_results,
            "clauses": [],
            "named_entities": [],
            "key_value_pairs": [],
            "metadata": {
                "processor_id": "batch-hybrid-processor",
                "pipeline_id": pipeline_id,
                "processing_method": hybrid_result["method"],
                "total_pages": hybrid_result["total_pages"],
                "processed_pages": hybrid_result["processed_pages"],
                "timestamp": datetime.now().isoformat(),
                "batch_mode": True
            }
        }
        
        parsed_output_path = pdf_output_dir / "parsed_output.json"
        with open(parsed_output_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_output, f, indent=2, ensure_ascii=False, default=str)
        
        # Stage 4: Classification
        classification_result = classifier.classify_document(full_text)
        verdict_dict = classifier.export_classification_verdict(classification_result)
        
        classification_verdict_path = pdf_output_dir / "classification_verdict.json"
        with open(classification_verdict_path, 'w', encoding='utf-8') as f:
            json.dump(verdict_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"  ✅ {pdf_path.name}: Classified as '{verdict_dict['label']}' ({verdict_dict['score']:.3f})")
        
        # Stage 5: Generate KAG Input
        kag_input_path = generate_kag_input(
            artifact_dir=pdf_output_dir,
            doc_id=pipeline_id,
            processor_id="batch-hybrid-processor",
            gcs_uri=f"file://{pdf_path}",
            pipeline_version="v1",
            metadata={
                "batch_processing": True,
                "processing_method": hybrid_result["method"],
                "total_pages": hybrid_result["total_pages"],
                "processed_pages": hybrid_result["processed_pages"],
                "original_filename": pdf_path.name
            }
        )
        
        # Stage 6: Validation
        is_valid = validate_kag_input_file(kag_input_path)
        if not is_valid:
            raise Exception("KAG input validation failed")
        
        # Calculate statistics
        processing_time = time.time() - start_time
        
        result.update({
            "success": True,
            "end_time": datetime.now().isoformat(),
            "processing_time": processing_time,
            "statistics": {
                "processing_method": hybrid_result["method"],
                "total_pages": hybrid_result["total_pages"],
                "processed_pages": hybrid_result["processed_pages"],
                "text_length": len(full_text),
                "classification_label": verdict_dict["label"],
                "classification_score": verdict_dict["score"],
                "classification_confidence": verdict_dict["confidence"],
                "vision_ocr_pages": sum(1 for r in vision_results if r.get("has_vision")),
                "plumber_text_pages": sum(1 for r in vision_results if r.get("has_plumber")),
                "ocr_errors": len(ocr_errors)
            },
            "artifacts": {
                "parsed_output": str(parsed_output_path),
                "classification_verdict": str(classification_verdict_path),
                "kag_input": str(kag_input_path)
            }
        })
        
        logger.info(f"  ✅ {pdf_path.name}: Completed in {processing_time:.2f}s")
        
    except Exception as e:
        processing_time = time.time() - start_time
        result.update({
            "success": False,
            "end_time": datetime.now().isoformat(),
            "processing_time": processing_time,
            "error_message": str(e)
        })
        logger.error(f"  ❌ {pdf_path.name}: Failed - {e}")
    
    return result


def run_batch_test():
    """Run batch processing test on all PDFs in test-files directory."""
    logger.info("="*60)
    logger.info("STARTING BATCH PIPELINE TEST")
    logger.info("="*60)
    
    # Setup directories
    test_files_dir = PROJECT_ROOT / "data/test-files"
    output_dir = PROJECT_ROOT / "artifacts/batch_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(test_files_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in {test_files_dir}")
        return False
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Initialize shared services
    try:
        logger.info("Initializing shared services...")
        ocr_service = GoogleVisionOCR.from_env()
        logger.info("✅ Vision OCR service initialized")
    except Exception as e:
        logger.warning(f"⚠️ Vision OCR initialization failed: {e}")
        ocr_service = None
    
    try:
        classifier = create_classifier()
        logger.info("✅ Document classifier initialized")
    except Exception as e:
        logger.error(f"❌ Classifier initialization failed: {e}")
        return False
    
    # Process all PDFs
    batch_start_time = time.time()
    results = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n--- Processing {i}/{len(pdf_files)}: {pdf_file.name} ---")
        
        result = process_single_pdf_batch(
            pdf_path=pdf_file,
            output_dir=output_dir,
            ocr_service=ocr_service,
            classifier=classifier
        )
        results.append(result)
    
    # Generate batch report
    batch_processing_time = time.time() - batch_start_time
    
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]
    
    batch_report = {
        "batch_summary": {
            "start_time": datetime.fromtimestamp(batch_start_time).isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_processing_time": batch_processing_time,
            "total_pdfs": len(pdf_files),
            "successful_pdfs": len(successful_results),
            "failed_pdfs": len(failed_results),
            "success_rate": (len(successful_results) / len(pdf_files)) * 100
        },
        "processing_statistics": {
            "avg_processing_time": sum(r.get("processing_time", 0) for r in successful_results) / max(1, len(successful_results)),
            "total_pages_processed": sum(r.get("statistics", {}).get("processed_pages", 0) for r in successful_results),
            "processing_methods": {
                method: sum(1 for r in successful_results if r.get("statistics", {}).get("processing_method") == method)
                for method in set(r.get("statistics", {}).get("processing_method") for r in successful_results if r.get("statistics", {}).get("processing_method"))
            },
            "classification_distribution": {
                label: sum(1 for r in successful_results if r.get("statistics", {}).get("classification_label") == label)
                for label in set(r.get("statistics", {}).get("classification_label") for r in successful_results if r.get("statistics", {}).get("classification_label"))
            }
        },
        "detailed_results": results
    }
    
    # Save batch report
    batch_report_path = output_dir / "batch_report.json"
    with open(batch_report_path, 'w', encoding='utf-8') as f:
        json.dump(batch_report, f, indent=2, ensure_ascii=False, default=str)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info("="*60)
    logger.info(f"📊 Total PDFs: {len(pdf_files)}")
    logger.info(f"✅ Successful: {len(successful_results)}")
    logger.info(f"❌ Failed: {len(failed_results)}")
    logger.info(f"📈 Success Rate: {batch_report['batch_summary']['success_rate']:.1f}%")
    logger.info(f"⏱️ Total Time: {batch_processing_time:.2f}s")
    logger.info(f"📄 Total Pages: {batch_report['processing_statistics']['total_pages_processed']}")
    
    if successful_results:
        logger.info("\n🎯 Classification Results:")
        for label, count in batch_report['processing_statistics']['classification_distribution'].items():
            logger.info(f"   {label}: {count} documents")
    
    if failed_results:
        logger.info("\n❌ Failed Documents:")
        for result in failed_results:
            logger.info(f"   {result['pdf_file']}: {result['error_message']}")
    
    logger.info(f"\n📁 Batch report saved: {batch_report_path}")
    logger.info(f"📁 Individual results in: {output_dir}")
    
    return len(failed_results) == 0


def main():
    """Main entry point for batch test."""
    logger.info("🔧 Starting Batch Pipeline Test")
    
    success = run_batch_test()
    
    if success:
        logger.info("\n✅ BATCH TEST PASSED - All PDFs processed successfully!")
        return 0
    else:
        logger.error("\n⚠️ BATCH TEST COMPLETED - Some PDFs failed processing!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)