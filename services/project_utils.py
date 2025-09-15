"""
Project utilities for path handling and configuration.
Provides functions to work with relative paths from project root.
"""

import os
from pathlib import Path
from typing import Union


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