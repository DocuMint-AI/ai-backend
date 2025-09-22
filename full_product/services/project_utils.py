"""
Project utilities for path handling and configuration.
Provides functions to work with relative paths from project root.
"""

import os
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Union, Tuple, Optional


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path: Absolute path to project root
    """
    # Find project root by looking for requirements.txt or setup.py
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists() or (parent / "setup.py").exists():
            return parent
    
    # Fallback: assume this file is in services/ and go up two levels
    return current_path.parent.parent


def get_data_dir() -> Path:
    """
    Get the data directory path.
    
    Returns:
        Path: Absolute path to data directory
    """
    return get_project_root() / "data"


def get_credentials_path() -> Path:
    """
    Get the Google Cloud credentials path.
    
    Returns:
        Path: Absolute path to credentials file
    """
    return get_data_dir() / ".cheetah" / "gcloud" / "vision-credentials.json"


def resolve_path(path: Union[str, Path], relative_to_project: bool = True) -> Path:
    """
    Resolve a path, optionally relative to project root.
    
    Args:
        path: Path to resolve (can be relative or absolute)
        relative_to_project: If True and path is relative, resolve relative to project root
        
    Returns:
        Path: Resolved absolute path
    """
    path = Path(path)
    
    if path.is_absolute():
        return path
    
    if relative_to_project:
        return get_project_root() / path
    else:
        return Path.cwd() / path


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure
        
    Returns:
        Path: Absolute path to the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


# Initialize project paths
PROJECT_ROOT = get_project_root()
DATA_DIR = get_data_dir()
CREDENTIALS_PATH = get_credentials_path()

# Ensure data directories exist
ensure_dir(DATA_DIR)
ensure_dir(DATA_DIR / "uploads")
ensure_dir(DATA_DIR / "processed")
ensure_dir(DATA_DIR / ".cheetah" / "gcloud")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for use in paths and UIDs.
    
    Args:
        filename: Original filename to sanitize
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove file extension
    name = Path(filename).stem
    
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[^\w\-_.]', '_', name)
    
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "document"
    
    return sanitized


def generate_user_uid(pdf_filename: str, timestamp: Optional[str] = None) -> str:
    """
    Generate a unique identifier from PDF filename and timestamp.
    
    Args:
        pdf_filename: Original PDF filename
        timestamp: Optional timestamp string (defaults to current time)
        
    Returns:
        Unique identifier in format: sanitized_filename_YYYYMMDD_HHMMSS_hash
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sanitize filename
    sanitized_name = sanitize_filename(pdf_filename)
    
    # Create a short hash for uniqueness
    hash_input = f"{pdf_filename}_{timestamp}_{os.getpid()}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    return f"{sanitized_name}_{timestamp}_{short_hash}"


def get_username_from_env() -> str:
    """
    Get username from environment variable.
    
    Returns:
        Username from environment, defaults to 'default_user'
    """
    return os.getenv("USERNAME", os.getenv("USER", "default_user"))


def resolve_user_session_paths(pdf_filename: str, username: Optional[str] = None, 
                             uid: Optional[str] = None) -> Tuple[str, Path]:
    """
    Resolve consistent local and GCS paths for user session storage.
    
    Args:
        pdf_filename: Original PDF filename
        username: Username (defaults to environment variable)
        uid: User session UID (generated if not provided)
        
    Returns:
        Tuple of (username-UID string, local base path)
    """
    if username is None:
        username = get_username_from_env()
    
    if uid is None:
        uid = generate_user_uid(pdf_filename)
    
    # Create username-UID identifier
    user_session_id = f"{username}-{uid}"
    
    # Create local base path
    local_base = get_data_dir() / "processed" / user_session_id
    
    return user_session_id, local_base


def get_user_session_structure(pdf_filename: str, username: Optional[str] = None,
                             uid: Optional[str] = None) -> dict:
    """
    Get complete user session directory structure.
    
    Args:
        pdf_filename: Original PDF filename
        username: Username (defaults to environment variable) 
        uid: User session UID (generated if not provided)
        
    Returns:
        Dictionary with all session paths
    """
    user_session_id, base_path = resolve_user_session_paths(pdf_filename, username, uid)
    
    # Define directory structure
    structure = {
        "user_session_id": user_session_id,
        "base_path": base_path,
        "artifacts": base_path / "artifacts",
        "uploads": base_path / "uploads", 
        "pipeline": base_path / "pipeline",
        "metadata": base_path / "metadata",
        "diagnostics": base_path / "diagnostics"
    }
    
    # Ensure all directories exist
    for path in structure.values():
        if isinstance(path, Path):
            ensure_dir(path)
    
    return structure


def get_gcs_paths(bucket_name: str, user_session_id: str) -> dict:
    """
    Get GCS path structure for user session.
    
    Args:
        bucket_name: GCS bucket name
        user_session_id: User session identifier (username-UID)
        
    Returns:
        Dictionary with GCS paths
    """
    base_uri = f"gs://{bucket_name}/{user_session_id}"
    
    return {
        "base_uri": base_uri,
        "uploads": f"{base_uri}/uploads",
        "embeddings": f"{base_uri}/embeddings", 
        "artifacts": f"{base_uri}/artifacts",
        "pipeline": f"{base_uri}/pipeline",
        "metadata": f"{base_uri}/metadata"
    }


def resolve_legacy_path_to_new_structure(legacy_path: str, user_session_id: str) -> Path:
    """
    Convert legacy file paths to new user session structure.
    
    Args:
        legacy_path: Old path (e.g., "data/processed/file.json")
        user_session_id: User session identifier
        
    Returns:
        New path under user session structure
    """
    legacy_path = Path(legacy_path)
    
    # Determine target subdirectory based on filename patterns
    filename = legacy_path.name
    
    if "pipeline_result" in filename:
        subdir = "pipeline"
    elif "mvp" in str(legacy_path) or "diagnostic" in filename:
        subdir = "artifacts"
    elif "metadata" in filename:
        subdir = "metadata"
    elif "embedding" in filename:
        subdir = "embeddings"
    else:
        subdir = "artifacts"  # Default fallback
    
    # Construct new path
    base_path = get_data_dir() / "processed" / user_session_id
    new_path = base_path / subdir / filename
    
    return new_path