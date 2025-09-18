"""
DocAI integration package for Google Document AI processing.

This package provides components for integrating Google Document AI
into the AI Backend document processing pipeline.
"""

from .schema import (
    ParsedDocument,
    Clause,
    NamedEntity,
    CrossReference,
    KeyValuePair,
    DocumentMetadata,
    ParseRequest,
    ParseResponse
)

from .client import DocAIClient
from .parser import DocumentParser

__all__ = [
    "ParsedDocument",
    "Clause", 
    "NamedEntity",
    "CrossReference",
    "KeyValuePair",
    "DocumentMetadata",
    "ParseRequest",
    "ParseResponse",
    "DocAIClient",
    "DocumentParser"
]