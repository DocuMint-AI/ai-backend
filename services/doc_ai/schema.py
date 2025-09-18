"""
Pydantic schema models for DocAI integration.

This module defines the data structures used for Google Document AI
processing, including parsed documents, entities, clauses, and metadata.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class EntityType(str, Enum):
    """Enumeration of supported named entity types."""
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    DATE = "DATE"
    MONEY = "MONEY"
    LOCATION = "LOCATION"
    JURISDICTION = "JURISDICTION"
    CONTRACT_PARTY = "CONTRACT_PARTY"
    OBLIGATION = "OBLIGATION"
    PENALTY = "PENALTY"
    DURATION = "DURATION"
    OTHER = "OTHER"


class ClauseType(str, Enum):
    """Enumeration of document clause types."""
    TERMINATION = "TERMINATION"
    PAYMENT = "PAYMENT"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    LIABILITY = "LIABILITY"
    GOVERNING_LAW = "GOVERNING_LAW"
    DISPUTE_RESOLUTION = "DISPUTE_RESOLUTION"
    FORCE_MAJEURE = "FORCE_MAJEURE"
    INDEMNIFICATION = "INDEMNIFICATION"
    INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY"
    WARRANTY = "WARRANTY"
    OTHER = "OTHER"


class TextSpan(BaseModel):
    """Text span with start and end offsets."""
    start_offset: int = Field(..., description="Start character offset in document")
    end_offset: int = Field(..., description="End character offset in document")
    text: str = Field(..., description="Extracted text content")


class BoundingBox(BaseModel):
    """Bounding box coordinates for visual elements."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate") 
    width: float = Field(..., description="Width dimension")
    height: float = Field(..., description="Height dimension")


class Clause(BaseModel):
    """Represents a legal or contractual clause in the document."""
    id: str = Field(..., description="Unique clause identifier")
    type: ClauseType = Field(..., description="Classification of the clause")
    text_span: TextSpan = Field(..., description="Text span in document")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    page_number: int = Field(..., description="Page number where clause appears")
    bounding_box: Optional[BoundingBox] = Field(None, description="Visual location")
    sub_clauses: List['Clause'] = Field(default_factory=list, description="Nested sub-clauses")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class NamedEntity(BaseModel):
    """Represents a named entity extracted from the document."""
    id: str = Field(..., description="Unique entity identifier")
    type: EntityType = Field(..., description="Entity classification")
    text_span: TextSpan = Field(..., description="Text span in document")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    normalized_value: Optional[str] = Field(None, description="Normalized entity value")
    page_number: int = Field(..., description="Page number where entity appears")
    bounding_box: Optional[BoundingBox] = Field(None, description="Visual location")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('normalized_value', pre=True, always=True)
    def normalize_entity_value(cls, v, values):
        """Normalize entity values based on type."""
        if not v:
            return v
        
        entity_type = values.get('type')
        text = values.get('text_span', {}).get('text', v)
        
        if entity_type == EntityType.DATE:
            # Attempt to normalize dates to ISO8601
            try:
                # This is a simplified example - you'd want more robust date parsing
                from dateutil import parser
                parsed_date = parser.parse(text)
                return parsed_date.isoformat()
            except:
                return v
        elif entity_type == EntityType.MONEY:
            # Normalize currency to ISO codes
            # This is a simplified example
            if 'USD' in text or '$' in text:
                return f"USD:{v}"
            elif 'EUR' in text or '€' in text:
                return f"EUR:{v}"
            return v
        
        return v


class CrossReference(BaseModel):
    """Represents a cross-reference between document elements."""
    id: str = Field(..., description="Unique cross-reference identifier")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    reference_type: str = Field(..., description="Type of reference relationship")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class KeyValuePair(BaseModel):
    """Represents a key-value pair extracted from the document."""
    id: str = Field(..., description="Unique key-value pair identifier")
    key: TextSpan = Field(..., description="Key text span")
    value: TextSpan = Field(..., description="Value text span")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    page_number: int = Field(..., description="Page number where pair appears")
    key_bounding_box: Optional[BoundingBox] = Field(None, description="Key visual location")
    value_bounding_box: Optional[BoundingBox] = Field(None, description="Value visual location")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DocumentMetadata(BaseModel):
    """Metadata about the document and processing pipeline."""
    document_id: str = Field(..., description="Unique document identifier")
    original_filename: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    page_count: int = Field(..., description="Number of pages")
    language: str = Field(..., description="Primary document language")
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processor_id: Optional[str] = Field(None, description="DocAI processor ID used")
    processor_version: Optional[str] = Field(None, description="DocAI processor version")
    confidence_threshold: float = Field(0.7, description="Confidence threshold applied")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class ParsedDocument(BaseModel):
    """Complete parsed document with all extracted elements."""
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    full_text: str = Field(..., description="Complete document text")
    clauses: List[Clause] = Field(default_factory=list, description="Extracted clauses")
    named_entities: List[NamedEntity] = Field(default_factory=list, description="Named entities")
    key_value_pairs: List[KeyValuePair] = Field(default_factory=list, description="Key-value pairs")
    cross_references: List[CrossReference] = Field(default_factory=list, description="Cross-references")
    processing_warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    raw_docai_response: Optional[Dict[str, Any]] = Field(None, description="Raw DocAI response")

    @property
    def total_entities(self) -> int:
        """Get total number of entities."""
        return len(self.named_entities)

    @property
    def entity_confidence_avg(self) -> float:
        """Get average confidence of all entities."""
        if not self.named_entities:
            return 0.0
        return sum(entity.confidence for entity in self.named_entities) / len(self.named_entities)

    @property
    def clause_confidence_avg(self) -> float:
        """Get average confidence of all clauses."""
        if not self.clauses:
            return 0.0
        return sum(clause.confidence for clause in self.clauses) / len(self.clauses)


class ParseRequest(BaseModel):
    """Request model for document parsing."""
    gcs_uri: str = Field(..., description="Google Cloud Storage URI of the document")
    processor_id: Optional[str] = Field(None, description="Specific DocAI processor ID to use")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")
    enable_native_pdf_parsing: bool = Field(True, description="Enable native PDF parsing")
    include_raw_response: bool = Field(False, description="Include raw DocAI response in output")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('gcs_uri')
    def validate_gcs_uri(cls, v):
        """Validate GCS URI format."""
        if not v.startswith('gs://'):
            raise ValueError('GCS URI must start with gs://')
        return v


class ParseResponse(BaseModel):
    """Response model for document parsing."""
    success: bool = Field(..., description="Whether parsing was successful")
    document: Optional[ParsedDocument] = Field(None, description="Parsed document")
    error_message: Optional[str] = Field(None, description="Error message if parsing failed")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")
    request_id: str = Field(..., description="Unique request identifier")
    
    @validator('document', pre=True, always=True)
    def validate_document_on_success(cls, v, values):
        """Ensure document is present when success is True."""
        success = values.get('success', False)
        if success and not v:
            raise ValueError('Document must be provided when success is True')
        if not success and v:
            raise ValueError('Document should not be provided when success is False')
        return v


# Allow forward references
Clause.model_rebuild()