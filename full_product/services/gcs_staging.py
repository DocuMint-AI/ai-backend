"""
GCS Staging Utilities for Document Processing Pipeline.

This module provides utilities for automatically staging local files to GCS
before processing through Vision/DocAI pipelines.
"""

import os
import time
import uuid
import logging
from pathlib import Path
from typing import Optional

from .doc_ai.client import DocAIClient, DocAIError
from .project_utils import get_gcs_paths, get_username_from_env

logger = logging.getLogger(__name__)


def auto_stage_document(
    input_path: str, 
    bucket_name: Optional[str] = None,
    user_session_id: Optional[str] = None,
    username: Optional[str] = None,
    blob_prefix: str = "uploads",
    force_upload: bool = False
) -> str:
    """
    Automatically stage a document to GCS using user session structure.
    
    Args:
        input_path: Local file path or existing gs:// URI
        bucket_name: Target bucket name. If None, uses GCS_TEST_BUCKET from environment
        user_session_id: User session identifier (username-UID format)
        username: Username for session structure (defaults to environment)
        blob_prefix: Subdirectory within user session (uploads, artifacts, etc.)
        force_upload: If True, upload even if input is already a gs:// URI
        
    Returns:
        GCS URI (gs://bucket/{username-UID}/{blob_prefix}/filename) ready for processing
        
    Raises:
        DocAIError: If staging fails
        ValueError: If input validation fails
    """
    try:
        # Handle existing GCS URIs
        if input_path.startswith('gs://') and not force_upload:
            logger.info(f"Input is already a GCS URI, passing through: {input_path}")
            return input_path
        
        # Validate local file if not GCS URI
        if not input_path.startswith('gs://'):
            local_file = Path(input_path)
            if not local_file.exists():
                raise ValueError(f"Local file not found: {input_path}")
            
            if not local_file.is_file():
                raise ValueError(f"Path is not a file: {input_path}")
            
            # Check file extension
            if local_file.suffix.lower() != '.pdf':
                raise ValueError(f"Only PDF files are supported, got: {local_file.suffix}")
        
        # Determine bucket name
        if not bucket_name:
            bucket_name = os.getenv('GCS_TEST_BUCKET', '').replace('gs://', '').rstrip('/')
            if not bucket_name:
                raise ValueError("No bucket specified and GCS_TEST_BUCKET not set in environment")
        
        # Clean bucket name if it includes gs:// prefix
        bucket_name = bucket_name.replace('gs://', '').rstrip('/')
        
        # Get or create user session ID
        if not user_session_id:
            if not username:
                username = get_username_from_env()
            
            # Generate UID from filename if not provided
            from .project_utils import generate_user_uid
            if input_path.startswith('gs://'):
                original_filename = input_path.split('/')[-1]
            else:
                original_filename = Path(input_path).name
            
            uid = generate_user_uid(original_filename)
            user_session_id = f"{username}-{uid}"
        
        # Get GCS paths using user session structure
        gcs_paths = get_gcs_paths(bucket_name, user_session_id)
        
        # Generate blob name using user session structure
        if input_path.startswith('gs://'):
            original_filename = input_path.split('/')[-1]
        else:
            original_filename = Path(input_path).name
        
        # Use user session structure: {username-UID}/{blob_prefix}/filename
        blob_name = f"{user_session_id}/{blob_prefix}/{original_filename}"
        
        logger.info(
            f"Starting document staging to GCS with user session structure: {input_path} -> {bucket_name}/{blob_name}"
        )
        logger.info(f"User session: {user_session_id}, blob prefix: {blob_prefix}")
        
        # Create DocAI client for GCS operations
        docai_client = DocAIClient(
            project_id=os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
            location=os.getenv('DOCAI_LOCATION', 'us'),
            credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )
        
        # Stage the file
        if input_path.startswith('gs://'):
            # Download from source GCS and re-upload to staging bucket with new structure
            logger.info(f"Re-staging GCS file to user session structure: {input_path}")
            
            # Download content
            content = docai_client.download_from_gcs(input_path)
            
            # Write to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Upload temporary file
                gcs_uri = docai_client.stage_to_gcs(temp_path, bucket_name, blob_name)
            finally:
                # Clean up temporary file
                Path(temp_path).unlink(missing_ok=True)
        else:
            # Upload local file directly
            gcs_uri = docai_client.stage_to_gcs(input_path, bucket_name, blob_name)
        
        logger.info(
            f"Document staging completed successfully: {input_path} -> {gcs_uri}"
        )
        logger.info(f"User session structure: bucket={bucket_name}, session={user_session_id}, prefix={blob_prefix}")
        
        return gcs_uri
        
    except DocAIError:
        raise
    except Exception as e:
        logger.error(f"Document staging failed: {input_path}, error: {str(e)}")
        raise DocAIError(f"Failed to stage document: {e}")


def get_staging_bucket_name() -> str:
    """
    Get the staging bucket name from environment configuration.
    
    Returns:
        Bucket name (without gs:// prefix)
        
    Raises:
        ValueError: If no bucket is configured
    """
    bucket = os.getenv('GCS_TEST_BUCKET', '').replace('gs://', '').rstrip('/')
    if not bucket:
        raise ValueError("GCS_TEST_BUCKET not configured in environment")
    return bucket


def is_gcs_uri(path: str) -> bool:
    """
    Check if a path is a GCS URI.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a GCS URI (starts with gs://)
    """
    return isinstance(path, str) and path.startswith('gs://')