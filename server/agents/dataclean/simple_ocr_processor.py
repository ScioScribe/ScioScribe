"""
Simple OCR Processor for ScioScribe Data Cleaning System.

This module provides basic OCR capabilities for extracting text from images
without complex table detection. This is a simplified version that avoids
OpenCV dependencies for initial testing.
"""

import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum
import re
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class ImageQuality(Enum):
    """Image quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

@dataclass
class SimpleOCRResult:
    """Simple OCR extraction result"""
    extracted_data: pd.DataFrame
    confidence: float
    quality: ImageQuality
    processing_notes: List[str]
    raw_text: str

class SimpleOCRProcessor:
    """
    Simple OCR processor for extracting text from images.
    
    This version focuses on basic OCR functionality without complex
    table detection, making it easier to test and debug.
    """
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize the SimpleOCRProcessor.
        
        Args:
            tesseract_path: Optional path to Tesseract executable
        """
        self.tesseract_path = tesseract_path
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # OCR configuration for better text recognition
        self.ocr_config = r'--oem 3 --psm 6'
        
        logger.info("SimpleOCRProcessor initialized successfully")
    
    async def process_image(self, image_path: str) -> SimpleOCRResult:
        """
        Process an image and extract text data.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            SimpleOCRResult containing extracted DataFrame and metadata
        """
        try:
            logger.info(f"Processing image: {image_path}")
            
            # Load and validate image
            image = await self._load_image(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Assess image quality
            quality = await self._assess_image_quality(image)
            processing_notes = [f"Initial image quality: {quality.value}"]
            
            # Enhance image for better OCR
            enhanced_image = await self._enhance_image(image)
            processing_notes.append("Applied image enhancement")
            
            # Extract text using OCR
            raw_text = await self._extract_text_ocr(enhanced_image)
            processing_notes.append(f"Extracted {len(raw_text)} characters")
            
            # Parse text into structured data
            dataframe = await self._parse_text_to_dataframe(raw_text)
            processing_notes.append(f"Created DataFrame: {dataframe.shape[0]}x{dataframe.shape[1]}")
            
            # Calculate confidence
            confidence = await self._calculate_confidence(dataframe, quality, raw_text)
            
            return SimpleOCRResult(
                extracted_data=dataframe,
                confidence=confidence,
                quality=quality,
                processing_notes=processing_notes,
                raw_text=raw_text
            )
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            # Return empty result with error information
            return SimpleOCRResult(
                extracted_data=pd.DataFrame(),
                confidence=0.0,
                quality=ImageQuality.POOR,
                processing_notes=[f"Error: {str(e)}"],
                raw_text=""
            )
    
    async def _load_image(self, image_path: str) -> Optional[Image.Image]:
        """Load image from file path"""
        try:
            return Image.open(image_path)
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {str(e)}")
            return None
    
    async def _assess_image_quality(self, image: Image.Image) -> ImageQuality:
        """Assess the quality of the input image"""
        try:
            # Convert to grayscale for analysis
            gray_image = image.convert('L')
            img_array = np.array(gray_image)
            
            # Calculate image statistics
            mean_intensity = np.mean(img_array)
            std_intensity = np.std(img_array)
            
            # Assess contrast (higher std = better contrast)
            contrast_score = std_intensity / 255.0
            
            # Assess brightness (closer to 128 = better)
            brightness_score = 1.0 - abs(mean_intensity - 128) / 128.0
            
            # Overall quality score
            quality_score = (contrast_score + brightness_score) / 2.0
            
            if quality_score > 0.7:
                return ImageQuality.EXCELLENT
            elif quality_score > 0.5:
                return ImageQuality.GOOD
            elif quality_score > 0.3:
                return ImageQuality.FAIR
            else:
                return ImageQuality.POOR
                
        except Exception as e:
            logger.warning(f"Image quality assessment failed: {str(e)}")
            return ImageQuality.FAIR
    
    async def _enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Enhance image quality for better OCR accuracy.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Enhanced PIL Image
        """
        try:
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Apply noise reduction
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Resize if too small (minimum 300 DPI equivalent)
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {str(e)}")
            return image
    
    async def _extract_text_ocr(self, image: Image.Image) -> str:
        """Extract text from image using Tesseract OCR"""
        try:
            # Use Tesseract with configuration
            text = pytesseract.image_to_string(image, config=self.ocr_config)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return ""
    
    async def _parse_text_to_dataframe(self, text: str) -> pd.DataFrame:
        """Parse extracted text into a pandas DataFrame"""
        try:
            if not text.strip():
                return pd.DataFrame()
            
            # Split text into lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if not lines:
                return pd.DataFrame()
            
            # Try to identify table structure from text
            rows = []
            for line in lines:
                # Try different delimiters
                if '\t' in line:
                    row = [cell.strip() for cell in line.split('\t')]
                elif '|' in line:
                    row = [cell.strip() for cell in line.split('|') if cell.strip()]
                elif '  ' in line:  # Multiple spaces
                    row = [cell.strip() for cell in re.split(r'\s{2,}', line) if cell.strip()]
                else:
                    # Single column or space-separated
                    row = [cell.strip() for cell in line.split() if cell.strip()]
                
                if row:
                    rows.append(row)
            
            if not rows:
                return pd.DataFrame()
            
            # Normalize row lengths
            max_cols = max(len(row) for row in rows)
            normalized_rows = []
            for row in rows:
                # Pad short rows with empty strings
                while len(row) < max_cols:
                    row.append('')
                normalized_rows.append(row[:max_cols])  # Truncate long rows
            
            # Create DataFrame
            if len(normalized_rows) > 1:
                # First row might be headers
                df = pd.DataFrame(normalized_rows[1:], columns=normalized_rows[0])
            else:
                df = pd.DataFrame(normalized_rows)
            
            # Clean up DataFrame
            df = df.replace('', np.nan)  # Replace empty strings with NaN
            df = df.dropna(how='all')  # Remove completely empty rows
            df = df.loc[:, ~df.columns.duplicated()]  # Remove duplicate columns
            
            return df
            
        except Exception as e:
            logger.error(f"Text parsing failed: {str(e)}")
            return pd.DataFrame()
    
    async def _calculate_confidence(self, dataframe: pd.DataFrame, quality: ImageQuality, raw_text: str) -> float:
        """Calculate confidence score for the OCR extraction"""
        try:
            confidence_factors = []
            
            # Data completeness factor
            if not dataframe.empty:
                total_cells = dataframe.shape[0] * dataframe.shape[1]
                filled_cells = dataframe.count().sum()
                completeness = filled_cells / total_cells if total_cells > 0 else 0
                confidence_factors.append(completeness)
            else:
                confidence_factors.append(0.0)
            
            # Image quality factor
            quality_scores = {
                ImageQuality.EXCELLENT: 1.0,
                ImageQuality.GOOD: 0.8,
                ImageQuality.FAIR: 0.6,
                ImageQuality.POOR: 0.3
            }
            confidence_factors.append(quality_scores[quality])
            
            # Text extraction factor (based on text length and structure)
            if raw_text:
                text_length_score = min(1.0, len(raw_text) / 100.0)  # Normalize to 100 chars
                confidence_factors.append(text_length_score)
            else:
                confidence_factors.append(0.0)
            
            # Calculate weighted average
            final_confidence = sum(confidence_factors) / len(confidence_factors)
            return min(1.0, max(0.0, final_confidence))
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return 0.3
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        return ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp']
    
    async def validate_image_file(self, file_path: str) -> bool:
        """Validate if file is a supported image format"""
        try:
            with Image.open(file_path) as img:
                # Try to load the image
                img.verify()
                return True
        except Exception:
            return False 