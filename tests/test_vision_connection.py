#!/usr/bin/env python3
"""
Test Google Vision API connection and OCR functionality.
"""

import sys
import os
from pathlib import Path

# Add services to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'preprocessing'))

def test_vision_api_connection():
    """Test the Google Vision API connection."""
    
    print("=" * 60)
    print("Testing Google Vision API Connection")
    print("=" * 60)
    
    try:
        # Import our OCR module
        import importlib.util
        ocr_spec = importlib.util.spec_from_file_location("ocr_processing", 
            os.path.join(os.path.dirname(__file__), 'services', 'preprocessing', 'OCR-processing.py'))
        ocr_module = importlib.util.module_from_spec(ocr_spec)
        ocr_spec.loader.exec_module(ocr_module)
        
        GoogleVisionOCR = ocr_module.GoogleVisionOCR
        
        print("✓ OCR module imported successfully")
        
        # Test 1: Create OCR instance from environment
        print("\n1. Testing OCR instance creation from environment...")
        try:
            ocr = GoogleVisionOCR.from_env()
            print(f"✓ OCR instance created successfully")
            print(f"  Project ID: {ocr.project_id}")
            print(f"  Language hints: {ocr.language_hints}")
            print(f"  Credentials path: {ocr.credentials_path}")
        except Exception as e:
            print(f"✗ Failed to create OCR instance: {e}")
            return False
        
        # Test 2: Test OCR on our test image
        print("\n2. Testing OCR on test image...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        test_image_path = os.path.join(script_dir, "data", "test_document.png")
        
        if not os.path.exists(test_image_path):
            print(f"✗ Test image not found: {test_image_path}")
            return False
        
        try:
            # Test image processing
            result = ocr.extract_text(test_image_path, page_number=1, image_metadata={
                "width": 800,
                "height": 600,
                "dpi": 300
            })
            
            print(f"✓ OCR processing completed successfully")
            
            # Validate result structure
            if "page_data" in result:
                page_data = result["page_data"]
                print(f"  Page: {page_data['page']}")
                print(f"  Dimensions: {page_data['width']}x{page_data['height']}")
                print(f"  Confidence: {page_data['page_confidence']:.2f}")
                print(f"  Text blocks: {len(page_data['text_blocks'])}")
                
                # Show extracted text
                full_text = result.get("full_text", "")
                print(f"\n  Extracted text preview:")
                print(f"  {full_text[:200]}{'...' if len(full_text) > 200 else ''}")
                
                # Show first block details
                if page_data['text_blocks']:
                    first_block = page_data['text_blocks'][0]
                    print(f"\n  First block details:")
                    print(f"    Block ID: {first_block['block_id']}")
                    print(f"    Text: {first_block['text'][:50]}...")
                    print(f"    Confidence: {first_block['confidence']:.2f}")
                    print(f"    Lines: {len(first_block['lines'])}")
                
            else:
                print(f"✗ Invalid result structure: {list(result.keys())}")
                return False
                
        except Exception as e:
            print(f"✗ OCR processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 3: Test complete DocAI document creation
        print("\n3. Testing complete DocAI document creation...")
        try:
            # Create sample derived images
            derived_images = [{
                "page": 1,
                "image_uri": f"file://{test_image_path}",
                "width": 800,
                "height": 600,
                "dpi": 300
            }]
            
            # Create complete document
            docai_doc = ocr.create_docai_document(
                document_id="test_doc_001",
                original_filename="test_document.png",
                pdf_path=test_image_path,
                pages_data=[result],
                derived_images=derived_images
            )
            
            print(f"✓ DocAI document created successfully")
            print(f"  Document ID: {docai_doc.document_id}")
            print(f"  Original filename: {docai_doc.original_filename}")
            print(f"  File fingerprint: {docai_doc.file_fingerprint[:30]}...")
            print(f"  Language: {docai_doc.language_detection['primary']}")
            print(f"  Pages: {len(docai_doc.ocr_result['pages'])}")
            print(f"  Pipeline version: {docai_doc.preprocessing['pipeline_version']}")
            
            # Save the result
            import json
            output_path = os.path.join(script_dir, "data", "test_ocr_result.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "document_id": docai_doc.document_id,
                    "original_filename": docai_doc.original_filename,
                    "file_fingerprint": docai_doc.file_fingerprint,
                    "pdf_uri": docai_doc.pdf_uri,
                    "derived_images": docai_doc.derived_images,
                    "language_detection": docai_doc.language_detection,
                    "ocr_result": docai_doc.ocr_result,
                    "extracted_assets": docai_doc.extracted_assets,
                    "preprocessing": docai_doc.preprocessing,
                    "warnings": docai_doc.warnings
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Result saved to: {output_path}")
            
        except Exception as e:
            print(f"✗ DocAI document creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"\n" + "=" * 60)
        print("🎉 SUCCESS: Google Vision API is working correctly!")
        print("✓ API connection established")
        print("✓ OCR processing functional")
        print("✓ DocAI format generation working")
        print("✓ All components integrated successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vision_api_connection()
    
    if success:
        print("\n🚀 Your OCR pipeline is ready for production use!")
        print("\nNext steps:")
        print("1. Start the FastAPI server: python services/processing-handler.py")
        print("2. Test with PDF files using the /upload and /ocr-process endpoints")
        print("3. Use the /results/{uid} endpoint to retrieve processed results")
    else:
        print("\n❌ Setup incomplete - please review errors above")
        sys.exit(1)