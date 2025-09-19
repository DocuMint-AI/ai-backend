"""
Services package for the AI Backend document processing system.

This package contains core services for document processing, OCR, and utilities.
"""

from .exceptions import (
    AIBackendError,
    PDFProcessingError,
    OCRProcessingError,
    DocumentParsingError,
    FileValidationError,
    ConfigurationError,
    ServiceInitializationError,
    AuthenticationError,
    ProcessingTimeoutError
)

__all__ = [
    'AIBackendError',
    'PDFProcessingError', 
    'OCRProcessingError',
    'DocumentParsingError',
    'FileValidationError',
    'ConfigurationError',
    'ServiceInitializationError',
    'AuthenticationError',
    'ProcessingTimeoutError'
]