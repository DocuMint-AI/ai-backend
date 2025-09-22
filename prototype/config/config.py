"""
Configuration management for the AI Backend system.

This module provides centralized configuration handling for environment variables
and application settings.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .exceptions import ConfigurationError


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    # Placeholder for future database settings
    pass


@dataclass
class OCRConfig:
    """OCR service configuration settings."""
    google_project_id: Optional[str]
    google_credentials_path: Optional[str]
    language_hints: List[str]
    confidence_threshold: float
    max_file_size_mb: int


@dataclass
class DocAIConfig:
    """Document AI configuration settings."""
    google_project_id: Optional[str]
    google_credentials_path: Optional[str]
    location: str
    processor_id: Optional[str]
    confidence_threshold: float


@dataclass
class ProcessingConfig:
    """Document processing configuration settings."""
    data_root: str
    image_format: str
    image_dpi: int
    max_file_size_mb: int


@dataclass
class AppConfig:
    """Main application configuration."""
    ocr: OCRConfig
    docai: DocAIConfig
    processing: ProcessingConfig
    debug: bool
    log_level: str


def load_config() -> AppConfig:
    """
    Load configuration from environment variables.
    
    Returns:
        AppConfig: Loaded configuration
        
    Raises:
        ConfigurationError: If required configuration is missing
    """
    try:
        # OCR Configuration
        ocr_config = OCRConfig(
            google_project_id=os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
            google_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            language_hints=os.getenv("LANGUAGE_HINTS", "en").split(","),
            confidence_threshold=float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.7")),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        )
        
        # DocAI Configuration  
        docai_config = DocAIConfig(
            google_project_id=os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
            google_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            location=os.getenv("DOCAI_LOCATION", "us"),
            processor_id=os.getenv("DOCAI_PROCESSOR_ID"),
            confidence_threshold=float(os.getenv("DOCAI_CONFIDENCE_THRESHOLD", "0.7"))
        )
        
        # Processing Configuration
        processing_config = ProcessingConfig(
            data_root=os.getenv("DATA_ROOT", "/data"),
            image_format=os.getenv("IMAGE_FORMAT", "PNG"),
            image_dpi=int(os.getenv("IMAGE_DPI", "300")),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        )
        
        # Main app configuration
        config = AppConfig(
            ocr=ocr_config,
            docai=docai_config,
            processing=processing_config,
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper()
        )
        
        return config
        
    except (ValueError, TypeError) as e:
        raise ConfigurationError(f"Invalid configuration: {e}")


def validate_config(config: AppConfig) -> List[str]:
    """
    Validate configuration and return list of issues.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of validation error messages
    """
    issues = []
    
    # Check OCR configuration
    if not config.ocr.google_project_id:
        issues.append("Missing GOOGLE_CLOUD_PROJECT_ID for OCR")
    
    if not config.ocr.google_credentials_path:
        issues.append("Missing GOOGLE_APPLICATION_CREDENTIALS for OCR")
    elif not Path(config.ocr.google_credentials_path).exists():
        issues.append(f"Google credentials file not found: {config.ocr.google_credentials_path}")
    
    # Check processing configuration
    if not Path(config.processing.data_root).exists():
        issues.append(f"Data root directory not found: {config.processing.data_root}")
    
    # Check DocAI configuration
    if config.docai.processor_id and not config.docai.google_project_id:
        issues.append("DocAI processor ID specified but missing Google project ID")
    
    return issues


# Global configuration instance (loaded lazily)
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the global configuration instance.
    
    Returns:
        AppConfig: Global configuration
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> AppConfig:
    """
    Force reload of configuration from environment.
    
    Returns:
        AppConfig: Reloaded configuration
    """
    global _config
    _config = load_config()
    return _config