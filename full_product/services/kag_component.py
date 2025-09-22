"""
Knowledge Augmented Generation (KAG) Component for AI Backend MVP

This module provides the KAG component that receives DocAI parsed documents
and classifier verdicts, then prepares the data for downstream processing.
It creates a structured handoff payload for knowledge augmentation workflows.

Features:
- Receives DocAI parsed text and classification verdicts
- Generates structured KAG input payloads
- Creates kag_input.json artifacts for transparency
- Supports document knowledge extraction workflows
- Provides clear logging and processing metadata
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class KAGInput:
    """Structured input for Knowledge Augmented Generation processing."""
    
    # Document content
    document_text: str
    document_metadata: Dict[str, Any]
    
    # Classification results
    classification_verdict: Dict[str, Any]
    
    # Processing context
    pipeline_id: str
    processing_timestamp: str
    user_session_id: str
    
    # KAG-specific configuration
    knowledge_extraction_config: Dict[str, Any]
    
    # Downstream processing hints
    processing_hints: Dict[str, Any]


@dataclass
class KAGOutput:
    """Output from KAG processing."""
    
    success: bool
    kag_input_path: str
    processing_summary: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class KAGComponent:
    """
    Knowledge Augmented Generation component that prepares document data
    for downstream knowledge processing workflows.
    """
    
    def __init__(self):
        """Initialize the KAG component."""
        self.component_version = "1.0.0"
        logger.info("KAGComponent initialized for MVP prototype")
    
    def _extract_document_insights(self, document_text: str, classification_verdict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract document insights based on classification results.
        
        Args:
            document_text: The parsed document text
            classification_verdict: Classification results from regex classifier
            
        Returns:
            Dictionary of extracted insights
        """
        insights = {
            "text_statistics": {
                "length": len(document_text),
                "word_count": len(document_text.split()),
                "line_count": len(document_text.split('\n')),
                "paragraph_count": len([p for p in document_text.split('\n\n') if p.strip()])
            },
            
            "classification_insights": {
                "primary_category": classification_verdict.get("label", "Unknown"),
                "confidence_level": classification_verdict.get("confidence", "very_low"),
                "classification_score": classification_verdict.get("score", 0.0),
                "total_pattern_matches": classification_verdict.get("total_matches", 0),
                "pattern_diversity": len(classification_verdict.get("matched_patterns", []))
            },
            
            "document_characteristics": {
                "has_legal_content": classification_verdict.get("score", 0.0) > 0.1,
                "document_complexity": self._assess_complexity(document_text, classification_verdict),
                "key_topics": self._extract_key_topics(classification_verdict),
                "legal_domains": self._extract_legal_domains(classification_verdict)
            }
        }
        
        return insights
    
    def _assess_complexity(self, document_text: str, classification_verdict: Dict[str, Any]) -> str:
        """Assess document complexity based on various factors."""
        text_length = len(document_text)
        pattern_matches = classification_verdict.get("total_matches", 0)
        pattern_diversity = len(classification_verdict.get("matched_patterns", []))
        
        # Simple heuristic for complexity assessment
        if text_length > 5000 and pattern_matches > 20 and pattern_diversity > 10:
            return "high"
        elif text_length > 2000 and pattern_matches > 10 and pattern_diversity > 5:
            return "medium"
        else:
            return "low"
    
    def _extract_key_topics(self, classification_verdict: Dict[str, Any]) -> List[str]:
        """Extract key topics from matched patterns."""
        matched_patterns = classification_verdict.get("matched_patterns", [])
        
        # Group by subcategory and get most frequent ones
        subcategory_counts = {}
        for pattern in matched_patterns:
            subcategory = pattern.get("subcategory", "unknown")
            subcategory_counts[subcategory] = subcategory_counts.get(subcategory, 0) + pattern.get("frequency", 0)
        
        # Return top 5 subcategories by frequency
        sorted_topics = sorted(subcategory_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic[0] for topic in sorted_topics[:5]]
    
    def _extract_legal_domains(self, classification_verdict: Dict[str, Any]) -> List[str]:
        """Extract legal domains from classification results."""
        category_scores = classification_verdict.get("category_scores", {})
        
        # Return categories with significant scores (> 0.1)
        significant_domains = [
            category for category, score in category_scores.items()
            if score > 0.1
        ]
        
        # Sort by score descending
        significant_domains.sort(key=lambda x: category_scores[x], reverse=True)
        return significant_domains[:3]  # Top 3 domains
    
    def _create_knowledge_extraction_config(self, classification_verdict: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration for knowledge extraction based on classification."""
        primary_category = classification_verdict.get("label", "Unknown")
        confidence = classification_verdict.get("confidence", "very_low")
        
        config = {
            "extraction_strategy": "regex_enhanced",
            "confidence_threshold": 0.1,  # Low threshold for MVP
            "focus_areas": [],
            "processing_modes": ["text_analysis", "pattern_extraction"],
            "quality_assurance": {
                "validate_extraction": True,
                "confidence_weighting": True,
                "fallback_enabled": True
            }
        }
        
        # Adjust configuration based on classification results
        if confidence in ["high", "medium"]:
            config["focus_areas"] = self._extract_key_topics(classification_verdict)
            config["processing_modes"].append("domain_specific_extraction")
        
        if primary_category != "Unknown":
            config["processing_modes"].append("category_specific_processing")
            config["primary_domain"] = primary_category
        
        return config
    
    def _create_processing_hints(self, document_text: str, classification_verdict: Dict[str, Any]) -> Dict[str, Any]:
        """Create processing hints for downstream components."""
        hints = {
            "document_type": classification_verdict.get("label", "Unknown"),
            "processing_priority": "standard",
            "quality_indicators": {
                "text_quality": "good" if len(document_text) > 100 else "poor",
                "classification_confidence": classification_verdict.get("confidence", "very_low"),
                "pattern_richness": "high" if classification_verdict.get("total_matches", 0) > 10 else "low"
            },
            "recommended_workflows": [],
            "preprocessing_notes": []
        }
        
        # Add workflow recommendations based on classification
        primary_category = classification_verdict.get("label", "Unknown")
        confidence = classification_verdict.get("confidence", "very_low")
        
        if confidence in ["high", "medium"]:
            hints["recommended_workflows"].append("automated_extraction")
            hints["processing_priority"] = "high"
        else:
            hints["recommended_workflows"].append("manual_review_recommended")
            hints["preprocessing_notes"].append("Low classification confidence - manual review suggested")
        
        if primary_category in ["Property_and_Real_Estate", "Business_and_Corporate", "Financial_and_Security"]:
            hints["recommended_workflows"].append("structured_data_extraction")
            hints["recommended_workflows"].append("compliance_analysis")
        
        return hints
    
    def process_document(
        self,
        document_text: str,
        classification_verdict: Dict[str, Any],
        document_metadata: Dict[str, Any],
        pipeline_id: str,
        user_session_id: str,
        artifacts_folder: Path
    ) -> KAGOutput:
        """
        Process document for Knowledge Augmented Generation.
        
        Args:
            document_text: Parsed text from DocAI
            classification_verdict: Results from regex classifier
            document_metadata: Additional document metadata
            pipeline_id: Pipeline identifier
            user_session_id: User session identifier
            artifacts_folder: Folder to save KAG artifacts
            
        Returns:
            KAGOutput with processing results
        """
        errors = []
        warnings = []
        processing_timestamp = datetime.utcnow().isoformat()
        
        try:
            logger.info(f"Processing document for KAG (Pipeline: {pipeline_id})")
            
            # Extract document insights
            document_insights = self._extract_document_insights(document_text, classification_verdict)
            
            # Create knowledge extraction configuration
            knowledge_config = self._create_knowledge_extraction_config(classification_verdict)
            
            # Create processing hints
            processing_hints = self._create_processing_hints(document_text, classification_verdict)
            
            # Create KAG input structure
            kag_input = KAGInput(
                document_text=document_text,
                document_metadata={
                    **document_metadata,
                    "insights": document_insights
                },
                classification_verdict=classification_verdict,
                pipeline_id=pipeline_id,
                processing_timestamp=processing_timestamp,
                user_session_id=user_session_id,
                knowledge_extraction_config=knowledge_config,
                processing_hints=processing_hints
            )
            
            # Convert to dictionary for JSON serialization
            kag_input_dict = asdict(kag_input)
            
            # Add KAG processing metadata
            kag_input_dict["kag_metadata"] = {
                "component_version": self.component_version,
                "processing_timestamp": processing_timestamp,
                "mvp_mode": True,
                "vertex_embedding_disabled": True,
                "classification_method": "regex_pattern_matching",
                "knowledge_extraction_approach": "text_and_pattern_based"
            }
            
            # Save KAG input to artifacts folder
            kag_input_path = artifacts_folder / "kag_input.json"
            
            with open(kag_input_path, 'w', encoding='utf-8') as f:
                json.dump(kag_input_dict, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"KAG input saved to: {kag_input_path}")
            
            # Create processing summary
            processing_summary = {
                "document_processed": True,
                "classification_integrated": True,
                "knowledge_config_created": True,
                "insights_extracted": True,
                "artifacts_generated": ["kag_input.json"],
                "document_characteristics": document_insights["document_characteristics"],
                "processing_recommendations": processing_hints["recommended_workflows"]
            }
            
            return KAGOutput(
                success=True,
                kag_input_path=str(kag_input_path),
                processing_summary=processing_summary,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"KAG processing failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            return KAGOutput(
                success=False,
                kag_input_path="",
                processing_summary={"error": error_msg},
                errors=errors,
                warnings=warnings
            )
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get current KAG component status."""
        return {
            "component": "KAGComponent",
            "version": self.component_version,
            "status": "ready",
            "mvp_mode": True,
            "features": {
                "document_processing": True,
                "classification_integration": True,
                "knowledge_extraction": True,
                "artifact_generation": True,
                "vertex_embedding": False  # Disabled for MVP
            }
        }


def create_kag_component() -> KAGComponent:
    """Factory function to create a KAG component instance."""
    return KAGComponent()


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Create KAG component
    kag = create_kag_component()
    
    # Test with sample data
    sample_text = """
    This is a sale deed executed between the vendor and vendee for the transfer of property.
    The consideration amount is Rs. 50,00,000/- and the property is located in Mumbai.
    """
    
    sample_classification = {
        "label": "Property_and_Real_Estate",
        "score": 0.85,
        "confidence": "high",
        "total_matches": 15,
        "matched_patterns": [
            {"keyword": "sale deed", "subcategory": "sale_deeds", "frequency": 2}
        ],
        "category_scores": {"Property_and_Real_Estate": 0.85}
    }
    
    sample_metadata = {"filename": "test_document.pdf"}
    
    # Create temporary artifacts folder
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        artifacts_folder = Path(temp_dir)
        
        result = kag.process_document(
            document_text=sample_text,
            classification_verdict=sample_classification,
            document_metadata=sample_metadata,
            pipeline_id="test-pipeline-123",
            user_session_id="test-user-456",
            artifacts_folder=artifacts_folder
        )
        
        print(f"KAG Processing Result: {result.success}")
        if result.success:
            print(f"KAG Input saved to: {result.kag_input_path}")
            with open(result.kag_input_path, 'r') as f:
                print(json.dumps(json.load(f), indent=2))