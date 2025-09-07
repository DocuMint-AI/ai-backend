"""
OCR processing module using Google Vision API.

This module provides a wrapper for Google Cloud Vision OCR functionality,
offering clean interfaces for text extraction from images.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any

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
    Result of OCR processing containing extracted text and metadata.
    
    Attributes:
        text: The complete extracted text
        blocks: List of text blocks with positioning information
        confidence: Overall confidence score (0.0 to 1.0)
    """
    text: str
    blocks: List[Dict[str, Any]]
    confidence: float


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
    
    def extract_text(self, image_path: str) -> OCRResult:
        """
        Extract text from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            OCRResult containing extracted text, blocks, and confidence
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            gcp_exceptions.GoogleAPIError: If Vision API call fails
            
        Example:
            >>> ocr = GoogleVisionOCR("project-id", "creds.json")
            >>> result = ocr.extract_text("document.jpg")
            >>> print(f"Extracted: {result.text}")
            >>> print(f"Confidence: {result.confidence}")
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
            
            logger.info(f"Processing image: {image_path}")
            return self.extract_from_bytes(image_bytes)
            
        except Exception as e:
            logger.error(f"Failed to extract text from {image_path}: {e}")
            raise
    
    def extract_from_bytes(self, image_bytes: bytes) -> OCRResult:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Raw image data as bytes
            
        Returns:
            OCRResult containing extracted text, blocks, and confidence
            
        Raises:
            gcp_exceptions.GoogleAPIError: If Vision API call fails
            
        Example:
            >>> with open("image.jpg", "rb") as f:
            ...     image_data = f.read()
            >>> result = ocr.extract_from_bytes(image_data)
            >>> print(result.text)
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
            
            # Parse response into OCRResult
            return self._parse_response(response)
            
        except gcp_exceptions.GoogleAPIError as e:
            logger.error(f"Google Vision API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during OCR processing: {e}")
            raise
    
    def _parse_response(self, response: vision.AnnotateImageResponse) -> OCRResult:
        """
        Parse Google Vision API response into OCRResult.
        
        Args:
            response: Vision API response object
            
        Returns:
            Parsed OCRResult with text, blocks, and confidence
        """
        # Extract full text
        full_text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        # Extract text blocks with metadata
        blocks = []
        total_confidence = 0.0
        confidence_count = 0
        
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    block_text = ""
                    block_confidence = 0.0
                    word_count = 0
                    
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = "".join([symbol.text for symbol in word.symbols])
                            block_text += word_text + " "
                            
                            if word.confidence:
                                block_confidence += word.confidence
                                word_count += 1
                    
                    # Calculate average confidence for this block
                    avg_confidence = block_confidence / word_count if word_count > 0 else 0.0
                    total_confidence += avg_confidence
                    confidence_count += 1
                    
                    # Get bounding box coordinates
                    vertices = []
                    if block.bounding_box:
                        vertices = [
                            {"x": vertex.x, "y": vertex.y} 
                            for vertex in block.bounding_box.vertices
                        ]
                    
                    blocks.append({
                        "text": block_text.strip(),
                        "confidence": avg_confidence,
                        "bounding_box": vertices
                    })
        
        # Calculate overall confidence
        overall_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        logger.info(f"OCR completed: {len(blocks)} blocks, confidence: {overall_confidence:.2f}")
        
        return OCRResult(
            text=full_text.strip(),
            blocks=blocks,
            confidence=overall_confidence
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
