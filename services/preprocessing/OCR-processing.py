"""
OCR processing module using Google Vision API.

This module provides a wrapper for Google Cloud Vision OCR functionality,
offering clean interfaces for text extraction from images.
"""

import logging
import os
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from google.cloud import vision
from google.api_core import exceptions as gcp_exceptions

# Optional dotenv support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("python-dotenv not installed. Environment variables must be set manually.")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """
    Enhanced OCR result following DocAI schema structure.
    
    Attributes:
        document_id: Unique identifier for the document
        original_filename: Name of the original file
        file_fingerprint: SHA256 hash of the file content
        pdf_uri: Optional GCS URI for the PDF
        derived_images: List of generated image metadata
        language_detection: Detected language information
        ocr_result: Main OCR results with pages array
        extracted_assets: Signatures, tables, etc.
        preprocessing: Pipeline metadata
        warnings: List of processing warnings
    """
    document_id: str
    original_filename: str
    file_fingerprint: str
    pdf_uri: Optional[str]
    derived_images: List[Dict[str, Any]]
    language_detection: Dict[str, Any]
    ocr_result: Dict[str, Any]
    extracted_assets: Dict[str, Any]
    preprocessing: Dict[str, Any]
    warnings: List[Dict[str, Any]]


class GoogleVisionOCR:
    """
    Google Cloud Vision API wrapper for OCR processing.
    
    Provides methods to extract text from images using Google's powerful
    OCR capabilities with configurable language hints and error handling.
    """
    
    def __init__(
        self, 
        project_id: str, 
        credentials_path: str, 
        language_hints: Optional[List[str]] = None
    ) -> None:
        """
        Initialize Google Vision OCR client.
        
        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account credentials JSON
            language_hints: Optional list of language codes (e.g., ['en', 'es'])
            
        Example:
            >>> ocr = GoogleVisionOCR(
            ...     project_id="my-project",
            ...     credentials_path="/path/to/credentials.json",
            ...     language_hints=["en", "es"]
            ... )
        """
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.language_hints = language_hints or ["en"]
        
        try:
            # Initialize Vision API client
            self.client = vision.ImageAnnotatorClient.from_service_account_file(
                credentials_path
            )
            logger.info(f"Initialized Google Vision OCR for project: {project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Vision client: {e}")
            raise
    
    @classmethod
    def from_env(cls, language_hints: Optional[List[str]] = None) -> "GoogleVisionOCR":
        """
        Create GoogleVisionOCR instance from environment variables.
        
        Environment variables required:
            GOOGLE_CLOUD_PROJECT_ID: Google Cloud project ID
            GOOGLE_CLOUD_CREDENTIALS_PATH: Path to service account credentials
            LANGUAGE_HINTS: Comma-separated language codes (optional)
        
        Args:
            language_hints: Override environment language hints
            
        Returns:
            GoogleVisionOCR instance
            
        Raises:
            ValueError: If required environment variables are missing
            
        Example:
            >>> # Set environment variables first
            >>> ocr = GoogleVisionOCR.from_env()
            >>> # or with custom language hints
            >>> ocr = GoogleVisionOCR.from_env(["en", "fr"])
        """
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
        
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID environment variable is required")
        if not credentials_path:
            raise ValueError("GOOGLE_CLOUD_CREDENTIALS_PATH environment variable is required")
        
        # Use provided language hints or get from environment
        if language_hints is None:
            env_hints = os.getenv("LANGUAGE_HINTS", "en")
            language_hints = [hint.strip() for hint in env_hints.split(",")]
        
        logger.info(f"Creating OCR instance from environment: project={project_id}, hints={language_hints}")
        
        return cls(
            project_id=project_id,
            credentials_path=credentials_path,
            language_hints=language_hints
        )
    
    def extract_text(self, image_path: str, page_number: int = 1, image_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract text from an image file with enhanced DocAI-compatible output.
        
        Args:
            image_path: Path to the image file
            page_number: Page number in the document
            image_metadata: Optional image metadata (width, height, dpi, etc.)
            
        Returns:
            Dictionary containing structured OCR results for the page
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            gcp_exceptions.GoogleAPIError: If Vision API call fails
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
            
            logger.info(f"Processing image: {image_path} (page {page_number})")
            return self.extract_from_bytes(image_bytes, page_number, image_metadata)
            
        except Exception as e:
            logger.error(f"Failed to extract text from {image_path}: {e}")
            raise
    
    def extract_from_bytes(self, image_bytes: bytes, page_number: int = 1, image_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract text from image bytes with enhanced DocAI-compatible output.
        
        Args:
            image_bytes: Raw image data as bytes
            page_number: Page number in the document
            image_metadata: Optional image metadata (width, height, dpi, etc.)
            
        Returns:
            Dictionary containing structured OCR results for the page
            
        Raises:
            gcp_exceptions.GoogleAPIError: If Vision API call fails
        """
        try:
            # Create Vision API image object
            image = vision.Image(content=image_bytes)
            
            # Configure image context with language hints
            image_context = vision.ImageContext(language_hints=self.language_hints)
            
            # Perform text detection
            response = self.client.document_text_detection(
                image=image, 
                image_context=image_context
            )
            
            # Check for API errors
            if response.error.message:
                raise gcp_exceptions.GoogleAPIError(
                    f"Vision API error: {response.error.message}"
                )
            
            # Parse response into DocAI-compatible format
            return self._parse_response_docai_format(response, page_number, image_metadata)
            
        except gcp_exceptions.GoogleAPIError as e:
            logger.error(f"Google Vision API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during OCR processing: {e}")
            raise
    
    def _parse_response_docai_format(self, response: vision.AnnotateImageResponse, page_number: int, image_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Parse Google Vision API response into DocAI-compatible format.
        
        Args:
            response: Vision API response object
            page_number: Page number in the document
            image_metadata: Optional image metadata
            
        Returns:
            Dictionary containing DocAI-compatible page data
        """
        # Default image dimensions if not provided
        if image_metadata:
            width = image_metadata.get("width", 1240)
            height = image_metadata.get("height", 1754)
        else:
            width, height = 1240, 1754  # Default values
        
        # Extract full text
        full_text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        # Extract text blocks with metadata
        text_blocks = []
        page_warnings = []
        block_count = 0
        total_confidence = 0.0
        confidence_count = 0
        
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_count += 1
                    block_id = f"p{page_number}_b{block_count}"
                    
                    # Extract block text and process paragraphs/lines
                    lines = []
                    line_count = 0
                    block_text = ""
                    block_confidence = 0.0
                    word_count = 0
                    
                    for paragraph in block.paragraphs:
                        for line_words in self._group_words_into_lines(paragraph.words):
                            line_count += 1
                            line_id = f"{block_id}_l{line_count}"
                            
                            # Process words in this line
                            line_text = ""
                            line_confidence = 0.0
                            words_data = []
                            
                            for word in line_words:
                                word_text = "".join([symbol.text for symbol in word.symbols])
                                line_text += word_text + " "
                                
                                word_conf = word.confidence if hasattr(word, 'confidence') and word.confidence else 0.0
                                if word_conf > 0:
                                    line_confidence += word_conf
                                    word_count += 1
                                
                                # Convert word bounding box
                                word_bbox = self._convert_bounding_box(word.bounding_box, width, height)
                                
                                words_data.append({
                                    "text": word_text,
                                    "confidence": word_conf,
                                    "bounding_box": word_bbox
                                })
                            
                            # Calculate line confidence
                            avg_line_confidence = line_confidence / len(line_words) if len(line_words) > 0 else 0.0
                            
                            lines.append({
                                "line_id": line_id,
                                "text": line_text.strip(),
                                "confidence": avg_line_confidence,
                                "words": words_data
                            })
                            
                            block_text += line_text
                    
                    # Calculate block confidence
                    avg_block_confidence = block_confidence / word_count if word_count > 0 else 0.0
                    if word_count > 0:
                        total_confidence += avg_block_confidence
                        confidence_count += 1
                    
                    # Convert block bounding box
                    block_bbox = self._convert_bounding_box(block.bounding_box, width, height)
                    
                    # Check for low confidence warning
                    if avg_block_confidence < 0.7 and avg_block_confidence > 0:
                        page_warnings.append({
                            "page": page_number,
                            "block_id": block_id,
                            "code": "LOW_CONFIDENCE",
                            "message": f"Block confidence ({avg_block_confidence:.2f}) below threshold"
                        })
                    
                    text_blocks.append({
                        "block_id": block_id,
                        "page": page_number,
                        "bounding_box": block_bbox,
                        "text": block_text.strip(),
                        "confidence": avg_block_confidence,
                        "lines": lines
                    })
        
        # Sort blocks in reading order (top to bottom, left to right)
        text_blocks = self._sort_blocks_reading_order(text_blocks)
        
        # Calculate overall page confidence
        page_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        page_data = {
            "page": page_number,
            "width": width,
            "height": height,
            "page_confidence": page_confidence,
            "text_blocks": text_blocks
        }
        
        logger.info(f"Page {page_number} processed: {len(text_blocks)} blocks, confidence: {page_confidence:.2f}")
        
        return {
            "page_data": page_data,
            "warnings": page_warnings,
            "full_text": full_text.strip()
        }
    
    def _group_words_into_lines(self, words: List) -> List[List]:
        """
        Group words into lines based on their vertical positions.
        
        Args:
            words: List of word objects from Vision API
            
        Returns:
            List of lists, where each inner list contains words in the same line
        """
        if not words:
            return []
        
        # Sort words by vertical position first, then horizontal
        sorted_words = sorted(words, key=lambda w: (
            min([v.y for v in w.bounding_box.vertices]),
            min([v.x for v in w.bounding_box.vertices])
        ))
        
        lines = []
        current_line = []
        current_y = None
        y_threshold = 10  # Pixels tolerance for same line
        
        for word in sorted_words:
            word_y = min([v.y for v in word.bounding_box.vertices])
            
            if current_y is None or abs(word_y - current_y) <= y_threshold:
                current_line.append(word)
                current_y = word_y if current_y is None else (current_y + word_y) / 2
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [word]
                current_y = word_y
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _convert_bounding_box(self, bbox, page_width: int, page_height: int) -> List[List[int]]:
        """
        Convert Vision API bounding box to consistent numeric arrays.
        
        Args:
            bbox: Vision API bounding box object
            page_width: Page width in pixels
            page_height: Page height in pixels
            
        Returns:
            List of [x, y] coordinate pairs
        """
        if not bbox or not bbox.vertices:
            return [[0, 0], [0, 0], [0, 0], [0, 0]]
        
        coordinates = []
        for vertex in bbox.vertices:
            x = getattr(vertex, 'x', 0)
            y = getattr(vertex, 'y', 0)
            
            # Ensure coordinates are within page bounds
            x = max(0, min(x, page_width))
            y = max(0, min(y, page_height))
            
            coordinates.append([x, y])
        
        # Ensure we have exactly 4 coordinates
        while len(coordinates) < 4:
            coordinates.append([0, 0])
        
        return coordinates[:4]
    
    def _sort_blocks_reading_order(self, blocks: List[Dict]) -> List[Dict]:
        """
        Sort text blocks in reading order (top to bottom, left to right).
        
        Args:
            blocks: List of text block dictionaries
            
        Returns:
            Sorted list of blocks
        """
        def get_block_position(block):
            bbox = block.get("bounding_box", [[0, 0], [0, 0], [0, 0], [0, 0]])
            # Use top-left corner for sorting
            top = min(coord[1] for coord in bbox)
            left = min(coord[0] for coord in bbox)
            return (top, left)
        
        return sorted(blocks, key=get_block_position)
    
    @staticmethod
    def calculate_file_fingerprint(file_path: str) -> str:
        """
        Calculate SHA256 fingerprint of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash as hex string
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return f"sha256:{hasher.hexdigest()}"
    
    @staticmethod
    def detect_language_confidence(text: str, language_hints: List[str]) -> Dict[str, Any]:
        """
        Detect primary language and confidence from text.
        
        Args:
            text: Text to analyze
            language_hints: List of language hints used in OCR
            
        Returns:
            Dictionary with language detection results
        """
        # Simple heuristic - in a real implementation you might use langdetect or similar
        primary_language = language_hints[0] if language_hints else "en"
        
        # Calculate confidence based on text characteristics
        if not text.strip():
            confidence = 0.0
        elif len(text) < 10:
            confidence = 0.5
        else:
            # Simple confidence based on presence of common words
            english_words = ["the", "and", "is", "in", "to", "of", "a", "that", "it", "with"]
            word_count = len(text.split())
            english_count = sum(1 for word in text.lower().split() if word in english_words)
            confidence = min(0.98, max(0.3, english_count / max(1, word_count) * 2))
        
        return {
            "primary": primary_language,
            "confidence": confidence,
            "language_hints": language_hints
        }
    
    def create_docai_document(
        self, 
        document_id: str,
        original_filename: str,
        pdf_path: str,
        pages_data: List[Dict[str, Any]],
        derived_images: List[Dict[str, Any]],
        pdf_uri: Optional[str] = None
    ) -> OCRResult:
        """
        Create complete DocAI-compatible document structure.
        
        Args:
            document_id: Unique document identifier
            original_filename: Original filename
            pdf_path: Path to the original PDF
            pages_data: List of processed page data
            derived_images: List of image metadata
            pdf_uri: Optional GCS URI for the PDF
            
        Returns:
            Complete OCRResult in DocAI format
        """
        # Calculate file fingerprint
        file_fingerprint = self.calculate_file_fingerprint(pdf_path)
        
        # Collect all text from pages
        full_text_parts = []
        all_warnings = []
        
        # Build pages array
        pages = []
        for page_result in pages_data:
            page_data = page_result["page_data"]
            pages.append(page_data)
            
            # Collect page text
            page_text = "\n".join([block["text"] for block in page_data["text_blocks"]])
            full_text_parts.append(page_text)
            
            # Collect warnings
            all_warnings.extend(page_result.get("warnings", []))
        
        full_text = "\n\n".join(full_text_parts)
        
        # Detect language
        language_detection = self.detect_language_confidence(full_text, self.language_hints)
        
        # Create OCR result structure
        ocr_result = {
            "full_text": full_text,
            "pages": pages
        }
        
        # Add warnings if any
        if all_warnings:
            ocr_result["warnings"] = all_warnings
        
        # Create preprocessing metadata
        preprocessing = {
            "pipeline_version": "preproc-v2.4",
            "generated_at": datetime.now().isoformat()
        }
        
        # Create extracted assets (placeholder for now)
        extracted_assets = {
            "signatures": [],
            "tables": [],
            "key_value_pairs": []
        }
        
        return OCRResult(
            document_id=document_id,
            original_filename=original_filename,
            file_fingerprint=file_fingerprint,
            pdf_uri=pdf_uri,
            derived_images=derived_images,
            language_detection=language_detection,
            ocr_result=ocr_result,
            extracted_assets=extracted_assets,
            preprocessing=preprocessing,
            warnings=all_warnings
        )


if __name__ == "__main__":
    """
    Demo usage of GoogleVisionOCR.
    
    Set up environment variables in .env file:
        GOOGLE_CLOUD_PROJECT_ID=your-project-id
        GOOGLE_CLOUD_CREDENTIALS_PATH=/path/to/credentials.json
        LANGUAGE_HINTS=en,es
    """
    try:
        # Method 1: Using environment variables (recommended)
        print("Attempting to create OCR instance from environment variables...")
        try:
            ocr = GoogleVisionOCR.from_env()
            print("✓ OCR instance created successfully from environment!")
            print(f"  Project: {ocr.project_id}")
            print(f"  Language hints: {ocr.language_hints}")
        except ValueError as e:
            print(f"✗ Environment setup issue: {e}")
            print("\nPlease create a .env file with:")
            print("GOOGLE_CLOUD_PROJECT_ID=your-project-id")
            print("GOOGLE_CLOUD_CREDENTIALS_PATH=/path/to/credentials.json")
            print("LANGUAGE_HINTS=en,es")
        
        # Method 2: Direct instantiation (fallback)
        if 'ocr' not in locals():
            print("\nTrying direct instantiation with placeholder values...")
            ocr = GoogleVisionOCR(
                project_id="your-project-id",
                credentials_path="/path/to/your/credentials.json",
                language_hints=["en"]
            )
        
        # Example usage (uncomment when you have valid credentials)
        # result = ocr.extract_text("sample_document.jpg")
        # print(f"Extracted text: {result.text}")
        # print(f"Number of blocks: {len(result.blocks)}")
        # print(f"Overall confidence: {result.confidence:.2f}")
        
        print("\nGoogleVisionOCR module loaded successfully!")
        print("Set up valid credentials to test OCR functionality.")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        print("This is expected if Google Cloud credentials are not properly configured.")
