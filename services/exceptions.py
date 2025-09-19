"""
Custom exceptions for the AI Backend document processing system.

This module defines custom exception classes used throughout the application
for better error handling and debugging.
"""

from typing import Optional, Dict, Any


class AIBackendError(Exception):
    """Base exception for all AI Backend errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PDFProcessingError(AIBackendError):
    """Raised when PDF processing fails."""
    pass


class OCRProcessingError(AIBackendError):
    """Raised when OCR processing fails."""
    pass


class DocumentParsingError(AIBackendError):
    """Raised when document parsing fails."""
    pass


class FileValidationError(AIBackendError):
    """Raised when file validation fails."""
    pass


class ConfigurationError(AIBackendError):
    """Raised when configuration is invalid or missing."""
    pass


class ServiceInitializationError(AIBackendError):
    """Raised when service initialization fails."""
    pass


class AuthenticationError(AIBackendError):
    """Raised when authentication fails."""
    pass


class ProcessingTimeoutError(AIBackendError):
    """Raised when processing takes too long."""
    pass