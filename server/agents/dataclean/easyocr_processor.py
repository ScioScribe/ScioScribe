"""
EasyOCR Processor for ScioScribe Data Cleaning System.

This module provides OCR capabilities using EasyOCR, a modern deep learning-based
OCR library that offers better accuracy than pytesseract and supports 80+ languages.
"""

import pandas as pd
import easyocr
import numpy as np
from PIL import Image
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logger = logging.getLogger(__name__)

class ImageQuality(Enum):
    """Image quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

@dataclass
class EasyOCRResult:
    """EasyOCR extraction result with confidence and metadata"""
    extracted_data: pd.DataFrame
    confidence: float
    quality: ImageQuality
    processing_notes: List[str]
    raw_text: str
    detected_text_boxes: List[Dict[str, Any]]  # Raw EasyOCR results

class EasyOCRProcessor:
    """
    OCR processor using EasyOCR for text extraction from images.
    
    EasyOCR advantages:
    - Deep learning-based (PyTorch)
    - 80+ language support
    - Better accuracy than pytesseract
    - GPU acceleration support
    - No complex setup required
    """
    
    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = True):
        """
        Initialize the EasyOCR processor.
        
        Args:
            languages: List of language codes (e.g., ['en', 'es', 'fr'])
            gpu: Whether to use GPU acceleration (if available)
        """
        self.languages = languages or ['en']  # Default to English
        self.gpu = gpu
        self.reader = None
        
        # Initialize EasyOCR reader
        self._initialize_reader()
        
        logger.info(f"EasyOCRProcessor initialized with languages: {self.languages}")
    
    def _initialize_reader(self):
        """Initialize the EasyOCR reader"""
        try:
            self.reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                verbose=False  # Reduce verbose output
            )
            logger.info(f"EasyOCR reader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR reader: {str(e)}")
            raise
    
    async def process_image(self, image_path: str) -> EasyOCRResult:
        """
        Process an image and extract text using EasyOCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            EasyOCRResult containing extracted DataFrame and metadata
        """
        try:
            logger.info(f"Processing image with EasyOCR: {image_path}")
            
            # Load and validate image
            image = await self._load_image(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Assess image quality
            quality = await self._assess_image_quality(image)
            processing_notes = [f"Initial image quality: {quality.value}"]
            
            # Convert PIL image to numpy array for EasyOCR
            image_array = np.array(image)
            
            # Extract text using EasyOCR
            detected_text_boxes = await self._extract_text_easyocr(image_array)
            processing_notes.append(f"Detected {len(detected_text_boxes)} text regions")
            
            # Process results into structured format
            raw_text, dataframe = await self._process_easyocr_results(detected_text_boxes)
            processing_notes.append(f"Extracted {len(raw_text)} characters")
            processing_notes.append(f"Created DataFrame: {dataframe.shape[0]}x{dataframe.shape[1]}")
            
            # Calculate confidence score
            confidence = await self._calculate_confidence(detected_text_boxes, quality)
            
            return EasyOCRResult(
                extracted_data=dataframe,
                confidence=confidence,
                quality=quality,
                processing_notes=processing_notes,
                raw_text=raw_text,
                detected_text_boxes=detected_text_boxes
            )
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            # Return empty result with error information
            return EasyOCRResult(
                extracted_data=pd.DataFrame(),
                confidence=0.0,
                quality=ImageQuality.POOR,
                processing_notes=[f"Error: {str(e)}"],
                raw_text="",
                detected_text_boxes=[]
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
            
            # Check image size
            width, height = image.size
            size_score = min(1.0, (width * height) / (800 * 600))  # Normalize to 800x600
            
            # Assess contrast (higher std = better contrast)
            contrast_score = std_intensity / 255.0
            
            # Assess brightness (closer to 128 = better)
            brightness_score = 1.0 - abs(mean_intensity - 128) / 128.0
            
            # Overall quality score
            quality_score = (contrast_score + brightness_score + size_score) / 3.0
            
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
    
    async def _extract_text_easyocr(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """Extract text from image using EasyOCR"""
        try:
            # Run EasyOCR in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                results = await loop.run_in_executor(
                    executor,
                    self.reader.readtext,
                    image_array
                )
            
            # Process EasyOCR results
            detected_text_boxes = []
            for result in results:
                bbox, text, confidence = result
                
                # Convert bbox to consistent format
                # EasyOCR returns 4 corner points
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                
                detected_text_boxes.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox,
                    'x_min': min(x_coords),
                    'y_min': min(y_coords),
                    'x_max': max(x_coords),
                    'y_max': max(y_coords)
                })
            
            return detected_text_boxes
            
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {str(e)}")
            return []
    
    async def _process_easyocr_results(self, detected_text_boxes: List[Dict[str, Any]]) -> Tuple[str, pd.DataFrame]:
        """Process EasyOCR results into raw text and structured DataFrame"""
        try:
            if not detected_text_boxes:
                return "", pd.DataFrame()
            
            # Sort text boxes by position (top to bottom, left to right)
            sorted_boxes = sorted(detected_text_boxes, key=lambda x: (x['y_min'], x['x_min']))
            
            # Extract raw text
            raw_text = ' '.join([box['text'] for box in sorted_boxes])
            
            # Try to detect table structure
            dataframe = await self._create_dataframe_from_text_boxes(sorted_boxes)
            
            return raw_text, dataframe
            
        except Exception as e:
            logger.error(f"Failed to process EasyOCR results: {str(e)}")
            return "", pd.DataFrame()
    
    async def _create_dataframe_from_text_boxes(self, text_boxes: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create DataFrame from positioned text boxes"""
        try:
            if not text_boxes:
                return pd.DataFrame()
            
            # Group text boxes into rows based on Y-coordinate proximity
            rows = []
            current_row = []
            current_y = text_boxes[0]['y_min']
            y_threshold = 20  # Pixels threshold for same row
            
            for box in text_boxes:
                if abs(box['y_min'] - current_y) <= y_threshold:
                    # Same row
                    current_row.append(box)
                else:
                    # New row
                    if current_row:
                        # Sort current row by x-coordinate
                        current_row.sort(key=lambda x: x['x_min'])
                        rows.append(current_row)
                    current_row = [box]
                    current_y = box['y_min']
            
            # Add the last row
            if current_row:
                current_row.sort(key=lambda x: x['x_min'])
                rows.append(current_row)
            
            # Convert to DataFrame
            if not rows:
                return pd.DataFrame()
            
            # Find maximum number of columns
            max_cols = max(len(row) for row in rows)
            
            # Create table data
            table_data = []
            for row in rows:
                row_data = [box['text'] for box in row]
                # Pad with empty strings if needed
                while len(row_data) < max_cols:
                    row_data.append('')
                table_data.append(row_data)
            
            # Create DataFrame
            if len(table_data) > 1:
                # First row as headers
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
            else:
                df = pd.DataFrame(table_data)
            
            # Clean up DataFrame
            df = df.replace('', np.nan).infer_objects(copy=False)
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.duplicated()]
            
            return df
            
        except Exception as e:
            logger.error(f"DataFrame creation failed: {str(e)}")
            return pd.DataFrame()
    
    async def _calculate_confidence(self, detected_text_boxes: List[Dict[str, Any]], quality: ImageQuality) -> float:
        """Calculate overall confidence score"""
        try:
            confidence_factors = []
            
            # EasyOCR confidence factor
            if detected_text_boxes:
                avg_confidence = sum(box['confidence'] for box in detected_text_boxes) / len(detected_text_boxes)
                confidence_factors.append(avg_confidence)
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
            
            # Text detection completeness factor
            if detected_text_boxes:
                # More detected text boxes usually means better coverage
                detection_score = min(1.0, len(detected_text_boxes) / 10.0)  # Normalize to 10 boxes
                confidence_factors.append(detection_score)
            else:
                confidence_factors.append(0.0)
            
            # Calculate weighted average
            final_confidence = sum(confidence_factors) / len(confidence_factors)
            return min(1.0, max(0.0, final_confidence))
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return 0.3
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        # EasyOCR supported languages
        return [
            'en', 'zh', 'ja', 'ko', 'th', 'vi', 'ar', 'bg', 'cs', 'da', 'de',
            'el', 'es', 'et', 'fi', 'fr', 'hr', 'hu', 'id', 'it', 'lt', 'lv',
            'mt', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sv', 'tr',
            'hi', 'bn', 'ta', 'te', 'kn', 'ml', 'mr', 'ne', 'si', 'ur', 'fa',
            'he', 'my', 'ka', 'am', 'hy', 'az', 'be', 'bs', 'cy', 'gl', 'ga',
            'is', 'mk', 'mn', 'eu', 'ca', 'la', 'co', 'eo', 'tl', 'fy', 'gd',
            'haw', 'jv', 'ku', 'lo', 'mi', 'oc', 'sm', 'sn', 'so', 'su', 'sw',
            'ty', 'yi', 'yo', 'zu'
        ]
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        return ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp']
    
    async def validate_image_file(self, file_path: str) -> bool:
        """Validate if file is a supported image format"""
        try:
            with Image.open(file_path) as img:
                img.verify()
                return True
        except Exception:
            return False
    
    def set_languages(self, languages: List[str]):
        """Change the languages for OCR processing"""
        self.languages = languages
        self._initialize_reader()
        logger.info(f"Updated languages to: {self.languages}")
    
    def enable_gpu(self, gpu: bool = True):
        """Enable or disable GPU acceleration"""
        if self.gpu != gpu:
            self.gpu = gpu
            self._initialize_reader()
            logger.info(f"GPU acceleration: {'enabled' if gpu else 'disabled'}")
    
    async def get_text_with_positions(self, image_path: str) -> List[Dict[str, Any]]:
        """Get text with bounding box positions (useful for advanced processing)"""
        try:
            image = await self._load_image(image_path)
            if image is None:
                return []
            
            image_array = np.array(image)
            detected_text_boxes = await self._extract_text_easyocr(image_array)
            
            return detected_text_boxes
            
        except Exception as e:
            logger.error(f"Failed to get text with positions: {str(e)}")
            return [] 