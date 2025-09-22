"""
Google Document AI client wrapper.

This module provides a clean interface for interacting with Google Document AI,
handling authentication, retries, and GCS URI processing.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from google.cloud import documentai
from google.cloud import storage
from google.api_core import exceptions as gcp_exceptions
from google.api_core import retry

from .schema import ParseRequest, DocumentMetadata


logger = structlog.get_logger(__name__)


class DocAIError(Exception):
    """Base exception for DocAI client errors."""
    pass


class DocAIAuthenticationError(DocAIError):
    """Raised when authentication fails."""
    pass


class DocAIProcessingError(DocAIError):
    """Raised when document processing fails."""
    pass


class DocAIClient:
    """
    Google Document AI client wrapper.
    
    Provides methods to process documents using Google Document AI
    with proper error handling, retries, and logging.
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "us",
        processor_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize DocAI client.
        
        Args:
            project_id: Google Cloud project ID
            location: DocAI processor location (default: "us")
            processor_id: Default processor ID to use
            credentials_path: Path to service account credentials JSON
        """
        self.project_id = project_id
        self.location = location
        self.default_processor_id = processor_id
        self.credentials_path = credentials_path
        
        # Initialize clients
        self._client = None
        self._storage_client = None
        
        logger.info(
            "DocAI client initialized",
            project_id=project_id,
            location=location,
            processor_id=processor_id
        )
    
    @property
    def client(self) -> documentai.DocumentProcessorServiceClient:
        """Get or create DocumentAI client."""
        if self._client is None:
            try:
                if self.credentials_path:
                    self._client = documentai.DocumentProcessorServiceClient.from_service_account_file(
                        self.credentials_path
                    )
                else:
                    self._client = documentai.DocumentProcessorServiceClient()
                
                logger.info("DocumentAI client created successfully")
                
            except Exception as e:
                logger.error("Failed to create DocumentAI client", error=str(e))
                raise DocAIAuthenticationError(f"Failed to authenticate with DocAI: {e}")
        
        return self._client
    
    @property
    def storage_client(self) -> storage.Client:
        """Get or create Storage client."""
        if self._storage_client is None:
            try:
                if self.credentials_path:
                    self._storage_client = storage.Client.from_service_account_json(
                        self.credentials_path
                    )
                else:
                    self._storage_client = storage.Client(project=self.project_id)
                
                logger.info("Storage client created successfully")
                
            except Exception as e:
                logger.error("Failed to create Storage client", error=str(e))
                raise DocAIAuthenticationError(f"Failed to authenticate with Storage: {e}")
        
        return self._storage_client
    
    def get_processor_name(self, processor_id: Optional[str] = None) -> str:
        """
        Build processor resource name.
        
        Args:
            processor_id: Processor ID (uses default if not provided)
            
        Returns:
            Full processor resource name
        """
        proc_id = processor_id or self.default_processor_id
        if not proc_id:
            raise DocAIError("No processor ID provided")
        
        return self.client.processor_path(
            self.project_id,
            self.location,
            proc_id
        )
    
    def _save_raw_response(self, response: documentai.ProcessResponse) -> None:
        """
        Save full raw DocAI response for diagnostics.
        
        Args:
            response: Full DocAI process response
        """
        try:
            # Create artifacts directory
            artifacts_dir = Path("artifacts") / "vision_to_docai"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert response to dictionary for JSON serialization
            response_dict = {
                "text": response.document.text if response.document.text else "",
                "pages": [],
                "entities": [],
                "page_count": len(response.document.pages) if response.document.pages else 0,
                "entity_count": len(response.document.entities) if response.document.entities else 0
            }
            
            # Extract pages
            if response.document.pages:
                for page in response.document.pages:
                    page_dict = {
                        "page_number": getattr(page, 'page_number', 0),
                        "width": page.dimension.width if page.dimension else 0,
                        "height": page.dimension.height if page.dimension else 0,
                        "blocks": [],
                        "tokens": []
                    }
                    
                    # Extract blocks
                    if hasattr(page, 'blocks') and page.blocks:
                        for block in page.blocks:
                            block_dict = {
                                "text": self._get_text_anchor_text(block.layout.text_anchor, response.document.text) if block.layout and block.layout.text_anchor else "",
                                "confidence": block.layout.confidence if block.layout else 0.0
                            }
                            page_dict["blocks"].append(block_dict)
                    
                    response_dict["pages"].append(page_dict)
            
            # Extract entities
            if response.document.entities:
                for entity in response.document.entities:
                    entity_dict = {
                        "type": entity.type_,
                        "mention_text": entity.mention_text,
                        "confidence": entity.confidence,
                        "id": entity.id if entity.id else "",
                        "start_offset": None,
                        "end_offset": None
                    }
                    
                    # Extract offsets from text anchor
                    if entity.text_anchor and entity.text_anchor.text_segments:
                        segment = entity.text_anchor.text_segments[0]
                        entity_dict["start_offset"] = segment.start_index
                        entity_dict["end_offset"] = segment.end_index
                    
                    response_dict["entities"].append(entity_dict)
            
            # Save to artifacts
            with open(artifacts_dir / "docai_raw_full.json", 'w', encoding='utf-8') as f:
                json.dump(response_dict, f, indent=2)
            
            logger.info("Full raw DocAI response saved to artifacts/vision_to_docai/docai_raw_full.json")
            
        except Exception as e:
            logger.error("Failed to save raw DocAI response", error=str(e))
    
    def _get_text_anchor_text(self, text_anchor, full_text: str) -> str:
        """Extract text from text anchor segments."""
        if not text_anchor or not text_anchor.text_segments:
            return ""
        
        text_parts = []
        for segment in text_anchor.text_segments:
            start = segment.start_index or 0
            end = segment.end_index or len(full_text)
            text_parts.append(full_text[start:end])
        
        return "".join(text_parts)

    def download_from_gcs(self, gcs_uri: str) -> bytes:
        """
        Download document content from Google Cloud Storage with enhanced error handling.
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path)
            
        Returns:
            Document content as bytes
            
        Raises:
            DocAIError: If download fails with detailed error information
        """
        try:
            # Validate GCS URI format
            if not gcs_uri.startswith('gs://'):
                raise ValueError(f"Invalid GCS URI format: {gcs_uri}. Must start with gs://")
            
            uri_parts = gcs_uri[5:].split('/', 1)  # Remove 'gs://' and split
            if len(uri_parts) != 2 or not uri_parts[0] or not uri_parts[1]:
                raise ValueError(f"Invalid GCS URI format: {gcs_uri}. Expected gs://bucket/path")
            
            bucket_name, blob_name = uri_parts
            
            logger.info("Downloading from GCS", gcs_uri=gcs_uri, bucket=bucket_name, blob=blob_name)
            
            # Check if bucket exists and is accessible
            try:
                bucket = self.storage_client.bucket(bucket_name)
                if not bucket.exists():
                    raise DocAIError(f"Bucket '{bucket_name}' does not exist or is not accessible")
            except Exception as e:
                if "403" in str(e) or "Forbidden" in str(e):
                    raise DocAIError(f"Access denied to bucket '{bucket_name}'. Check IAM permissions.")
                elif "404" in str(e):
                    raise DocAIError(f"Bucket '{bucket_name}' not found")
                else:
                    raise DocAIError(f"Error accessing bucket '{bucket_name}': {e}")
            
            # Download blob
            blob = bucket.blob(blob_name)
            
            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {gcs_uri}")
            
            # Check file size (limit to reasonable size)
            blob.reload()  # Get current metadata
            file_size = blob.size
            max_size = 50 * 1024 * 1024  # 50MB limit
            
            if file_size > max_size:
                raise DocAIError(f"File too large: {file_size / 1024 / 1024:.1f}MB (max: {max_size / 1024 / 1024}MB)")
            
            content = blob.download_as_bytes()
            
            logger.info("Downloaded from GCS", size_bytes=len(content), file_size_mb=f"{len(content) / 1024 / 1024:.2f}")
            return content
            
        except DocAIError:
            raise
        except FileNotFoundError as e:
            logger.error("File not found in GCS", gcs_uri=gcs_uri, error=str(e))
            raise DocAIError(f"File not found: {e}")
        except Exception as e:
            logger.error("Failed to download from GCS", gcs_uri=gcs_uri, error=str(e))
            if "403" in str(e) or "Forbidden" in str(e):
                raise DocAIError(f"Access denied to GCS resource. Check IAM permissions: {e}")
            elif "404" in str(e):
                raise DocAIError(f"GCS resource not found: {e}")
            else:
                raise DocAIError(f"GCS download failed: {e}")
    
    def ensure_bucket_exists(self, bucket_name: str, location: str = "US") -> bool:
        """
        Ensure GCS bucket exists, create if necessary.
        
        Args:
            bucket_name: Name of the bucket
            location: GCS location for new bucket
            
        Returns:
            True if bucket exists or was created successfully
            
        Raises:
            DocAIError: If bucket creation fails
        """
        try:
            bucket = self.storage_client.bucket(bucket_name)
            
            if bucket.exists():
                logger.info("Using existing bucket", bucket_name=bucket_name)
                return True
            
            # Create bucket with proper configuration
            logger.info("Creating new bucket", bucket_name=bucket_name, location=location)
            
            bucket = self.storage_client.create_bucket(
                bucket_name,
                location=location,
                predefined_acl="private"  # Secure by default
            )
            
            logger.info("Created bucket successfully", bucket_name=bucket_name)
            return True
            
        except Exception as e:
            logger.error("Failed to ensure bucket exists", bucket_name=bucket_name, error=str(e))
            if "409" in str(e) or "already exists" in str(e).lower():
                # Bucket exists but we can't access it
                logger.warning("Bucket exists but access denied", bucket_name=bucket_name)
                return True
            elif "403" in str(e) or "Forbidden" in str(e):
                raise DocAIError(f"Permission denied: Cannot create or access bucket '{bucket_name}'. Check IAM permissions.")
            else:
                raise DocAIError(f"Failed to ensure bucket exists: {e}")
    
    def get_document_metadata(self, gcs_uri: str, content: bytes) -> DocumentMetadata:
        """
        Extract document metadata.
        
        Args:
            gcs_uri: GCS URI of the document
            content: Document content bytes
            
        Returns:
            Document metadata
        """
        try:
            # Extract filename from GCS URI
            filename = Path(gcs_uri).name
            
            # Basic metadata - in real implementation you might use libraries
            # like PyPDF2 or pdfplumber to extract more detailed metadata
            metadata = DocumentMetadata(
                document_id=f"docai_{int(time.time())}_{hash(gcs_uri) % 10000:04d}",
                original_filename=filename,
                file_size=len(content),
                page_count=1,  # Would be calculated from actual document
                language="en",  # Would be detected from document
                processor_id=self.default_processor_id
            )
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to extract metadata", error=str(e))
            raise DocAIError(f"Failed to extract metadata: {e}")
    
    @retry.Retry(
        predicate=retry.if_exception_type(
            gcp_exceptions.ServiceUnavailable,
            gcp_exceptions.InternalServerError,
            gcp_exceptions.TooManyRequests
        ),
        initial=1.0,
        maximum=60.0,
        multiplier=2.0,
        deadline=300.0
    )
    def process_document_sync(
        self, 
        content: bytes, 
        mime_type: str,
        processor_id: Optional[str] = None,
        enable_native_pdf_parsing: bool = True
    ) -> documentai.Document:
        """
        Process document synchronously with DocAI.
        
        Args:
            content: Document content as bytes
            mime_type: MIME type of the document
            processor_id: Processor ID to use (optional)
            enable_native_pdf_parsing: Whether to enable native PDF parsing
            
        Returns:
            Processed Document from DocAI
        """
        try:
            processor_name = self.get_processor_name(processor_id)
            
            logger.info(
                "Processing document with DocAI",
                processor=processor_name,
                mime_type=mime_type,
                size_bytes=len(content),
                native_pdf=enable_native_pdf_parsing
            )
            
            # Create raw document
            raw_document = documentai.RawDocument(
                content=content,
                mime_type=mime_type
            )
            
            # Create process request (simplified - remove problematic process options for now)
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document
            )
            
            # Process document
            start_time = time.time()
            response = self.client.process_document(request=request)
            processing_time = time.time() - start_time
            
            # Save full raw response for diagnostics
            self._save_raw_response(response)
            
            logger.info(
                "Document processing completed",
                processing_time=processing_time,
                pages=len(response.document.pages) if response.document.pages else 0,
                entities=len(response.document.entities) if response.document.entities else 0
            )
            
            return response.document
            
        except gcp_exceptions.GoogleAPICallError as e:
            logger.error("DocAI API error", error=str(e), error_code=e.code)
            raise DocAIProcessingError(f"DocAI processing failed: {e}")
        except Exception as e:
            logger.error("Unexpected error during processing", error=str(e))
            raise DocAIError(f"Unexpected processing error: {e}")
    
    async def process_document_async(
        self,
        content: bytes,
        mime_type: str,
        processor_id: Optional[str] = None,
        enable_native_pdf_parsing: bool = True
    ) -> documentai.Document:
        """
        Process document asynchronously.
        
        This method runs the synchronous processing in a thread pool
        to avoid blocking the async event loop.
        
        Args:
            content: Document content as bytes
            mime_type: MIME type of the document
            processor_id: Processor ID to use (optional)
            enable_native_pdf_parsing: Whether to enable native PDF parsing
            
        Returns:
            Processed Document from DocAI
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            None,
            self.process_document_sync,
            content,
            mime_type,
            processor_id,
            enable_native_pdf_parsing
        )
    
    def process_gcs_document(
        self,
        gcs_uri: str,
        processor_id: Optional[str] = None,
        enable_native_pdf_parsing: bool = True
    ) -> tuple[documentai.Document, DocumentMetadata]:
        """
        Process document from GCS URI.
        
        Args:
            gcs_uri: GCS URI of the document
            processor_id: Processor ID to use (optional)
            enable_native_pdf_parsing: Whether to enable native PDF parsing
            
        Returns:
            Tuple of (processed document, metadata)
        """
        try:
            # Download document
            content = self.download_from_gcs(gcs_uri)
            
            # Get metadata
            metadata = self.get_document_metadata(gcs_uri, content)
            
            # Determine MIME type from filename
            filename = Path(gcs_uri).name.lower()
            if filename.endswith('.pdf'):
                mime_type = "application/pdf"
            elif filename.endswith(('.png', '.jpg', '.jpeg')):
                mime_type = f"image/{filename.split('.')[-1]}"
            else:
                # Default to PDF
                mime_type = "application/pdf"
            
            # Process document
            document = self.process_document_sync(
                content,
                mime_type,
                processor_id,
                enable_native_pdf_parsing
            )
            
            return document, metadata
            
        except Exception as e:
            logger.error("Failed to process GCS document", gcs_uri=gcs_uri, error=str(e))
            raise
    
    async def process_gcs_document_async(
        self,
        gcs_uri: str,
        processor_id: Optional[str] = None,
        enable_native_pdf_parsing: bool = True
    ) -> tuple[documentai.Document, DocumentMetadata]:
        """
        Process document from GCS URI asynchronously.
        
        Args:
            gcs_uri: GCS URI of the document
            processor_id: Processor ID to use (optional)
            enable_native_pdf_parsing: Whether to enable native PDF parsing
            
        Returns:
            Tuple of (processed document, metadata)
        """
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            None,
            self.process_gcs_document,
            gcs_uri,
            processor_id,
            enable_native_pdf_parsing
        )