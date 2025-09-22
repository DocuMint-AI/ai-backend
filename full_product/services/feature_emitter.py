"""
Feature vector emitter for generating ML-ready features from parsed documents.

This module provides functionality to generate feature vectors from parsed
documents, including embeddings placeholders and structural features for
downstream ML models and Vertex AI integration.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Use logging if structlog not available
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# Handle numpy import gracefully
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def emit_feature_vector(parsed_output: dict, out_path: str, classifier_verdict: Optional[dict] = None) -> None:
    """
    Generate feature vector JSON from parsed document output.
    
    Args:
        parsed_output: Parsed document dictionary with clauses, entities, etc.
        out_path: Output path for feature_vector.json
        classifier_verdict: Optional classification verdict from regex classifier (MVP)
        
    Generates:
        feature_vector.json with embeddings, KV flags, structural features, and classifier verdict
    """
    try:
        logger.info("Generating feature vector", output_path=out_path)
        
        # Extract basic document info
        document_id = parsed_output.get("metadata", {}).get("document_id", "unknown")
        full_text = parsed_output.get("full_text", "")
        clauses = parsed_output.get("clauses", [])
        named_entities = parsed_output.get("named_entities", [])
        key_value_pairs = parsed_output.get("key_value_pairs", [])
        needs_review = parsed_output.get("metadata", {}).get("needs_review", False)
        
        # Generate embeddings (placeholder or Vertex)
        embedding_doc = _generate_document_embedding(full_text)
        embedding_clauses = _generate_clause_embeddings(clauses)
        
        # Extract KV flags and values
        kv_flags, kv_values = _extract_kv_features(key_value_pairs, full_text)
        
        # Calculate structural features
        structural = _calculate_structural_features(parsed_output)
        
        # Calculate confidence metrics
        confidences = _calculate_confidence_metrics(named_entities, clauses, key_value_pairs)
        
        # Compose feature vector matching test expectations
        feature_vector = {
            "document_id": document_id,
            "embedding_doc": embedding_doc,
            "kv_flags": kv_flags,
            "structural": structural,
            "needs_review": needs_review,
            # MVP: Classifier verdict integration
            "classifier_verdict": classifier_verdict,
            # Additional details
            "embedding_clauses": embedding_clauses,
            "kv_values": kv_values,
            "confidences": confidences,
            "generation_metadata": {
                "timestamp": Path().absolute().as_posix(),
                "version": "1.0",
                "feature_count": len(kv_flags) + len(structural) + len(confidences),
                "mvp_mode": True,
                "vertex_embedding_disabled": True,
                "classification_method": "regex_pattern_matching" if classifier_verdict else "none"
            }
        }
        
        # Save with atomic write
        out_file = Path(out_path)
        temp_file = out_file.with_suffix('.tmp')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(feature_vector, f, indent=2, ensure_ascii=False)
        
        # Atomically rename to final file
        if out_file.exists():
            out_file.unlink()  # Remove existing file first
        temp_file.rename(out_file)
        
        if hasattr(logger, 'info') and hasattr(logger.info, '__call__'):
            try:
                # Try structlog style first
                logger.info(
                    "Feature vector generated successfully",
                    output_path=str(out_file),
                    feature_count=feature_vector["generation_metadata"]["feature_count"],
                    needs_review=needs_review
                )
            except TypeError:
                # Fallback to standard logging
                logger.info(f"Feature vector generated: {str(out_file)}")
        else:
            print(f"Feature vector generated: {str(out_file)}")
        
    except Exception as e:
        error_msg = f"Failed to generate feature vector: {str(e)}"
        if hasattr(logger, 'error'):
            try:
                logger.error(error_msg)
            except TypeError:
                print(error_msg)
        else:
            print(error_msg)
        raise


def _generate_document_embedding(text: str) -> List[float]:
    """
    Generate document-level embedding vector.
    
    Args:
        text: Full document text
        
    Returns:
        Embedding vector (placeholder or Vertex API result)
    """
    vertex_enabled = os.getenv("VERTEX_EMBEDDING_ENABLED", "false").lower() == "true"
    
    if vertex_enabled:
        try:
            # TODO: Implement Vertex AI embedding call
            # from google.cloud import aiplatform
            # embedding = aiplatform.TextEmbeddingModel.from_pretrained("textembedding-gecko").get_embeddings([text])
            logger.info("Vertex embeddings enabled but not implemented - using placeholder")
            return _generate_placeholder_embedding(768)  # Vertex embedding size
        except Exception as e:
            logger.warning("Vertex embedding failed, using placeholder", error=str(e))
            return _generate_placeholder_embedding(768)
    else:
        logger.info("Vertex embeddings disabled - using deterministic placeholder")
        return _generate_placeholder_embedding(768)


def _generate_clause_embeddings(clauses: List[dict]) -> List[List[float]]:
    """Generate embeddings for each clause."""
    clause_embeddings = []
    
    for clause in clauses:
        clause_text = clause.get("text_span", {}).get("text", "")
        if clause_text:
            # For now, use placeholder embeddings
            clause_embeddings.append(_generate_placeholder_embedding(768))
    
    return clause_embeddings


def _generate_placeholder_embedding(size: int = 768) -> List[float]:
    """Generate deterministic placeholder embedding vector."""
    # Create deterministic placeholder based on size
    return [0.1 * (i % 10) for i in range(size)]


def _extract_kv_features(key_value_pairs: List[dict], full_text: str) -> tuple[Dict[str, bool], Dict[str, Any]]:
    """
    Extract KV flags and values for feature vector.
    
    Args:
        key_value_pairs: List of extracted key-value pairs
        full_text: Full document text for fallback extraction
        
    Returns:
        Tuple of (kv_flags, kv_values)
    """
    # Mandatory insurance document fields
    mandatory_fields = ["policy_no", "date_of_commencement", "sum_assured", "dob", "nominee"]
    
    kv_flags = {}
    kv_values = {}
    
    # Check for extracted KVs
    for field in mandatory_fields:
        kv_flags[f"has_{field}"] = False
        kv_values[field] = None
    
    # Process actual extracted KVs
    for kv in key_value_pairs:
        key_text = kv.get("key", {}).get("text", "").lower()
        value_text = kv.get("value", {}).get("text", "")
        
        # Map to standardized field names
        if "policy" in key_text and "no" in key_text:
            kv_flags["has_policy_no"] = True
            kv_values["policy_no"] = value_text
        elif "date" in key_text and "commencement" in key_text:
            kv_flags["has_date_of_commencement"] = True
            kv_values["date_of_commencement"] = value_text
        elif "sum" in key_text and "assured" in key_text:
            kv_flags["has_sum_assured"] = True
            kv_values["sum_assured"] = value_text
        elif "birth" in key_text or "dob" in key_text:
            kv_flags["has_dob"] = True
            kv_values["dob"] = value_text
        elif "nominee" in key_text:
            kv_flags["has_nominee"] = True
            kv_values["nominee"] = value_text
    
    return kv_flags, kv_values


def _calculate_structural_features(parsed_output: dict) -> Dict[str, Any]:
    """Calculate structural document features."""
    clauses = parsed_output.get("clauses", [])
    entities = parsed_output.get("named_entities", [])
    kvs = parsed_output.get("key_value_pairs", [])
    full_text = parsed_output.get("full_text", "")
    
    return {
        "page_count": parsed_output.get("metadata", {}).get("page_count", 1),
        "clause_count": len(clauses),
        "entity_count": len(entities),
        "kv_count": len(kvs),
        "text_length": len(full_text),
        "clause_coverage": len(clauses) / max(1, len(full_text.split('\n'))),  # Approx coverage
        "entity_density": len(entities) / max(1, len(full_text.split())),  # Entities per word
        "avg_clause_length": sum(len(c.get("text_span", {}).get("text", "")) for c in clauses) / max(1, len(clauses))
    }


def _calculate_confidence_metrics(entities: List[dict], clauses: List[dict], kvs: List[dict]) -> Dict[str, float]:
    """Calculate confidence metrics across all extracted elements."""
    all_confidences = []
    
    # Collect all confidence scores
    for entity in entities:
        conf = entity.get("confidence")
        if conf is not None:
            all_confidences.append(conf)
    
    for clause in clauses:
        conf = clause.get("confidence")
        if conf is not None:
            all_confidences.append(conf)
    
    for kv in kvs:
        conf = kv.get("confidence")
        if conf is not None:
            all_confidences.append(conf)
    
    if not all_confidences:
        return {"avg_confidence": 0.0, "min_confidence": 0.0, "max_confidence": 0.0}
    
    # Calculate variance without numpy if not available
    avg_conf = sum(all_confidences) / len(all_confidences)
    if HAS_NUMPY:
        variance = np.var(all_confidences).item() if len(all_confidences) > 1 else 0.0
    else:
        variance = sum((x - avg_conf) ** 2 for x in all_confidences) / len(all_confidences) if len(all_confidences) > 1 else 0.0
    
    return {
        "avg_confidence": avg_conf,
        "min_confidence": min(all_confidences),
        "max_confidence": max(all_confidences),
        "confidence_variance": variance
    }