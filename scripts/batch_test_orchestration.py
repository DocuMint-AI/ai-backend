#!/usr/bin/env python3
"""
Batch Document Processing Test

This script processes all PDFs in data/test-files through the complete
orchestration pipeline and outputs results to artifacts/batch_test/.
"""

import sys
import os
import json
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from main import app

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

client = TestClient(app)

def process_all_pdfs():
    """Process all PDFs in test-files directory."""
    test_files_dir = Path("data/test-files")
    output_dir = Path("artifacts/batch_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not test_files_dir.exists():
        logger.error(f"Test files directory not found: {test_files_dir}")
        return False
    
    pdf_files = list(test_files_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found in test-files directory")
        return False
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    results = []
    successful = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING FILE {i}/{len(pdf_files)}: {pdf_path.name}")
        logger.info(f"{'='*60}")
        
        try:
            # Process through API
            with open(pdf_path, "rb") as f:
                files = {"file": (pdf_path.name, f, "application/pdf")}
                response = client.post("/api/v1/process-document", files=files)
            
            if response.status_code == 200:
                result = response.json()
                pipeline_id = result.get("pipeline_id", "unknown")
                
                # Save result
                result_file = output_dir / f"{pdf_path.stem}_result.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                
                # Check for kag_input.json
                processed_dir = Path("data/processed") / pipeline_id
                kag_file = processed_dir / "kag_input.json"
                
                if kag_file.exists():
                    logger.info(f"✅ SUCCESS: {pdf_path.name} → kag_input.json generated")
                    successful += 1
                else:
                    logger.warning(f"⚠️ PARTIAL: {pdf_path.name} → processed but no kag_input.json")
                
                results.append({
                    "file": pdf_path.name,
                    "status": "success",
                    "pipeline_id": pipeline_id,
                    "kag_generated": kag_file.exists()
                })
                
            else:
                logger.error(f"❌ FAILED: {pdf_path.name} → HTTP {response.status_code}")
                results.append({
                    "file": pdf_path.name,
                    "status": "failed",
                    "error": response.text
                })
                
        except Exception as e:
            logger.error(f"❌ ERROR: {pdf_path.name} → {e}")
            results.append({
                "file": pdf_path.name,
                "status": "error",
                "error": str(e)
            })
    
    # Save batch summary
    summary = {
        "total_files": len(pdf_files),
        "successful": successful,
        "success_rate": f"{successful/len(pdf_files)*100:.1f}%",
        "timestamp": "{{ timestamp }}",
        "results": results
    }
    
    summary_file = output_dir / "batch_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"BATCH PROCESSING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total files: {len(pdf_files)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Success rate: {successful/len(pdf_files)*100:.1f}%")
    logger.info(f"Results saved to: {output_dir}")
    
    return successful == len(pdf_files)

if __name__ == "__main__":
    import datetime
    # Replace timestamp placeholder
    script_content = Path(__file__).read_text()
    script_content = script_content.replace("{{ timestamp }}", datetime.datetime.now().isoformat())
    
    success = process_all_pdfs()
    sys.exit(0 if success else 1)
