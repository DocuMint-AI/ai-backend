"""
Enhanced text parsing utilities for DocAI-compatible document processing.

This module provides utilities for parsing and extracting structured data
from DocAI-format OCR results, including key-value pairs, tables, and 
enhanced text processing capabilities.
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Union, Any, List, Optional, Tuple


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """
    Enhanced parsed document containing structured sections, entities, and metadata.
    
    Attributes:
        sections: Dictionary mapping section names to their content
        key_value_pairs: Extracted key-value pairs
        tables: Detected table structures
        entities: Named entities and structured data
        metadata: Document metadata and processing info
    """
    sections: Dict[str, str]
    key_value_pairs: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class LocalTextParser:
    """
    Enhanced local text parser for extracting structured data from DocAI-format documents.
    
    Provides methods for parsing DocAI OCR results, extracting key-value pairs,
    detecting tables, and processing structured document content.
    """
    
    def __init__(self, text: Union[str, Path, Dict]) -> None:
        """
        Initialize text parser with text content, file path, or DocAI result.
        
        Args:
            text: Raw text string, Path to text file, or DocAI OCR result dict
            
        Example:
            >>> # From raw text
            >>> parser = LocalTextParser("Raw text content here")
            >>> # From file
            >>> parser = LocalTextParser(Path("document.txt"))
            >>> # From DocAI result
            >>> parser = LocalTextParser(docai_ocr_result)
        """
        if isinstance(text, dict) and "ocr_result" in text:
            # DocAI format input
            self.docai_data = text
            self.raw_text = text["ocr_result"]["full_text"]
            self.source = "docai_result"
            self.pages = text["ocr_result"]["pages"]
        elif isinstance(text, str) and not "\n" in text and len(text) < 500 and Path(text).exists():
            # File input - only if it's a short string that looks like a path
            self.raw_text = self.load_text_from_file(str(text))
            self.source = str(text)
            self.docai_data = None
            self.pages = []
        elif isinstance(text, str):
            # Raw text input
            self.raw_text = text
            self.source = "raw_string"
            self.docai_data = None
            self.pages = []
        else:
            raise ValueError("Input must be text string, valid file path, or DocAI result dict")
        
        self.cleaned_text = ""
        self.parsed_sections = {}
        self.key_value_pairs = []
        self.detected_tables = []
        self.extracted_entities = []
        
        logger.info(f"Initialized parser with {len(self.raw_text)} characters from {self.source}")
    
    @staticmethod
    def load_text_from_file(path: str) -> str:
        """
        Load text content from a file.
        
        Args:
            path: Path to the text file
            
        Returns:
            Text content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file encoding is unsupported
            
        Example:
            >>> text = LocalTextParser.load_text_from_file("document.txt")
            >>> print(f"Loaded {len(text)} characters")
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        try:
            # Try UTF-8 first, fall back to latin-1 if needed
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode failed for {path}, trying latin-1")
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        logger.info(f"Loaded {len(content)} characters from {path}")
        return content
    
    def clean_text(self) -> str:
        """
        Clean and normalize text content.
        
        Removes extra whitespace, normalizes line endings, and removes
        common artifacts from OCR or document conversion.
        
        Returns:
            Cleaned text string
            
        Example:
            >>> parser = LocalTextParser("  Multiple   spaces\\n\\n\\nText  ")
            >>> cleaned = parser.clean_text()
            >>> print(repr(cleaned))  # "Multiple spaces\\nText"
        """
        text = self.raw_text
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace
        text = re.sub(r' {2,}', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newline
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control chars
        
        # Trim whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        self.cleaned_text = text
        logger.info(f"Text cleaned: {len(self.raw_text)} -> {len(text)} characters")
        
        return text
    
    def parse_sections(self) -> Dict[str, str]:
        """
        Parse text into logical sections using common document patterns.
        
        Identifies sections based on headers, formatting, and content patterns.
        Configurable via regex patterns for different document types.
        
        Returns:
            Dictionary mapping section names to their content
            
        Example:
            >>> parser = LocalTextParser("TITLE\\nContent\\n\\nSECTION 1\\nMore content")
            >>> sections = parser.parse_sections()
            >>> print(sections.keys())  # dict_keys(['title', 'section_1'])
        """
        if not self.cleaned_text:
            self.clean_text()
        
        text = self.cleaned_text
        sections = {}
        
        # Common section header patterns
        header_patterns = [
            r'^([A-Z][A-Z\s]{2,}):?\s*$',  # ALL CAPS headers
            r'^(SECTION\s+\d+):?\s*(.*)$',  # Numbered sections
            r'^(\d+\.?\s+[A-Z][A-Za-z\s]+):?\s*$',  # Numbered titles
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):?\s*$',  # Title Case headers
        ]
        
        current_section = "content"
        current_content = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                current_content.append('')
                continue
            
            # Check if line matches any header pattern
            is_header = False
            for pattern in header_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    # Start new section
                    current_section = match.group(1).lower().replace(' ', '_')
                    current_content = []
                    is_header = True
                    break
            
            if not is_header:
                current_content.append(line)
        
        # Save final section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # Remove empty sections
        sections = {k: v for k, v in sections.items() if v.strip()}
        
        self.parsed_sections = sections
        logger.info(f"Parsed {len(sections)} sections: {list(sections.keys())}")
        
        return sections
    
    def extract_key_values(self, patterns: Dict[str, str]) -> Dict[str, str]:
        """
        Extract key-value pairs using custom regex patterns.
        
        Args:
            patterns: Dictionary mapping field names to regex patterns
            
        Returns:
            Dictionary of extracted key-value pairs
            
        Example:
            >>> text = "Name: John Doe\\nEmail: john@example.com\\nPhone: 555-1234"
            >>> parser = LocalTextParser(text)
            >>> patterns = {
            ...     "name": r"Name:\s*(.+)",
            ...     "email": r"Email:\s*([\w.-]+@[\w.-]+)",
            ...     "phone": r"Phone:\s*([\d-]+)"
            ... }
            >>> values = parser.extract_key_values(patterns)
            >>> print(values)  # {'name': 'John Doe', 'email': 'john@example.com', ...}
        """
        if not self.cleaned_text:
            self.clean_text()
        
        text = self.cleaned_text
        extracted = {}
        
        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Use first capture group if available, otherwise full match
                    value = match.group(1) if match.groups() else match.group(0)
                    extracted[field_name] = value.strip()
                    logger.debug(f"Extracted {field_name}: {value.strip()}")
                else:
                    logger.debug(f"No match found for pattern '{field_name}': {pattern}")
            except re.error as e:
                logger.warning(f"Invalid regex pattern for '{field_name}': {e}")
        
        logger.info(f"Extracted {len(extracted)} key-value pairs")
        return extracted
    
    def extract_key_values_from_docai(self) -> List[Dict[str, Any]]:
        """
        Extract key-value pairs from DocAI format using spatial analysis.
        
        Returns:
            List of dictionaries containing key-value pairs with positions
        """
        if not self.docai_data:
            logger.warning("No DocAI data available for spatial key-value extraction")
            return []
        
        kv_pairs = []
        
        for page in self.pages:
            page_num = page["page"]
            
            # Look for potential key-value pairs in text blocks
            for i, block in enumerate(page["text_blocks"]):
                block_text = block["text"].strip()
                
                # Common key-value patterns
                patterns = [
                    r'([A-Za-z\s]+):\s*([^\n]+)',  # "Key: Value"
                    r'([A-Za-z\s]+)\s*=\s*([^\n]+)',  # "Key = Value"
                    r'([A-Za-z\s]+)\s*-\s*([^\n]+)',  # "Key - Value"
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, block_text)
                    for match in matches:
                        key = match.group(1).strip()
                        value = match.group(2).strip()
                        
                        if len(key) > 1 and len(value) > 0:  # Basic validation
                            kv_pairs.append({
                                "key": key,
                                "value": value,
                                "confidence": block["confidence"],
                                "page": page_num,
                                "block_id": block["block_id"],
                                "source": "spatial_analysis"
                            })
        
        self.key_value_pairs = kv_pairs
        logger.info(f"Extracted {len(kv_pairs)} key-value pairs from DocAI data")
        return kv_pairs
    
    def detect_tables_from_docai(self) -> List[Dict[str, Any]]:
        """
        Detect table structures from DocAI format using spatial analysis.
        
        Returns:
            List of dictionaries containing detected table information
        """
        if not self.docai_data:
            logger.warning("No DocAI data available for table detection")
            return []
        
        tables = []
        
        for page in self.pages:
            page_num = page["page"]
            blocks = page["text_blocks"]
            
            # Group blocks by vertical position to find potential rows
            rows = self._group_blocks_into_rows(blocks)
            
            # Look for patterns that suggest tabular data
            for row_group in rows:
                if len(row_group) >= 2:  # At least 2 columns
                    # Check if blocks are aligned horizontally
                    if self._are_blocks_aligned_horizontally(row_group):
                        table_data = {
                            "table_id": f"table_p{page_num}_{len(tables) + 1}",
                            "page": page_num,
                            "rows": len([row_group]),  # Simplified - would need more logic
                            "columns": len(row_group),
                            "cells": []
                        }
                        
                        for i, block in enumerate(row_group):
                            table_data["cells"].append({
                                "row": 0,  # Simplified
                                "column": i,
                                "text": block["text"],
                                "confidence": block["confidence"],
                                "block_id": block["block_id"]
                            })
                        
                        tables.append(table_data)
        
        self.detected_tables = tables
        logger.info(f"Detected {len(tables)} potential tables from DocAI data")
        return tables
    
    def _group_blocks_into_rows(self, blocks: List[Dict]) -> List[List[Dict]]:
        """
        Group text blocks into potential table rows based on vertical alignment.
        
        Args:
            blocks: List of text blocks from a page
            
        Returns:
            List of lists, where each inner list represents a potential row
        """
        if not blocks:
            return []
        
        # Sort blocks by vertical position (top of bounding box)
        sorted_blocks = sorted(blocks, key=lambda b: min(coord[1] for coord in b["bounding_box"]))
        
        rows = []
        current_row = []
        current_y = None
        y_threshold = 20  # Pixels tolerance for same row
        
        for block in sorted_blocks:
            block_y = min(coord[1] for coord in block["bounding_box"])
            
            if current_y is None or abs(block_y - current_y) <= y_threshold:
                current_row.append(block)
                current_y = block_y if current_y is None else (current_y + block_y) / 2
            else:
                if len(current_row) > 1:  # Only keep potential rows
                    rows.append(sorted(current_row, key=lambda b: min(coord[0] for coord in b["bounding_box"])))
                current_row = [block]
                current_y = block_y
        
        if len(current_row) > 1:
            rows.append(sorted(current_row, key=lambda b: min(coord[0] for coord in b["bounding_box"])))
        
        return rows
    
    def _are_blocks_aligned_horizontally(self, blocks: List[Dict]) -> bool:
        """
        Check if blocks are aligned horizontally (suggesting table structure).
        
        Args:
            blocks: List of text blocks
            
        Returns:
            True if blocks appear to be in a table row
        """
        if len(blocks) < 2:
            return False
        
        # Check if blocks have similar heights and are roughly aligned
        heights = []
        y_positions = []
        
        for block in blocks:
            bbox = block["bounding_box"]
            height = max(coord[1] for coord in bbox) - min(coord[1] for coord in bbox)
            y_pos = min(coord[1] for coord in bbox)
            
            heights.append(height)
            y_positions.append(y_pos)
        
        # Check height consistency
        avg_height = sum(heights) / len(heights)
        height_variance = sum((h - avg_height) ** 2 for h in heights) / len(heights)
        
        # Check vertical alignment
        avg_y = sum(y_positions) / len(y_positions)
        y_variance = sum((y - avg_y) ** 2 for y in y_positions) / len(y_positions)
        
        # Simple heuristics for table detection
        return height_variance < (avg_height * 0.3) ** 2 and y_variance < 100
    
    def extract_entities_from_docai(self) -> List[Dict[str, Any]]:
        """
        Extract named entities and structured data from DocAI format.
        
        Returns:
            List of dictionaries containing extracted entities
        """
        entities = []
        
        # Common entity patterns
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            "date": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            "currency": r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars?)\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "zipcode": r'\b\d{5}(?:-\d{4})?\b'
        }
        
        if self.docai_data:
            # Extract from DocAI structured data
            for page in self.pages:
                page_num = page["page"]
                
                for block in page["text_blocks"]:
                    text = block["text"]
                    
                    for entity_type, pattern in patterns.items():
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        for match in matches:
                            entities.append({
                                "type": entity_type,
                                "value": match.group(0),
                                "confidence": block["confidence"],
                                "page": page_num,
                                "block_id": block["block_id"],
                                "start_pos": match.start(),
                                "end_pos": match.end()
                            })
        else:
            # Extract from raw text
            for entity_type, pattern in patterns.items():
                matches = re.finditer(pattern, self.raw_text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "type": entity_type,
                        "value": match.group(0),
                        "confidence": 0.8,  # Default confidence for regex matches
                        "page": 1,
                        "block_id": None,
                        "start_pos": match.start(),
                        "end_pos": match.end()
                    })
        
        self.extracted_entities = entities
        logger.info(f"Extracted {len(entities)} entities")
        return entities
    
    def to_json(self) -> str:
        """
        Convert parsed document to JSON format with enhanced structure.
        
        Returns:
            JSON string representation of the parsed document
        """
        # Ensure all parsing methods have been run
        if not self.parsed_sections:
            self.parse_sections()
        
        if not self.key_value_pairs and self.docai_data:
            self.extract_key_values_from_docai()
        
        if not self.detected_tables and self.docai_data:
            self.detect_tables_from_docai()
        
        if not self.extracted_entities:
            self.extract_entities_from_docai()
        
        # Create enhanced metadata
        metadata = {
            "source": self.source,
            "original_length": len(self.raw_text),
            "cleaned_length": len(self.cleaned_text),
            "sections_count": len(self.parsed_sections),
            "key_value_pairs_count": len(self.key_value_pairs),
            "tables_count": len(self.detected_tables),
            "entities_count": len(self.extracted_entities),
            "parser_version": "2.0",
            "docai_compatible": self.docai_data is not None
        }
        
        if self.docai_data:
            metadata.update({
                "document_id": self.docai_data.get("document_id"),
                "original_filename": self.docai_data.get("original_filename"),
                "pages_count": len(self.pages)
            })
        
        parsed_doc = ParsedDocument(
            sections=self.parsed_sections,
            key_value_pairs=self.key_value_pairs,
            tables=self.detected_tables,
            entities=self.extracted_entities,
            metadata=metadata
        )
        
        # Convert to JSON
        return json.dumps(asdict(parsed_doc), indent=2, ensure_ascii=False)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the parsed document.
        
        Returns:
            Dictionary containing parsing summary statistics
        """
        return {
            "text_length": len(self.raw_text),
            "sections": len(self.parsed_sections),
            "key_value_pairs": len(self.key_value_pairs),
            "tables": len(self.detected_tables),
            "entities": len(self.extracted_entities),
            "entity_types": list(set(e["type"] for e in self.extracted_entities)),
            "has_docai_data": self.docai_data is not None,
            "pages": len(self.pages) if self.pages else 1
        }


if __name__ == "__main__":
    """
    Demo usage of enhanced LocalTextParser with DocAI compatibility.
    """
    # Sample document text
    sample_text = """
    COMPANY OVERVIEW
    
    Acme Corporation is a leading provider of innovative solutions.
    Founded in 2020, we serve customers worldwide.
    
    CONTACT INFORMATION
    
    Name: John Smith
    Email: john.smith@acme.com
    Phone: (555) 123-4567
    Address: 123 Main St, Anytown, USA 12345
    
    SECTION 1: Products
    
    We offer a range of high-quality products including:
    - Software solutions
    - Hardware components
    - Consulting services
    
    FINANCIAL DATA
    
    Revenue: $1.2M
    Employees: 25
    SSN: 123-45-6789
    Date: 01/15/2024
    """
    
    try:
        # Initialize parser with sample text
        parser = LocalTextParser(sample_text)
        
        # Clean text
        cleaned = parser.clean_text()
        print(f"Cleaned text length: {len(cleaned)} characters")
        
        # Parse sections
        sections = parser.parse_sections()
        print(f"\\nParsed {len(sections)} sections:")
        for section_name in sections.keys():
            print(f"  - {section_name}")
        
        # Extract key-value pairs using traditional method
        contact_patterns = {
            "name": r"Name:\s*(.+)",
            "email": r"Email:\s*([\w.-]+@[\w.-]+)",
            "phone": r"Phone:\s*([\(\)\d\s-]+)",
            "revenue": r"Revenue:\s*(\$[\d.]+[MK]?)"
        }
        
        extracted = parser.extract_key_values(contact_patterns)
        print(f"\\nExtracted {len(extracted)} key-value pairs:")
        for key, value in extracted.items():
            print(f"  {key}: {value}")
        
        # Extract entities
        entities = parser.extract_entities_from_docai()
        print(f"\\nExtracted {len(entities)} entities:")
        entity_summary = {}
        for entity in entities:
            entity_type = entity["type"]
            if entity_type not in entity_summary:
                entity_summary[entity_type] = []
            entity_summary[entity_type].append(entity["value"])
        
        for etype, values in entity_summary.items():
            print(f"  {etype}: {', '.join(values)}")
        
        # Get summary
        summary = parser.get_summary()
        print(f"\\nParsing Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Convert to JSON
        json_output = parser.to_json()
        print(f"\\nJSON output length: {len(json_output)} characters")
        print("\\nFirst 300 characters of JSON:")
        print(json_output[:300] + "..." if len(json_output) > 300 else json_output)
        
        print("\\n" + "="*60)
        print("Enhanced LocalTextParser demo completed successfully!")
        print("Now supports DocAI format, entity extraction, and table detection.")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
