#!/usr/bin/env python3
"""
Create a test image with text for OCR testing.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image():
    """Create a simple test image with text."""
    
    # Create image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Add text content
    text_content = [
        "SAMPLE DOCUMENT",
        "",
        "This is a test document for OCR processing.",
        "It contains multiple lines of text to test",
        "the Google Vision API integration.",
        "",
        "Key Information:",
        "• Document Type: Test Sample",
        "• Date: September 15, 2025",
        "• Status: Active",
        "",
        "Contact: test@example.com",
        "Phone: (555) 123-4567"
    ]
    
    try:
        # Try to use a system font
        font_large = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 24)
        font_medium = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 16)
        font_small = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 14)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y_position = 50
    
    for i, line in enumerate(text_content):
        if not line.strip():  # Empty line
            y_position += 20
            continue
            
        if i == 0:  # Title
            font = font_large
            color = 'black'
        elif line.startswith("•") or ":" in line:
            font = font_small
            color = 'darkblue'
        else:
            font = font_medium
            color = 'black'
            
        draw.text((50, y_position), line, fill=color, font=font)
        y_position += 30 if font == font_large else 25
    
    return image

def main():
    """Create and save test image."""
    
        # Create test image directory (relative to script location)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    # Create the test image
    image_path = os.path.join(data_dir, "test_document.png")
    image.save(image_path, "PNG")
    
    print(f"✓ Test image created: {image_path}")
    print(f"  Image size: {image.size}")
    print(f"  Image mode: {image.mode}")
    
    return image_path

if __name__ == "__main__":
    main()