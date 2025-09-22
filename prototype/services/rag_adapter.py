"""
RAG Adapter for KAG Input Compatibility

This module provides a flexible compatibility adapter that enables the existing RAG system
to consume kag_input.json files produced by the document processing pipeline while maintaining
backward compatibility with legacy JSON formats.

Features:
- Auto-detects KAG vs legacy JSON format
- Configurable chunking with overlap (default: 500 chars, 50 overlap)
- Preserves structured data (clauses, entities, key-value pairs)
- Enriches chunks with document metadata (classifier, confidence)
- Deterministic chunk IDs for consistent citations
- Robust error handling and comprehensive logging

Chunking Policy:
- Text chunks: {document_id}_c{0001}, {document_id}_c{0002}, ...
- Clause chunks: {document_id}_clause_{0001}, {document_id}_clause_{0002}, ...
- Entity chunks: {document_id}_entity_{type}
- Context chunks: {document_id}_context

Usage:
    from .rag_adapter import load_and_normalize
    
    # Load single file or directory
    docs = load_and_normalize("path/to/kag_input.json")
    docs = load_and_normalize("path/to/directory", chunk_size=300, chunk_overlap=30)
    
    # Use with existing RAG system
    for doc in docs:
        chunks = create_chunks_for_embeddings(doc)
        # Process chunks for embedding and indexing
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGAdapter:
    """
    Flexible adapter for converting KAG input and legacy formats to normalized RAG format.
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, min_chunk_length: int = 50):
        """
        Initialize RAG adapter with chunking configuration.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_length: Minimum chunk length to include
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length
        
        logger.debug(f"RAG Adapter initialized: chunk_size={chunk_size}, overlap={chunk_overlap}, min_length={min_chunk_length}")
    
    def is_kag_format(self, data: Dict[str, Any]) -> bool:
        """
        Detect if the JSON data is in KAG input format.
        
        Args:
            data: Loaded JSON data
            
        Returns:
            True if KAG format, False if legacy format
        """
        # KAG format has these key characteristics
        kag_indicators = [
            "parsed_document" in data,
            "classifier_verdict" in data,
            "document_id" in data,
            "metadata" in data
        ]
        
        return sum(kag_indicators) >= 2  # At least 2 indicators present
    
    def extract_text_from_legacy(self, data: Dict[str, Any]) -> str:
        """
        Extract text from legacy JSON format.
        
        Args:
            data: Legacy format JSON data
            
        Returns:
            Extracted text content
        """
        # Try different legacy field patterns
        text_candidates = [
            data.get("content", ""),
            data.get("text", ""),
            data.get("extracted_data", {}).get("text_content", ""),
            data.get("extracted_data", {}).get("content", ""),
            data.get("full_text", "")
        ]
        
        for text in text_candidates:
            if text and text.strip():
                return text.strip()
        
        logger.warning("No text content found in legacy format")
        return ""
    
    def extract_text_from_kag(self, data: Dict[str, Any]) -> str:
        """
        Extract text from KAG input format.
        
        Args:
            data: KAG format JSON data
            
        Returns:
            Extracted text content
        """
        parsed_doc = data.get("parsed_document", {})
        
        # Primary text source
        full_text = parsed_doc.get("full_text", "")
        if full_text and full_text.strip():
            return full_text.strip()
        
        # Fallback to legacy fields within parsed_document
        text_candidates = [
            parsed_doc.get("text", ""),
            parsed_doc.get("content", ""),
            data.get("full_text", ""),  # Sometimes at root level
            data.get("text", "")
        ]
        
        for text in text_candidates:
            if text and text.strip():
                return text.strip()
        
        logger.warning("No text content found in KAG format")
        return ""
    
    def create_text_chunks(self, text: str, document_id: str, chunk_prefix: str = "c") -> List[Dict[str, Any]]:
        """
        Create overlapping text chunks from document text.
        
        Args:
            text: Full document text
            document_id: Document identifier
            chunk_prefix: Prefix for chunk IDs (e.g., 'c' for text, 'clause' for clauses)
            
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        text = text.strip()
        
        # Split text into sentences for better chunk boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        chunk_start = 0
        chunk_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(test_chunk) > self.chunk_size and current_chunk:
                # Save current chunk
                if len(current_chunk) >= self.min_chunk_length:
                    chunk_end = chunk_start + len(current_chunk)
                    chunks.append({
                        "chunk_id": f"{document_id}_{chunk_prefix}{chunk_count + 1:04d}",
                        "text": current_chunk.strip(),
                        "start": chunk_start,
                        "end": chunk_end,
                        "metadata": {
                            "chunk_type": "text" if chunk_prefix == "c" else chunk_prefix,
                            "chunk_index": chunk_count,
                            "char_count": len(current_chunk.strip())
                        }
                    })
                    chunk_count += 1
                
                # Start new chunk with overlap
                overlap_chars = min(self.chunk_overlap, len(current_chunk))
                if overlap_chars > 0:
                    overlap_text = current_chunk[-overlap_chars:]
                    chunk_start = chunk_end - overlap_chars
                    current_chunk = overlap_text + " " + sentence
                else:
                    chunk_start = chunk_end
                    current_chunk = sentence
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_length:
            chunk_end = chunk_start + len(current_chunk)
            chunks.append({
                "chunk_id": f"{document_id}_{chunk_prefix}{chunk_count + 1:04d}",
                "text": current_chunk.strip(),
                "start": chunk_start,
                "end": chunk_end,
                "metadata": {
                    "chunk_type": "text" if chunk_prefix == "c" else chunk_prefix,
                    "chunk_index": chunk_count,
                    "char_count": len(current_chunk.strip())
                }
            })
        
        logger.debug(f"Created {len(chunks)} {chunk_prefix} chunks from {len(text)} characters")
        return chunks
    
    def create_clause_chunks(self, clauses: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        """
        Create chunks from structured clauses.
        
        Args:
            clauses: List of clause objects from KAG input
            document_id: Document identifier
            
        Returns:
            List of clause chunk dictionaries
        """
        chunks = []
        
        for i, clause in enumerate(clauses):
            # Extract clause text
            clause_text = ""
            if isinstance(clause, dict):
                # Try different text field patterns
                text_candidates = [
                    clause.get("text_span", {}).get("text", ""),
                    clause.get("text", ""),
                    clause.get("content", ""),
                    str(clause) if not isinstance(clause, dict) else ""
                ]
                
                for text in text_candidates:
                    if text and text.strip():
                        clause_text = text.strip()
                        break
            else:
                clause_text = str(clause).strip()
            
            if clause_text and len(clause_text) >= self.min_chunk_length:
                chunks.append({
                    "chunk_id": f"{document_id}_clause_{i + 1:04d}",
                    "text": clause_text,
                    "start": 0,  # Clause doesn't have position in full text
                    "end": len(clause_text),
                    "metadata": {
                        "chunk_type": "clause",
                        "clause_index": i,
                        "clause_type": clause.get("type", "unknown") if isinstance(clause, dict) else "text",
                        "confidence": clause.get("confidence", 1.0) if isinstance(clause, dict) else 1.0,
                        "char_count": len(clause_text)
                    }
                })
        
        logger.debug(f"Created {len(chunks)} clause chunks from {len(clauses)} clauses")
        return chunks
    
    def create_entity_chunks(self, entities: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        """
        Create context chunks from named entities grouped by type.
        
        Args:
            entities: List of entity objects from KAG input
            document_id: Document identifier
            
        Returns:
            List of entity chunk dictionaries
        """
        if not entities:
            return []
        
        # Group entities by type
        entity_groups = {}
        for entity in entities:
            if isinstance(entity, dict):
                entity_type = entity.get("type", "unknown")
                if entity_type not in entity_groups:
                    entity_groups[entity_type] = []
                entity_groups[entity_type].append(entity)
        
        chunks = []
        for entity_type, group_entities in entity_groups.items():
            entity_texts = []
            
            for entity in group_entities:
                # Extract entity text
                entity_text = ""
                text_candidates = [
                    entity.get("text_span", {}).get("text", ""),
                    entity.get("text", ""),
                    entity.get("mention_text", ""),
                    entity.get("name", "")
                ]
                
                for text in text_candidates:
                    if text and text.strip():
                        entity_text = text.strip()
                        break
                
                if entity_text:
                    confidence = entity.get("confidence", 1.0)
                    entity_texts.append(f"{entity_text} (confidence: {confidence:.2f})")
            
            if entity_texts:
                chunk_text = f"{entity_type} entities: " + "; ".join(entity_texts)
                
                chunks.append({
                    "chunk_id": f"{document_id}_entity_{entity_type.lower()}",
                    "text": chunk_text,
                    "start": 0,
                    "end": len(chunk_text),
                    "metadata": {
                        "chunk_type": "entity",
                        "entity_type": entity_type,
                        "entity_count": len(entity_texts),
                        "char_count": len(chunk_text)
                    }
                })
        
        logger.debug(f"Created {len(chunks)} entity chunks from {len(entities)} entities")
        return chunks
    
    def create_context_chunk(self, data: Dict[str, Any], document_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a context chunk with document metadata.
        
        Args:
            data: Full document data (KAG or legacy)
            document_id: Document identifier
            
        Returns:
            Context chunk dictionary or None
        """
        context_parts = [f"Document ID: {document_id}"]
        
        # Extract classification information
        if self.is_kag_format(data):
            classifier_verdict = data.get("classifier_verdict", {})
            metadata = data.get("metadata", {})
            
            if classifier_verdict.get("label"):
                context_parts.append(f"Document Type: {classifier_verdict['label']}")
            if classifier_verdict.get("confidence"):
                context_parts.append(f"Classification Confidence: {classifier_verdict['confidence']}")
            if classifier_verdict.get("score"):
                context_parts.append(f"Classification Score: {classifier_verdict['score']:.3f}")
            if metadata.get("total_pages"):
                context_parts.append(f"Total Pages: {metadata['total_pages']}")
            if metadata.get("processing_method"):
                context_parts.append(f"Processing Method: {metadata['processing_method']}")
        
        if len(context_parts) > 1:  # More than just document ID
            context_text = ". ".join(context_parts) + "."
            
            return {
                "chunk_id": f"{document_id}_context",
                "text": context_text,
                "start": 0,
                "end": len(context_text),
                "metadata": {
                    "chunk_type": "context",
                    "char_count": len(context_text)
                }
            }
        
        return None
    
    def normalize_document(self, data: Dict[str, Any], file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Normalize a single document from KAG or legacy format to adapter format.
        
        Args:
            data: Loaded JSON data
            file_path: Optional file path for document ID generation
            
        Returns:
            Normalized adapter format dictionary
        """
        is_kag = self.is_kag_format(data)
        
        # Extract document ID
        document_id = data.get("document_id", "")
        if not document_id and file_path:
            document_id = Path(file_path).stem
        if not document_id:
            document_id = f"doc_{hash(str(data))}"
        
        logger.debug(f"Processing document: {document_id} (format: {'KAG' if is_kag else 'legacy'})")
        
        # Extract text content
        if is_kag:
            full_text = self.extract_text_from_kag(data)
            parsed_doc = data.get("parsed_document", {})
            classifier_verdict = data.get("classifier_verdict", {})
            metadata = data.get("metadata", {})
            
            # Extract structured data
            clauses = parsed_doc.get("clauses", [])
            entities = parsed_doc.get("named_entities", [])
            kv_pairs = parsed_doc.get("key_value_pairs", [])
            
            # Extract document confidence - handle both numeric and string values
            confidence_value = classifier_verdict.get("confidence", 
                             classifier_verdict.get("score",
                             parsed_doc.get("document_confidence", 
                             metadata.get("document_confidence", 0.0))))
            
            # Convert string confidence to numeric
            if isinstance(confidence_value, str):
                confidence_map = {
                    "very_high": 0.95,
                    "high": 0.85,
                    "medium": 0.75,
                    "low": 0.55,
                    "very_low": 0.35,
                    "unknown": 0.0
                }
                document_confidence = confidence_map.get(confidence_value.lower(), 0.0)
            else:
                document_confidence = float(confidence_value)
        else:
            full_text = self.extract_text_from_legacy(data)
            clauses = []
            entities = []
            kv_pairs = []
            classifier_verdict = {}
            document_confidence = 0.0
        
        # Create chunks
        chunks = []
        
        # Text chunks from full text
        if full_text:
            text_chunks = self.create_text_chunks(full_text, document_id, "c")
            chunks.extend(text_chunks)
        
        # Clause chunks
        if clauses:
            clause_chunks = self.create_clause_chunks(clauses, document_id)
            chunks.extend(clause_chunks)
        
        # Entity chunks
        if entities:
            entity_chunks = self.create_entity_chunks(entities, document_id)
            chunks.extend(entity_chunks)
        
        # Context chunk
        context_chunk = self.create_context_chunk(data, document_id)
        if context_chunk:
            chunks.append(context_chunk)
        
        # Enrich all chunks with document metadata
        for chunk in chunks:
            chunk["metadata"].update({
                "document_id": document_id,
                "classifier_label": classifier_verdict.get("label", "unknown"),
                "document_confidence": document_confidence,
                "source_format": "kag" if is_kag else "legacy"
            })
        
        # Build normalized output
        normalized = {
            "document_id": document_id,
            "full_text": full_text,
            "chunks": chunks,
            "structured": {
                "clauses": clauses,
                "entities": entities,
                "kv_pairs": kv_pairs
            },
            "classifier": {
                "label": classifier_verdict.get("label", "unknown"),
                "score": classifier_verdict.get("score", 0.0),
                "confidence": classifier_verdict.get("confidence", "unknown")
            },
            "document_confidence": document_confidence,
            "raw": data
        }
        
        logger.info(f"Normalized document {document_id}: {len(chunks)} chunks, "
                   f"classifier: {normalized['classifier']['label']}, "
                   f"confidence: {document_confidence:.3f}")
        
        return normalized
    
    def load_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and normalize a single JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Normalized document
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not valid JSON
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return self.normalize_document(data, str(file_path))
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise
    
    def load_directory(self, dir_path: str, file_pattern: str = "*.json") -> List[Dict[str, Any]]:
        """
        Load and normalize all JSON files in a directory.
        
        Args:
            dir_path: Path to directory
            file_pattern: Glob pattern for files to load
            
        Returns:
            List of normalized documents
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        # Find JSON files
        if file_pattern == "kag_input.json":
            # Look for specific kag_input.json files
            json_files = list(dir_path.rglob("kag_input.json"))
        else:
            # Use glob pattern
            json_files = list(dir_path.glob(file_pattern))
        
        if not json_files:
            logger.warning(f"No JSON files found in {dir_path} with pattern {file_pattern}")
            return []
        
        documents = []
        for json_file in json_files:
            try:
                doc = self.load_single_file(str(json_file))
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")
                continue
        
        logger.info(f"Loaded {len(documents)} documents from {dir_path}")
        return documents


def load_and_normalize(path_or_dir: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Load and normalize KAG input or legacy JSON files to adapter format.
    
    Args:
        path_or_dir: Path to single file or directory containing JSON files
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of normalized document dictionaries in adapter format
        
    Example:
        # Load single file
        docs = load_and_normalize("artifacts/test/kag_input.json")
        
        # Load directory with custom chunking
        docs = load_and_normalize("artifacts/", chunk_size=300, chunk_overlap=30)
    """
    adapter = RAGAdapter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    path = Path(path_or_dir)
    
    if path.is_file():
        logger.info(f"Loading single file: {path}")
        return [adapter.load_single_file(str(path))]
    elif path.is_dir():
        logger.info(f"Loading directory: {path}")
        return adapter.load_directory(str(path))
    else:
        raise FileNotFoundError(f"Path not found: {path}")


def create_chunks_for_embeddings(adapter_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract chunks from adapter document format ready for embedding.
    
    Args:
        adapter_doc: Normalized document from load_and_normalize()
        
    Returns:
        List of dictionaries with chunk_id, text, and metadata for embedding
        
    Example:
        docs = load_and_normalize("kag_input.json")
        for doc in docs:
            chunks = create_chunks_for_embeddings(doc)
            # Pass chunks to embed_chunks()
    """
    return [
        {
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "metadata": chunk["metadata"]
        }
        for chunk in adapter_doc["chunks"]
    ]


def get_chunks_summary(adapter_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for loaded documents.
    
    Args:
        adapter_docs: List of normalized documents
        
    Returns:
        Summary dictionary with statistics
    """
    if not adapter_docs:
        return {"total_documents": 0, "total_chunks": 0}
    
    total_chunks = sum(len(doc["chunks"]) for doc in adapter_docs)
    chunk_types = {}
    classifiers = {}
    
    for doc in adapter_docs:
        for chunk in doc["chunks"]:
            chunk_type = chunk["metadata"].get("chunk_type", "unknown")
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        classifier_label = doc["classifier"]["label"]
        classifiers[classifier_label] = classifiers.get(classifier_label, 0) + 1
    
    return {
        "total_documents": len(adapter_docs),
        "total_chunks": total_chunks,
        "chunk_types": chunk_types,
        "classifiers": classifiers,
        "avg_chunks_per_doc": total_chunks / len(adapter_docs) if adapter_docs else 0
    }


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    # Test with a sample file if available
    test_file = "artifacts/single_test/test-1758411760/kag_input.json"
    if Path(test_file).exists():
        docs = load_and_normalize(test_file)
        print(f"Loaded {len(docs)} documents")
        
        if docs:
            summary = get_chunks_summary(docs)
            print(f"Summary: {summary}")
            
            chunks = create_chunks_for_embeddings(docs[0])
            print(f"First document has {len(chunks)} chunks ready for embedding")
    else:
        print(f"Test file not found: {test_file}")