"""
Document parser for transforming DocAI output into normalized schema.

This module converts raw Google Document AI responses into our
standardized schema format with proper entity normalization and fallback extraction.
"""

import re
import uuid
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import structlog
from decimal import Decimal

from google.cloud import documentai
from dateutil import parser as date_parser

from .schema import (
    ParsedDocument,
    Clause,
    NamedEntity,
    CrossReference, 
    KeyValuePair,
    DocumentMetadata,
    EntityType,
    ClauseType,
    TextSpan,
    BoundingBox
)
from ..text_utils import normalize_text, normalize_for_comparison
from ..feature_emitter import emit_feature_vector
from ..regex_fallback import run_fallback_kvs, validate_mandatory_kvs

# Import text normalization utilities
from ..text_utils import normalize_text, normalize_for_comparison


logger = structlog.get_logger(__name__)


class DocumentParser:
    """
    Transforms raw DocAI responses into normalized ParsedDocument schema.
    
    Handles entity normalization, clause detection, cross-reference extraction,
    and confidence scoring.
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize document parser.
        
        Args:
            confidence_threshold: Minimum confidence threshold for entities
        """
        self.confidence_threshold = confidence_threshold
        
        # Entity type mappings from DocAI to our schema
        self.entity_type_mapping = {
            'PERSON': EntityType.PERSON,
            'ORGANIZATION': EntityType.ORGANIZATION,
            'DATE': EntityType.DATE,
            'MONEY': EntityType.MONEY,
            'LOCATION': EntityType.LOCATION,
            'CONTRACT_PARTY': EntityType.CONTRACT_PARTY,
            'OBLIGATION': EntityType.OBLIGATION,
            'PENALTY': EntityType.PENALTY,
            'DURATION': EntityType.DURATION,
            'JURISDICTION': EntityType.JURISDICTION
        }
        
        # Clause detection patterns (simplified)
        self.clause_patterns = {
            ClauseType.TERMINATION: [
                r'terminat\w+',
                r'expir\w+',
                r'end of (?:this )?(?:agreement|contract)',
                r'dissolv\w+'
            ],
            ClauseType.PAYMENT: [
                r'payment\s+(?:terms|due|schedule)',
                r'invoice\w*',
                r'compensation',
                r'remuneration'
            ],
            ClauseType.CONFIDENTIALITY: [
                r'confidential\w*',
                r'non-disclosure',
                r'proprietary information',
                r'trade secret\w*'
            ],
            ClauseType.LIABILITY: [
                r'liabilit\w+',
                r'damages',
                r'indemnif\w+',
                r'limitation of liability'
            ],
            ClauseType.GOVERNING_LAW: [
                r'governing law',
                r'applicable law',
                r'jurisdiction',
                r'venue'
            ],
            ClauseType.DISPUTE_RESOLUTION: [
                r'dispute resolution',
                r'arbitration',
                r'mediation',
                r'litigation'
            ]
        }
        
        logger.info("Document parser initialized", confidence_threshold=confidence_threshold)
    
    def parse_document(
        self,
        docai_document: documentai.Document,
        metadata: DocumentMetadata,
        include_raw_response: bool = False
    ) -> ParsedDocument:
        """
        Parse DocAI document into normalized schema.
        
        Args:
            docai_document: Raw DocAI document response
            metadata: Document metadata
            include_raw_response: Whether to include raw DocAI response
            
        Returns:
            Parsed document in normalized schema
        """
        try:
            logger.info("Starting document parsing", document_id=metadata.document_id)
            
            # Extract and normalize full text
            raw_full_text = self._extract_full_text(docai_document)
            full_text = normalize_text(raw_full_text)
            
            # Extract entities
            named_entities = self._extract_entities(docai_document, full_text)
            
            # Extract key-value pairs  
            key_value_pairs = self._extract_key_value_pairs(docai_document, full_text)
            
            # Detect clauses
            clauses = self._detect_clauses(docai_document, full_text)
            
            # Run fallback extraction if DocAI results are insufficient
            needs_review = self._check_needs_review(named_entities, key_value_pairs, clauses, full_text)
            
            if needs_review:
                logger.info("Running fallback extraction due to insufficient DocAI results")
                
                # Use enhanced fallback extractor for better coverage
                enhanced_fallback = run_fallback_kvs(normalize_text(full_text))
                fallback_kvs_dict = enhanced_fallback.get("extracted_kvs", {})
                
                # Convert fallback results to schema-compatible KVs
                for field_name, field_extractions in fallback_kvs_dict.items():
                    for extraction in field_extractions:
                        if extraction.get("value"):
                            # Create schema-compatible KeyValuePair (simplified)
                            try:
                                kv_dict = {
                                    "id": f"fallback_{field_name}_{len(key_value_pairs)}",
                                    "key": {"text": field_name.replace("_", " ").title()},
                                    "value": {"text": extraction["normalized_value"]},
                                    "confidence": extraction.get("confidence", 0.8),
                                    "source": extraction.get("source", "fallback_regex")
                                }
                                # Note: In production, convert to proper KeyValuePair objects
                                # For MVP, store as dict for JSON serialization
                                key_value_pairs.append(kv_dict)
                            except Exception as e:
                                logger.warning(f"Failed to convert fallback KV {field_name}: {e}")
                
                # Also run original fallback for schema objects
                fallback_entities, fallback_kvs_schema, fallback_clauses = self._run_fallback_extraction_for_schema(full_text)
                
                # Merge original fallback results
                named_entities.extend(fallback_entities)
                clauses.extend(fallback_clauses)
                
                # Re-check needs_review after enhanced fallback
                enhanced_mandatory = enhanced_fallback.get("mandatory_found", 0)
                if enhanced_mandatory >= 2:
                    needs_review = False
                    logger.info(f"Enhanced fallback found {enhanced_mandatory} mandatory fields - document review not needed")
            
            # Extract cross-references
            cross_references = self._extract_cross_references(named_entities)
            
            # Collect warnings
            warnings = self._collect_warnings(docai_document, named_entities, clauses)
            
            # Create parsed document
            parsed_doc = ParsedDocument(
                metadata=metadata,
                full_text=full_text,
                clauses=clauses,
                named_entities=named_entities,
                key_value_pairs=key_value_pairs,
                cross_references=cross_references,
                processing_warnings=warnings,
                raw_docai_response=self._serialize_docai_response(docai_document) if include_raw_response else None
            )
            
            # Add normalized text to metadata for consistency
            parsed_doc.metadata.normalized_text = normalize_text(full_text)
            
            # Add needs_review flag to metadata
            if needs_review:
                parsed_doc.metadata.needs_review = True
                logger.info("Document marked for review due to low extraction confidence")
            
            logger.info(
                "Document parsing completed",
                document_id=metadata.document_id,
                entities=len(named_entities),
                clauses=len(clauses),
                key_value_pairs=len(key_value_pairs),
                cross_references=len(cross_references),
                warnings=len(warnings)
            )
            
            # Generate feature vector for ML/Vertex integration
            try:
                parsed_dict = parsed_doc.dict()
                feature_output_path = Path("artifacts") / "vision_to_docai" / "feature_vector.json"
                emit_feature_vector(parsed_dict, str(feature_output_path))
                
                # Generate diagnostics summary
                self._generate_diagnostics_summary(parsed_dict, full_text)
                
            except Exception as e:
                logger.warning("Failed to generate feature vector or diagnostics", error=str(e))
            
            return parsed_doc
            
        except Exception as e:
            logger.error("Document parsing failed", error=str(e))
            raise
    
    def _extract_full_text(self, document: documentai.Document) -> str:
        """Extract complete document text."""
        try:
            if document.text:
                return document.text
            
            # Fallback: concatenate text from pages
            text_parts = []
            for page in document.pages:
                for paragraph in page.paragraphs:
                    paragraph_text = self._get_text_from_layout(paragraph.layout, document.text)
                    text_parts.append(paragraph_text)
                    text_parts.append('\n')
            
            return ''.join(text_parts)
            
        except Exception as e:
            logger.warning("Failed to extract full text", error=str(e))
            return ""
    
    def _extract_entities(self, document: documentai.Document, full_text: str) -> List[NamedEntity]:
        """Extract and normalize named entities."""
        entities = []
        entity_id_counter = 1
        
        try:
            for entity in document.entities:
                # Map entity type
                entity_type = self.entity_type_mapping.get(
                    entity.type_.upper(),
                    EntityType.OTHER
                )
                
                # Get confidence
                confidence = entity.confidence if hasattr(entity, 'confidence') else 0.8
                
                # Skip low confidence entities
                if confidence < self.confidence_threshold:
                    continue
                
                # Get text span
                text_span = self._get_text_span_from_layout(entity.mention_text, full_text)
                if not text_span:
                    continue
                
                # Get page number
                page_number = self._get_page_number_from_layout(entity.page_anchor)
                
                # Get bounding box
                bounding_box = self._get_bounding_box_from_layout(entity.page_anchor)
                
                # Normalize entity value
                normalized_value = self._normalize_entity_value(entity_type, text_span.text)
                
                named_entity = NamedEntity(
                    id=f"entity_{entity_id_counter:04d}",
                    type=entity_type,
                    text_span=text_span,
                    confidence=confidence,
                    normalized_value=normalized_value,
                    page_number=page_number,
                    bounding_box=bounding_box,
                    metadata={
                        'docai_type': entity.type_,
                        'docai_confidence': confidence
                    }
                )
                
                entities.append(named_entity)
                entity_id_counter += 1
            
            logger.debug("Extracted entities", count=len(entities))
            return entities
            
        except Exception as e:
            logger.warning("Failed to extract entities", error=str(e))
            return []
    
    def _extract_key_value_pairs(self, document: documentai.Document, full_text: str) -> List[KeyValuePair]:
        """Extract key-value pairs from form fields."""
        pairs = []
        pair_id_counter = 1
        
        try:
            for page in document.pages:
                if not hasattr(page, 'form_fields'):
                    continue
                
                for field in page.form_fields:
                    # Extract key
                    key_text = self._get_text_from_layout(field.field_name, document.text)
                    key_span = self._create_text_span(key_text, full_text)
                    
                    # Extract value
                    value_text = self._get_text_from_layout(field.field_value, document.text)
                    value_span = self._create_text_span(value_text, full_text)
                    
                    if not key_span or not value_span:
                        continue
                    
                    # Get confidence
                    confidence = getattr(field.field_name, 'confidence', 0.8)
                    
                    # Skip low confidence pairs
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Get page number
                    page_number = page.page_number if hasattr(page, 'page_number') else 1
                    
                    pair = KeyValuePair(
                        id=f"kvp_{pair_id_counter:04d}",
                        key=key_span,
                        value=value_span,
                        confidence=confidence,
                        page_number=page_number,
                        metadata={'docai_confidence': confidence}
                    )
                    
                    pairs.append(pair)
                    pair_id_counter += 1
            
            logger.debug("Extracted key-value pairs", count=len(pairs))
            return pairs
            
        except Exception as e:
            logger.warning("Failed to extract key-value pairs", error=str(e))
            return []
    
    def _detect_clauses(self, document: documentai.Document, full_text: str) -> List[Clause]:
        """Detect clauses using pattern matching."""
        clauses = []
        clause_id_counter = 1
        
        try:
            # Split text into paragraphs for clause detection
            paragraphs = full_text.split('\n\n')
            current_offset = 0
            
            for paragraph in paragraphs:
                if len(paragraph.strip()) < 50:  # Skip short paragraphs
                    current_offset += len(paragraph) + 2  # +2 for \n\n
                    continue
                
                # Check for clause patterns
                clause_type = self._classify_clause(paragraph)
                if clause_type:
                    # Create text span
                    start_offset = current_offset
                    end_offset = current_offset + len(paragraph)
                    
                    text_span = TextSpan(
                        start_offset=start_offset,
                        end_offset=end_offset,
                        text=paragraph.strip()
                    )
                    
                    # Estimate confidence based on pattern matches
                    confidence = self._calculate_clause_confidence(paragraph, clause_type)
                    
                    if confidence >= self.confidence_threshold:
                        clause = Clause(
                            id=f"clause_{clause_id_counter:04d}",
                            type=clause_type,
                            text_span=text_span,
                            confidence=confidence,
                            page_number=1,  # Would calculate from text offset
                            metadata={
                                'detection_method': 'pattern_matching',
                                'paragraph_index': len(clauses)
                            }
                        )
                        
                        clauses.append(clause)
                        clause_id_counter += 1
                
                current_offset += len(paragraph) + 2  # +2 for \n\n
            
            logger.debug("Detected clauses", count=len(clauses))
            return clauses
            
        except Exception as e:
            logger.warning("Failed to detect clauses", error=str(e))
            return []
    
    def _extract_cross_references(self, entities: List[NamedEntity]) -> List[CrossReference]:
        """Extract cross-references between entities."""
        cross_references = []
        ref_id_counter = 1
        
        try:
            # Simple cross-reference detection based on entity proximity and types
            for i, entity1 in enumerate(entities):
                for j, entity2 in enumerate(entities[i+1:], i+1):
                    # Check if entities are related
                    if self._are_entities_related(entity1, entity2):
                        cross_ref = CrossReference(
                            id=f"ref_{ref_id_counter:04d}",
                            source_entity_id=entity1.id,
                            target_entity_id=entity2.id,
                            reference_type=self._determine_reference_type(entity1, entity2),
                            confidence=min(entity1.confidence, entity2.confidence),
                            metadata={
                                'detection_method': 'proximity_based',
                                'distance': abs(entity1.text_span.start_offset - entity2.text_span.start_offset)
                            }
                        )
                        
                        cross_references.append(cross_ref)
                        ref_id_counter += 1
            
            logger.debug("Extracted cross-references", count=len(cross_references))
            return cross_references
            
        except Exception as e:
            logger.warning("Failed to extract cross-references", error=str(e))
            return []
    
    def _collect_warnings(
        self,
        document: documentai.Document,
        entities: List[NamedEntity],
        clauses: List[Clause]
    ) -> List[str]:
        """Collect processing warnings."""
        warnings = []
        
        # Check for low confidence entities
        low_conf_entities = [e for e in entities if e.confidence < 0.8]
        if low_conf_entities:
            warnings.append(f"{len(low_conf_entities)} entities have confidence below 0.8")
        
        # Check for low confidence clauses
        low_conf_clauses = [c for c in clauses if c.confidence < 0.8]
        if low_conf_clauses:
            warnings.append(f"{len(low_conf_clauses)} clauses have confidence below 0.8")
        
        # Check document quality
        if hasattr(document, 'pages') and document.pages:
            total_confidence = sum(
                getattr(page, 'confidence', 0.9) for page in document.pages
            ) / len(document.pages)
            
            if total_confidence < 0.8:
                warnings.append(f"Document OCR quality is low (avg confidence: {total_confidence:.2f})")
        
        return warnings
    
    # Helper methods
    
    def _get_text_span_from_layout(self, mention_text: str, full_text: str) -> Optional[TextSpan]:
        """Create text span from mention text."""
        if not mention_text or not full_text:
            return None
        
        # Find text in full document
        start_offset = full_text.find(mention_text)
        if start_offset == -1:
            return None
        
        return TextSpan(
            start_offset=start_offset,
            end_offset=start_offset + len(mention_text),
            text=mention_text
        )
    
    def _create_text_span(self, text: str, full_text: str) -> Optional[TextSpan]:
        """Create text span by finding text in full document."""
        return self._get_text_span_from_layout(text, full_text)
    
    def _get_page_number_from_layout(self, page_anchor) -> int:
        """Extract page number from page anchor."""
        try:
            if hasattr(page_anchor, 'page_refs') and page_anchor.page_refs:
                return page_anchor.page_refs[0].page + 1  # Convert to 1-based
            return 1
        except:
            return 1
    
    def _get_bounding_box_from_layout(self, page_anchor) -> Optional[BoundingBox]:
        """Extract bounding box from page anchor."""
        try:
            if hasattr(page_anchor, 'page_refs') and page_anchor.page_refs:
                page_ref = page_anchor.page_refs[0]
                if hasattr(page_ref, 'bounding_box'):
                    bbox = page_ref.bounding_box
                    return BoundingBox(
                        x=bbox.left,
                        y=bbox.top,
                        width=bbox.right - bbox.left,
                        height=bbox.bottom - bbox.top
                    )
            return None
        except:
            return None
    
    def _get_text_from_layout(self, layout, document_text: str) -> str:
        """Extract text from layout object."""
        try:
            if hasattr(layout, 'text_anchor') and layout.text_anchor:
                segments = layout.text_anchor.text_segments
                if segments:
                    segment = segments[0]
                    start = segment.start_index
                    end = segment.end_index
                    return document_text[start:end] if document_text else ""
            return ""
        except:
            return ""
    
    def _normalize_entity_value(self, entity_type: EntityType, text: str) -> Optional[str]:
        """Normalize entity value based on type."""
        try:
            if entity_type == EntityType.DATE:
                # Parse and normalize dates to ISO8601
                parsed_date = date_parser.parse(text, fuzzy=True)
                return parsed_date.isoformat()
            
            elif entity_type == EntityType.MONEY:
                # Normalize currency values
                # Extract currency and amount
                if '$' in text:
                    return f"USD:{text}"
                elif '€' in text:
                    return f"EUR:{text}"
                elif '£' in text:
                    return f"GBP:{text}"
                return text
            
            return text
            
        except Exception:
            return text
    
    def _classify_clause(self, paragraph: str) -> Optional[ClauseType]:
        """Classify paragraph as a clause type."""
        paragraph_lower = paragraph.lower()
        
        for clause_type, patterns in self.clause_patterns.items():
            for pattern in patterns:
                if re.search(pattern, paragraph_lower):
                    return clause_type
        
        return None
    
    def _calculate_clause_confidence(self, paragraph: str, clause_type: ClauseType) -> float:
        """Calculate confidence score for clause classification."""
        paragraph_lower = paragraph.lower()
        patterns = self.clause_patterns.get(clause_type, [])
        
        matches = sum(1 for pattern in patterns if re.search(pattern, paragraph_lower))
        max_confidence = 0.95
        base_confidence = 0.7
        
        # More pattern matches = higher confidence
        confidence = base_confidence + (matches / len(patterns)) * (max_confidence - base_confidence)
    def _serialize_docai_response(self, document: documentai.Document) -> Dict[str, Any]:
        """Serialize DocAI document response to dictionary."""
        try:
            # Convert to JSON-serializable format
            # This is a simplified version - real implementation would handle all DocAI types
            return {
                'text': document.text,
                'pages': len(document.pages) if document.pages else 0,
                'entities': len(document.entities) if document.entities else 0,
                'mime_type': document.mime_type if hasattr(document, 'mime_type') else None
            }
        except Exception as e:
            logger.warning("Failed to serialize DocAI response", error=str(e))
            return {}
    
    def _check_needs_review(self, entities: List[NamedEntity], kvs: List[KeyValuePair], clauses: List[Clause], full_text: str = "") -> bool:
        """
        Enhanced check if document needs manual review based on extraction quality and fallback success.
        
        Args:
            entities: Extracted named entities
            kvs: Extracted key-value pairs
            clauses: Extracted clauses
            full_text: Full document text for fallback checking
            
        Returns:
            True if document needs review
        """
        # Check for minimum mandatory fields in extracted KVs
        mandatory_kv_types = ["policy_no", "date_of_commencement", "sum_assured", "dob"]
        
        found_mandatory = 0
        for kv in kvs:
            key_text = kv.key.text.lower() if hasattr(kv.key, 'text') else str(kv.key).lower()
            if any(mandatory in key_text for mandatory in mandatory_kv_types):
                found_mandatory += 1
        
        # Check fallback extraction for mandatory fields if DocAI failed
        if found_mandatory < 2 and full_text:  # Less than 2 mandatory fields found
            logger.info("Running enhanced fallback extraction for mandatory KVs")
            fallback_result = run_fallback_kvs(normalize_text(full_text))
            fallback_mandatory = fallback_result.get("mandatory_found", 0)
            
            # If fallback found mandatory fields, reduce review need
            if fallback_mandatory >= 2:
                logger.info(f"Enhanced fallback extraction found {fallback_mandatory} mandatory fields - reducing review need")
                return False
        
        # Check entity extraction quality
        high_confidence_entities = [e for e in entities if e.confidence > self.confidence_threshold]
        
        # Check clause coverage
        total_clause_length = sum(c.text_span.end_offset - c.text_span.start_offset for c in clauses)
        
        # Needs review if insufficient extraction
        needs_review = (
            len(entities) < 3 or  # Too few entities
            found_mandatory < 2 or  # Missing mandatory KVs
            len(clauses) < 3 or  # Too few clauses
            len(high_confidence_entities) < len(entities) * 0.7  # Low confidence
        )
        
        return needs_review
    
    def _run_fallback_extraction(self, full_text: str) -> Dict[str, Any]:
        """
        P3 Fix: Enhanced fallback extraction using regex patterns.
        Returns simple dict structure for testing - not schema objects.
        """
        logger.info("Running fallback extraction with regex patterns")
        
        patterns = {
            "policy_no": [
                r'Policy\s*No[:\s.]*([A-Za-z0-9\-/]+)',
                r'Policy\s*Number[:\s.]*([A-Za-z0-9\-/]+)'
            ],
            "date_of_commencement": [
                r'Date\s+of\s+Commencement\s+of\s+Policy[:\s.]*([0-9\-/\.]+)',
                r'Commencement\s+Date[:\s.]*([0-9\-/\.]+)'
            ],
            "sum_assured": [
                r'Sum\s+Assured\s+for\s+Basic\s+Plan[:\s.]*\(?\s*Rs\.?\s*\)?[:\s.]*([0-9,]+)',
                r'Sum\s+Assured[:\s.]*\(?\s*Rs\.?\s*\)?[:\s.]*([0-9,]+)'
            ],
            "dob": [
                r'Date\s+of\s+Birth[:\s.]*([0-9\-/\.]+)',
                r'DOB[:\s.]*([0-9\-/\.]+)'
            ],
            "nominee": [
                r'Nominee\s+under\s+section\s+39[^:]*?[:\s.]*([A-Za-z\s]+)',
                r'Nominee[:\s.]*([A-Za-z\s]+)'
            ]
        }
        
        # Simple extraction - return as plain dict for testing
        fallback_kv = {}
        policy_numbers = []
        
        for field, field_patterns in patterns.items():
            fallback_kv[field] = []
            for pattern in field_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                for match in matches:
                    if match.strip():
                        # Normalize the extracted value
                        normalized_value = self._normalize_kv_value(field, match.strip())
                        
                        fallback_kv[field].append({
                            "value": match.strip(),
                            "normalized_value": normalized_value,
                            "pattern": pattern,
                            "confidence": "regex_fallback",
                            "source": "fallback_regex"
                        })
                        
                        # Collect policy numbers separately
                        if field == "policy_no":
                            policy_numbers.append(normalized_value)
        
        return {
            "fallback_kv": fallback_kv,
            "policy_numbers": policy_numbers
        }
    
    def _classify_clause_type(self, heading: str, content: str) -> str:
        """Classify clause type based on heading and content."""
        heading_lower = heading.lower()
        content_lower = content.lower()
        
        # Map to valid ClauseType enum values
        if any(term in heading_lower for term in ['benefit', 'payout', 'death']):
            return 'OTHER'  # BENEFIT not in enum, use OTHER
        elif any(term in heading_lower for term in ['exclusion', 'exception', 'not covered']):
            return 'LIABILITY'  # Map exclusions to LIABILITY
        elif any(term in heading_lower for term in ['condition', 'term', 'requirement']):
            return 'OTHER'  # CONDITIONS not in enum
        elif any(term in heading_lower for term in ['definition', 'meaning']):
            return 'OTHER'  # DEFINITIONS not in enum
        elif any(term in heading_lower for term in ['premium', 'payment', 'fee']):
            return 'PAYMENT'  # Premium maps to PAYMENT
        elif any(term in heading_lower for term in ['termination', 'cancellation']):
            return 'TERMINATION'
        elif any(term in heading_lower for term in ['confidential', 'privacy']):
            return 'CONFIDENTIALITY'
        elif any(term in heading_lower for term in ['liability', 'responsible']):
            return 'LIABILITY'
        elif any(term in heading_lower for term in ['law', 'jurisdiction', 'governing']):
            return 'GOVERNING_LAW'
        elif any(term in heading_lower for term in ['dispute', 'resolution', 'arbitration']):
            return 'DISPUTE_RESOLUTION'
        else:
            return 'OTHER'
    
    def _normalize_kv_value(self, field: str, value: str) -> str:
        """Normalize extracted KV values based on field type."""
        value = value.strip()
        
        if field == "date_of_commencement" or field == "dob":
            # Normalize dates to ISO format
            try:
                from datetime import datetime
                # Try common date formats
                for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                return value  # Return original if parsing fails
            except Exception:
                return value
        
        elif field == "sum_assured":
            # Normalize currency to integer
            try:
                # Remove commas and currency symbols
                clean_value = re.sub(r'[,\s₹$]', '', value)
                return str(int(clean_value))
            except (ValueError, TypeError):
                return value
        
        elif field == "policy_no":
            # Normalize policy number format
            return value.upper().replace(" ", "")
        
        elif field == "nominee":
            # Normalize person names
            return value.title().strip()
        
        return value
    
    def _generate_diagnostics_summary(self, parsed_dict: Dict[str, Any], full_text: str) -> None:
        """Generate diagnostics summary for pipeline analysis."""
        try:
            # Calculate text similarity if Vision data available
            vision_file = Path("data") / "testing-ocr-pdf-1-1e08491e-28e026de" / "testing-ocr-pdf-1-1e08491e-28e026de.json"
            text_similarity = 0.0
            
            if vision_file.exists():
                try:
                    with open(vision_file, 'r', encoding='utf-8') as f:
                        vision_data = json.load(f)
                    vision_text = vision_data.get("ocr_result", {}).get("full_text", "")
                    
                    from ..text_utils import calculate_text_similarity
                    similarity_result = calculate_text_similarity(vision_text, full_text)
                    text_similarity = similarity_result["combined_similarity"]
                except Exception as e:
                    logger.warning("Failed to calculate text similarity", error=str(e))
            
            # Generate diagnostics
            diagnostics = {
                "timestamp": str(datetime.now().isoformat()),
                "similarity_score": text_similarity,
                "counts": {
                    "clauses": len(parsed_dict.get("clauses", [])),
                    "named_entities": len(parsed_dict.get("named_entities", [])),
                    "key_value_pairs": len(parsed_dict.get("key_value_pairs", []))
                },
                "needs_review": parsed_dict.get("metadata", {}).get("needs_review", False),
                "text_stats": {
                    "length": len(full_text),
                    "normalized_length": len(normalize_text(full_text))
                }
            }
            
            # Save diagnostics
            diagnostics_path = Path("artifacts") / "vision_to_docai" / "diagnostics.json"
            diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(diagnostics_path, 'w', encoding='utf-8') as f:
                json.dump(diagnostics, f, indent=2, ensure_ascii=False)
            
            logger.info(
                "Diagnostics summary generated",
                path=str(diagnostics_path),
                similarity=text_similarity,
                needs_review=diagnostics["needs_review"]
            )
            
            # Print path to console as requested
            print(f"📊 Diagnostics saved to: {diagnostics_path}")
            
        except Exception as e:
            logger.error("Failed to generate diagnostics summary", error=str(e))
    
    def _run_fallback_extraction_for_schema(self, full_text: str) -> tuple[List[NamedEntity], List[KeyValuePair], List[Clause]]:
        """Run fallback extraction that returns schema objects for production use."""
        # Placeholder for production fallback extraction
        return [], [], []
    
    def _map_kv_to_entity_type(self, kv_type: str) -> Optional[EntityType]:
        """Map KV field type to entity type."""
        mapping = {
            "policy_no": EntityType.ORGANIZATION,  # Policy numbers are org-related
            "date_of_commencement": EntityType.DATE,
            "sum_assured": EntityType.MONEY,
            "dob": EntityType.DATE,
            "nominee": EntityType.PERSON
        }
        return mapping.get(kv_type)
    
    def _extract_clauses_by_headings(self, full_text: str) -> List[Clause]:
        """Extract clauses based on heading patterns and document structure."""
        
        clauses = []
        
        # Pattern for detecting headings (uppercase lines or numbered sections)
        heading_patterns = [
            r'^\d+\.\s+([A-Z][^:\n]+):?\s*$',  # Numbered sections
            r'^([A-Z\s]{10,}):?\s*$',  # All caps headings
            r'^([A-Z][a-z\s]+):\s*$'  # Title case with colon
        ]
        
        lines = full_text.split('\n')
        current_clause = None
        clause_content = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a heading
            is_heading = False
            heading_text = ""
            
            for pattern in heading_patterns:
                match = re.match(pattern, line)
                if match:
                    is_heading = True
                    heading_text = match.group(1).strip()
                    break
            
            if is_heading:
                # Save previous clause if exists
                if current_clause and clause_content:
                    clause_text = '\n'.join(clause_content)
                    start_offset = full_text.find(clause_text)
                    if start_offset >= 0:
                        clauses.append(Clause(
                            id=str(uuid.uuid4()),
                            type=self._classify_clause_type(heading_text, clause_text),
                            confidence=0.7,  # Medium confidence for regex-based extraction
                            text_span=TextSpan(
                                start_offset=start_offset,
                                end_offset=start_offset + len(clause_text),
                                text=clause_text
                            ),
                            page_number=1,  # Default to page 1 for fallback
                            metadata={"title": current_clause}
                        ))
                
                # Start new clause
                current_clause = heading_text
                clause_content = []
            else:
                # Add to current clause content
                if current_clause:
                    clause_content.append(line)
        
        # Handle final clause
        if current_clause and clause_content:
            clause_text = '\n'.join(clause_content)
            start_offset = full_text.find(clause_text)
            if start_offset >= 0:
                clauses.append(Clause(
                    id=str(uuid.uuid4()),
                    type=self._classify_clause_type(current_clause, clause_text),
                    confidence=0.7,
                    text_span=TextSpan(
                        start_offset=start_offset,
                        end_offset=start_offset + len(clause_text),
                        text=clause_text
                    ),
                    page_number=1,  # Default to page 1 for fallback
                    metadata={"title": current_clause}
                ))
        
        return clauses
    
    def _are_entities_related(self, entity1: NamedEntity, entity2: NamedEntity) -> bool:
        """Check if two entities are related."""
        # Simple proximity check
        distance = abs(entity1.text_span.start_offset - entity2.text_span.start_offset)
        
        # Entities are related if they're close and have compatible types
        if distance > 1000:  # More than 1000 characters apart
            return False
        
        # Check type compatibility
        compatible_types = {
            (EntityType.PERSON, EntityType.ORGANIZATION),
            (EntityType.ORGANIZATION, EntityType.CONTRACT_PARTY),
            (EntityType.DATE, EntityType.OBLIGATION),
            (EntityType.MONEY, EntityType.PENALTY),
            (EntityType.LOCATION, EntityType.JURISDICTION)
        }
        
        type_pair = (entity1.type, entity2.type)
        return type_pair in compatible_types or type_pair[::-1] in compatible_types
    
    def _determine_reference_type(self, entity1: NamedEntity, entity2: NamedEntity) -> str:
        """Determine the type of relationship between entities."""
        type_pair = (entity1.type, entity2.type)
        
        reference_types = {
            (EntityType.PERSON, EntityType.ORGANIZATION): "employed_by",
            (EntityType.ORGANIZATION, EntityType.CONTRACT_PARTY): "is_party",
            (EntityType.DATE, EntityType.OBLIGATION): "due_date",
            (EntityType.MONEY, EntityType.PENALTY): "penalty_amount",
            (EntityType.LOCATION, EntityType.JURISDICTION): "under_jurisdiction"
        }
        
        return reference_types.get(type_pair, reference_types.get(type_pair[::-1], "related_to"))
    
    def _serialize_docai_response(self, document: documentai.Document) -> Dict[str, Any]:
        """Serialize DocAI document response to dictionary."""
        try:
            # Convert to JSON-serializable format
            # This is a simplified version - real implementation would handle all DocAI types
            return {
                'text': document.text,
                'pages': len(document.pages) if document.pages else 0,
                'entities': len(document.entities) if document.entities else 0,
                'mime_type': document.mime_type if hasattr(document, 'mime_type') else None
            }
        except Exception as e:
            logger.warning("Failed to serialize DocAI response", error=str(e))
            return {}