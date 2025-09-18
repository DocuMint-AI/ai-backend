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
    ParseResponse,
    EntityType,
    ClauseType,
    TextSpan,
    BoundingBox
)

from .client import DocAIClient, DocAIError, DocAIAuthenticationError, DocAIProcessingError
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
    "EntityType",
    "ClauseType", 
    "TextSpan",
    "BoundingBox",
    "DocAIClient",
    "DocAIError",
    "DocAIAuthenticationError",
    "DocAIProcessingError",
    "DocumentParser"
]