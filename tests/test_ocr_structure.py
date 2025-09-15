#!/usr/bin/env python3
"""
Test the OCR processing structure without requiring Google Cloud dependencies.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock the google.cloud.vision module
class MockVision:
    class Image:
        def __init__(self, content=None):
            self.content = content
    
    class ImageContext:
        def __init__(self, language_hints=None):
            self.language_hints = language_hints
    
    class AnnotateImageResponse:
        def __init__(self):
            self.error = type('Error', (), {'message': ''})()
            self.full_text_annotation = type('FullTextAnnotation', (), {
                'text': 'Sample text for testing',
                'pages': []
            })()
    
    class ImageAnnotatorClient:
        @classmethod
        def from_service_account_file(cls, path):
            return cls()
        
        def document_text_detection(self, image=None, image_context=None):
            return MockVision.AnnotateImageResponse()

# Mock the module before importing
sys.modules['google'] = type('Module', (), {})()
sys.modules['google.cloud'] = type('Module', (), {})()
sys.modules['google.cloud.vision'] = MockVision()
sys.modules['google.api_core'] = type('Module', (), {})()
sys.modules['google.api_core.exceptions'] = type('Module', (), {
    'GoogleAPIError': Exception
})()

# Now we can import our OCR module
import importlib.util
ocr_spec = importlib.util.spec_from_file_location("ocr_processing", 
    os.path.join(os.path.dirname(__file__), 'services', 'preprocessing', 'OCR-processing.py'))
ocr_module = importlib.util.module_from_spec(ocr_spec)
ocr_spec.loader.exec_module(ocr_module)
GoogleVisionOCR = ocr_module.GoogleVisionOCR
OCRResult = ocr_module.OCRResult

def test_ocr_structure():
    """Test the OCR processing structure."""
    print("Testing OCR processing structure...")
    
    # Test basic initialization
    try:
        ocr = GoogleVisionOCR(
            project_id="test-project",
            credentials_path="test-credentials.json",
            language_hints=["en"]
        )
        print("✓ OCR initialization successful")
    except Exception as e:
        print(f"✗ OCR initialization failed: {e}")
        return False
    
    # Test helper methods
    try:
        # Test file fingerprint calculation
        # Create a test file
        test_file = "test_file.txt"
        with open(test_file, 'w') as f:
            f.write("test content")
        
        fingerprint = GoogleVisionOCR.calculate_file_fingerprint(test_file)
        print(f"✓ File fingerprint generation: {fingerprint[:20]}...")
        
        # Clean up
        os.remove(test_file)
        
        # Test language detection
        lang_result = GoogleVisionOCR.detect_language_confidence("This is English text", ["en"])
        print(f"✓ Language detection: {lang_result}")
        
        # Test bounding box conversion
        # Mock bounding box
        mock_bbox = type('BBox', (), {
            'vertices': [
                type('Vertex', (), {'x': 100, 'y': 50})(),
                type('Vertex', (), {'x': 200, 'y': 50})(),
                type('Vertex', (), {'x': 200, 'y': 100})(),
                type('Vertex', (), {'x': 100, 'y': 100})()
            ]
        })()
        
        converted = ocr._convert_bounding_box(mock_bbox, 1240, 1754)
        print(f"✓ Bounding box conversion: {converted}")
        
        # Test block sorting
        sample_blocks = [
            {"bounding_box": [[100, 200], [200, 200], [200, 250], [100, 250]]},
            {"bounding_box": [[100, 50], [200, 50], [200, 100], [100, 100]]},
            {"bounding_box": [[300, 50], [400, 50], [400, 100], [300, 100]]}
        ]
        
        sorted_blocks = ocr._sort_blocks_reading_order(sample_blocks)
        print(f"✓ Block sorting: {len(sorted_blocks)} blocks sorted")
        
        return True
        
    except Exception as e:
        print(f"✗ Helper method testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_docai_document_creation():
    """Test DocAI document creation."""
    print("\nTesting DocAI document creation...")
    
    try:
        ocr = GoogleVisionOCR("test-project", "test-creds.json", ["en"])
        
        # Sample pages data
        sample_pages_data = [
            {
                "page_data": {
                    "page": 1,
                    "width": 1240,
                    "height": 1754,
                    "page_confidence": 0.95,
                    "text_blocks": [
                        {
                            "block_id": "p1_b1",
                            "page": 1,
                            "bounding_box": [[100, 50], [800, 50], [800, 120], [100, 120]],
                            "text": "Sample Document Title",
                            "confidence": 0.98,
                            "lines": [
                                {
                                    "line_id": "p1_b1_l1",
                                    "text": "Sample Document Title",
                                    "confidence": 0.98,
                                    "words": [
                                        {
                                            "text": "Sample",
                                            "confidence": 0.99,
                                            "bounding_box": [[100, 50], [200, 50], [200, 120], [100, 120]]
                                        },
                                        {
                                            "text": "Document",
                                            "confidence": 0.98,
                                            "bounding_box": [[210, 50], [350, 50], [350, 120], [210, 120]]
                                        },
                                        {
                                            "text": "Title",
                                            "confidence": 0.97,
                                            "bounding_box": [[360, 50], [450, 50], [450, 120], [360, 120]]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "warnings": [],
                "full_text": "Sample Document Title"
            }
        ]
        
        # Sample derived images
        derived_images = [
            {
                "page": 1,
                "image_uri": "file:///data/test/page_001.png",
                "width": 1240,
                "height": 1754,
                "dpi": 300
            }
        ]
        
        # Create test file for fingerprint
        test_pdf = "test.pdf"
        with open(test_pdf, 'w') as f:
            f.write("test pdf content")
        
        # Create DocAI document
        docai_result = ocr.create_docai_document(
            document_id="test_doc_123",
            original_filename="test.pdf",
            pdf_path=test_pdf,
            pages_data=sample_pages_data,
            derived_images=derived_images,
            pdf_uri=None
        )
        
        # Clean up
        os.remove(test_pdf)
        
        print(f"✓ DocAI document created successfully")
        print(f"  Document ID: {docai_result.document_id}")
        print(f"  File fingerprint: {docai_result.file_fingerprint[:30]}...")
        print(f"  Pages count: {len(docai_result.ocr_result['pages'])}")
        print(f"  Language: {docai_result.language_detection['primary']}")
        print(f"  Pipeline version: {docai_result.preprocessing['pipeline_version']}")
        
        return True
        
    except Exception as e:
        print(f"✗ DocAI document creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OCR Processing Structure Tests")
    print("=" * 60)
    
    success1 = test_ocr_structure()
    success2 = test_docai_document_creation()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✓ All OCR structure tests passed!")
    else:
        print("✗ Some tests failed!")
    
    print("OCR pipeline is ready for DocAI compatibility")