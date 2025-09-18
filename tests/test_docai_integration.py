#!/usr/bin/env python3
"""
Comprehensive DocAI Integration Test Script

Tests the DocAI integration using the existing test document and credentials.
This script will process the test PDF through DocAI and validate the complete pipeline.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

class DocAITester:
    """Comprehensive test suite for DocAI integration."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        self.location = os.getenv("DOCAI_LOCATION", "us")
        self.processor_id = os.getenv("DOCAI_PROCESSOR_ID")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Test file path
        self.test_file = Path("./data/test-files/testing-ocr-pdf-1.pdf")
        self.results_dir = Path("./data/processed")
        self.results_dir.mkdir(exist_ok=True)
        
        print("🔧 DocAI Test Configuration:")
        print(f"   Project ID: {self.project_id}")
        print(f"   Location: {self.location}")
        print(f"   Processor ID: {self.processor_id}")
        print(f"   Credentials: {self.credentials_path}")
        print(f"   Test file: {self.test_file}")
        print("")
    
    def validate_setup(self):
        """Validate the test setup."""
        print("🔍 Validating setup...")
        
        # Check environment variables
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID not set")
        if not self.processor_id:
            raise ValueError("DOCAI_PROCESSOR_ID not set")
        if not self.credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set")
        
        # Check credentials file
        if not Path(self.credentials_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
        
        # Check test file
        if not self.test_file.exists():
            raise FileNotFoundError(f"Test file not found: {self.test_file}")
        
        print("✅ Setup validation passed")
        print("")
    
    def test_imports(self):
        """Test that all DocAI components can be imported."""
        print("📦 Testing imports...")
        
        try:
            from services.doc_ai.schema import (
                ParseRequest, ParseResponse, ParsedDocument, 
                DocumentMetadata, NamedEntity, Clause
            )
            print("   ✓ Schema imports successful")
        except Exception as e:
            print(f"   ✗ Schema import failed: {e}")
            return False
        
        try:
            from services.doc_ai.client import DocAIClient
            print("   ✓ Client import successful") 
        except Exception as e:
            print(f"   ✗ Client import failed: {e}")
            return False
        
        try:
            from services.doc_ai.parser import DocumentParser
            print("   ✓ Parser import successful")
        except Exception as e:
            print(f"   ✗ Parser import failed: {e}")
            return False
        
        print("✅ All imports successful")
        return True

    async def test_client_initialization(self):
        """Test DocAI client initialization."""
        print("🚀 Testing DocAI client initialization...")
        
        try:
            from services.doc_ai.client import DocAIClient
            
            client = DocAIClient(
                project_id=self.project_id,
                location=self.location,
                processor_id=self.processor_id,
                credentials_path=self.credentials_path
            )
            
            # Test processor name generation
            processor_name = client.get_processor_name()
            print(f"   Processor name: {processor_name}")
            
            print("✅ Client initialization successful")
            return client
            
        except Exception as e:
            print(f"❌ Client initialization failed: {e}")
            raise

    def test_authentication(self):
        """Test Google Cloud authentication."""
        print("🔐 Testing Google Cloud authentication...")
        
        try:
            from google.cloud import documentai
            from google.oauth2 import service_account
            
            # Load credentials
            credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
            print("   ✓ Credentials loaded successfully")
            
            # Create client
            client = documentai.DocumentProcessorServiceClient(credentials=credentials)
            print("   ✓ DocAI client created successfully")
            
            # Test listing processors
            parent = f'projects/{self.project_id}/locations/{self.location}'
            
            processors = client.list_processors(parent=parent)
            processor_list = list(processors)
            print(f"   ✓ Found {len(processor_list)} processors")
            
            # Check if our processor exists
            our_processor = None
            for proc in processor_list:
                if self.processor_id in proc.name:
                    our_processor = proc
                    break
            
            if our_processor:
                print(f"   ✓ Found our processor: {our_processor.display_name}")
            else:
                print(f"   ⚠️  Processor {self.processor_id} not found in list")
            
            print("✅ Authentication successful")
            return True
            
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            raise

    async def test_local_file_processing(self, client):
        """Test processing the local test file."""
        print("📄 Testing local file processing...")
        
        try:
            # Read the test file
            with open(self.test_file, 'rb') as f:
                file_content = f.read()
            
            print(f"   File size: {len(file_content):,} bytes")
            
            # Create metadata
            from services.doc_ai.schema import DocumentMetadata
            metadata = DocumentMetadata(
                document_id=f"test_{int(datetime.now().timestamp())}",
                original_filename=self.test_file.name,
                file_size=len(file_content),
                page_count=1,  # Will be updated after processing
                language="en",
                processor_id=self.processor_id
            )
            
            # Process document
            print("   Processing with DocAI...")
            docai_document = await client.process_document_async(
                content=file_content,
                mime_type="application/pdf",
                enable_native_pdf_parsing=True
            )
            
            print(f"   ✓ DocAI processing completed")
            print(f"   Text length: {len(docai_document.text) if docai_document.text else 0}")
            print(f"   Pages: {len(docai_document.pages) if docai_document.pages else 0}")
            print(f"   Entities: {len(docai_document.entities) if docai_document.entities else 0}")
            
            # Show first 200 characters of extracted text
            if docai_document.text:
                preview = docai_document.text[:200].replace('\n', ' ')
                print(f"   Text preview: {preview}...")
            
            print("✅ Local file processing successful")
            return docai_document, metadata
            
        except Exception as e:
            print(f"❌ Local file processing failed: {e}")
            traceback.print_exc()
            raise

    def test_document_parsing(self, docai_document, metadata):
        """Test document parsing and normalization."""
        print("🔧 Testing document parsing...")
        
        try:
            from services.doc_ai.parser import DocumentParser
            
            parser = DocumentParser(confidence_threshold=0.7)
            
            # Parse the document
            parsed_doc = parser.parse_document(
                docai_document=docai_document,
                metadata=metadata,
                include_raw_response=False
            )
            
            print(f"   Full text length: {len(parsed_doc.full_text)}")
            print(f"   Named entities: {len(parsed_doc.named_entities)}")
            print(f"   Clauses: {len(parsed_doc.clauses)}")
            print(f"   Key-value pairs: {len(parsed_doc.key_value_pairs)}")
            print(f"   Cross-references: {len(parsed_doc.cross_references)}")
            print(f"   Warnings: {len(parsed_doc.processing_warnings)}")
            
            # Show entity details
            if parsed_doc.named_entities:
                print("   \n📋 Sample entities:")
                for i, entity in enumerate(parsed_doc.named_entities[:5]):
                    print(f"      {i+1}. {entity.type}: '{entity.text_span.text}' (confidence: {entity.confidence:.2f})")
            
            # Show clause details
            if parsed_doc.clauses:
                print("   \n📝 Sample clauses:")
                for i, clause in enumerate(parsed_doc.clauses[:3]):
                    text_preview = clause.text_span.text[:100] + "..." if len(clause.text_span.text) > 100 else clause.text_span.text
                    print(f"      {i+1}. {clause.type}: '{text_preview}' (confidence: {clause.confidence:.2f})")
            
            # Show warnings
            if parsed_doc.processing_warnings:
                print("   \n⚠️  Processing warnings:")
                for warning in parsed_doc.processing_warnings:
                    print(f"      - {warning}")
            
            # Show statistics
            print(f"   \n📊 Statistics:")
            print(f"      Average entity confidence: {parsed_doc.entity_confidence_avg:.2f}")
            print(f"      Average clause confidence: {parsed_doc.clause_confidence_avg:.2f}")
            
            print("✅ Document parsing successful")
            return parsed_doc
            
        except Exception as e:
            print(f"❌ Document parsing failed: {e}")
            traceback.print_exc()
            raise

    def save_results(self, parsed_doc, docai_document):
        """Save test results for inspection."""
        print("💾 Saving test results...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save parsed document
            parsed_file = self.results_dir / f"docai_parsed_{timestamp}.json"
            with open(parsed_file, 'w', encoding='utf-8') as f:
                # Convert to dict and handle datetime serialization
                data = parsed_doc.dict()
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            # Save raw DocAI response (simplified)
            raw_file = self.results_dir / f"docai_raw_{timestamp}.json"
            with open(raw_file, 'w', encoding='utf-8') as f:
                raw_data = {
                    "text": docai_document.text,
                    "page_count": len(docai_document.pages) if docai_document.pages else 0,
                    "entity_count": len(docai_document.entities) if docai_document.entities else 0,
                    "text_preview": docai_document.text[:500] + "..." if docai_document.text and len(docai_document.text) > 500 else docai_document.text
                }
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
            print(f"   ✓ Parsed results: {parsed_file}")
            print(f"   ✓ Raw results: {raw_file}")
            print("✅ Results saved successfully")
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

    async def test_gcs_upload_and_process(self, client):
        """Test uploading to GCS and processing."""
        print("☁️  Testing GCS upload and processing...")
        
        try:
            from google.cloud import storage
            
            # Create storage client
            storage_client = storage.Client(project=self.project_id)
            
            # Create or get bucket
            bucket_name = f"{self.project_id}-docai-test"
            try:
                bucket = storage_client.create_bucket(bucket_name, location="US")
                print(f"   ✓ Created bucket: {bucket_name}")
            except Exception:
                bucket = storage_client.bucket(bucket_name)
                print(f"   ✓ Using existing bucket: {bucket_name}")
            
            # Upload test file
            blob_name = f"test-documents/{self.test_file.name}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(self.test_file))
            
            gcs_uri = f"gs://{bucket_name}/{blob_name}"
            print(f"   ✓ Uploaded to: {gcs_uri}")
            
            # Process from GCS
            print("   Processing from GCS...")
            docai_document, metadata = await client.process_gcs_document_async(
                gcs_uri=gcs_uri,
                enable_native_pdf_parsing=True
            )
            
            print(f"   ✓ GCS processing completed")
            print(f"   Document ID: {metadata.document_id}")
            
            print("✅ GCS processing successful")
            return docai_document, metadata, gcs_uri
            
        except Exception as e:
            print(f"❌ GCS processing failed: {e}")
            print("   This is optional - local processing works fine")
            return None, None, None

    async def run_comprehensive_test(self):
        """Run comprehensive DocAI integration test."""
        print("🧪 Starting comprehensive DocAI integration test")
        print("=" * 60)
        
        try:
            # Validate setup
            self.validate_setup()
            
            # Test imports
            if not self.test_imports():
                return False
            
            # Test authentication
            self.test_authentication()
            
            # Test client initialization
            client = await self.test_client_initialization()
            
            # Test local file processing
            docai_document, metadata = await self.test_local_file_processing(client)
            
            # Test document parsing
            parsed_doc = self.test_document_parsing(docai_document, metadata)
            
            # Save results
            self.save_results(parsed_doc, docai_document)
            
            # Test GCS processing (optional)
            print("\n" + "=" * 60)
            try:
                gcs_doc, gcs_metadata, gcs_uri = await self.test_gcs_upload_and_process(client)
                if gcs_doc:
                    print(f"🌟 GCS URI for future tests: {gcs_uri}")
            except Exception as e:
                print(f"⚠️  GCS test skipped: {e}")
            
            print("\n" + "=" * 60)
            print("🎉 All tests completed successfully!")
            print("\n📋 Summary:")
            print(f"   Document: {self.test_file.name}")
            print(f"   Text length: {len(parsed_doc.full_text):,} characters")
            print(f"   Entities found: {len(parsed_doc.named_entities)}")
            print(f"   Clauses found: {len(parsed_doc.clauses)}")
            print(f"   Processing warnings: {len(parsed_doc.processing_warnings)}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            traceback.print_exc()
            return False

async def main():
    """Main test function."""
    tester = DocAITester()
    success = await tester.run_comprehensive_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())