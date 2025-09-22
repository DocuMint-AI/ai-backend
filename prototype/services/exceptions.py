"""
Custom exceptions for the AI Backend system.
"""


class PDFProcessingError(Exception):
    """Raised when PDF processing fails."""
    pass


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class OCRProcessingError(Exception):
    """Raised when OCR processing fails."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ClassificationError(Exception):
    """Raised when document classification fails."""
    pass