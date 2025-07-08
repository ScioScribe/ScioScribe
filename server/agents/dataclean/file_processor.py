"""
File Processing Agent for multi-modal data ingestion.

This agent handles the initial processing of uploaded files, converting them
to a standardized DataFrame format for further analysis.
"""

import os
import uuid
import pandas as pd
import chardet
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from .models import ProcessingResult, FileMetadata
from .easyocr_processor import EasyOCRProcessor

logger = logging.getLogger(__name__)


class FileProcessingAgent:
    """
    Agent responsible for processing various file formats and converting them
    to structured DataFrames for analysis.
    """

    def __init__(self):
        """Initialize the file processing agent."""
        self.supported_formats = ['.csv', '.xlsx', '.xls']
        
        # Initialize EasyOCR processor for image processing
        try:
            self.ocr_processor = EasyOCRProcessor(languages=['en'], gpu=False)
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"EasyOCR initialization failed: {str(e)}")
            self.ocr_processor = None
            
        self.image_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp']
        
    async def process_file(self, file_path: str, file_type: str) -> ProcessingResult:
        """
        Main processing entry point for uploaded files.
        
        Args:
            file_path: Path to the uploaded file
            file_type: MIME type of the file
            
        Returns:
            ProcessingResult with success status and processed data
        """
        try:
            logger.info(f"Processing file: {file_path}, type: {file_type}")
            
            # Determine file extension
            file_extension = Path(file_path).suffix.lower()
            
            # Check if file format is supported
            if file_extension not in self.supported_formats and file_extension not in self.image_formats:
                return ProcessingResult(
                    success=False,
                    error_message=f"Unsupported file format: {file_extension}"
                )
            
            # Process based on file type
            if file_extension == '.csv':
                dataframe = await self._process_csv(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                dataframe = await self._process_excel(file_path)
            elif file_extension in self.image_formats:
                dataframe = await self._process_image(file_path)
            else:
                return ProcessingResult(
                    success=False,
                    error_message=f"Handler not implemented for: {file_extension}"
                )
            
            # Generate data preview
            data_preview = self._generate_data_preview(dataframe)
            
            return ProcessingResult(
                success=True,
                data_preview=data_preview,
                file_info={
                    'shape': dataframe.shape,
                    'columns': list(dataframe.columns),
                    'dtypes': dataframe.dtypes.to_dict()
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return ProcessingResult(
                success=False,
                error_message=f"Processing failed: {str(e)}"
            )
    
    async def _process_csv(self, file_path: str) -> pd.DataFrame:
        """
        Process CSV files with encoding detection.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Processed DataFrame
        """
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding_result = chardet.detect(raw_data)
                encoding = encoding_result['encoding'] or 'utf-8'
            
            # Try to read with detected encoding
            try:
                df = pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                # Fallback to common encodings
                for enc in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(file_path, encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Could not determine file encoding")
            
            logger.info(f"Successfully processed CSV with shape: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {str(e)}")
            raise
    
    async def _process_excel(self, file_path: str) -> pd.DataFrame:
        """
        Process Excel files (XLSX/XLS).
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Processed DataFrame
        """
        try:
            # Read Excel file - use first sheet by default
            df = pd.read_excel(file_path, sheet_name=0)
            
            logger.info(f"Successfully processed Excel with shape: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Error processing Excel {file_path}: {str(e)}")
            raise
    
    async def _process_image(self, file_path: str) -> pd.DataFrame:
        """
        Process image files using EasyOCR to extract tabular data.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Processed DataFrame from OCR extraction
        """
        try:
            if not self.ocr_processor:
                logger.error("EasyOCR processor not available")
                return pd.DataFrame({'OCR_Error': ['OCR processor not available']})
            
            # Use EasyOCR to extract data
            ocr_result = await self.ocr_processor.process_image(file_path)
            
            if ocr_result and not ocr_result.extracted_data.empty:
                logger.info(f"Successfully processed image with EasyOCR. Shape: {ocr_result.extracted_data.shape}, Confidence: {ocr_result.confidence}")
                return ocr_result.extracted_data
            
            logger.warning(f"EasyOCR processing returned empty data for {file_path}")
            # Return empty DataFrame with placeholder structure
            return pd.DataFrame({'OCR_Error': ['No data extracted from image']})
                
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {str(e)}")
            # Return error information in DataFrame format
            return pd.DataFrame({'OCR_Error': [f"Processing failed: {str(e)}"]})
    
    def _generate_data_preview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a preview of the processed data.
        
        Args:
            df: Processed DataFrame
            
        Returns:
            Dictionary containing data preview information
        """
        preview = {
            'shape': df.shape,
            'columns': list(df.columns),
            'sample_rows': df.head(5).to_dict('records'),
            'column_types': df.dtypes.astype(str).to_dict(),
            'null_counts': df.isnull().sum().to_dict(),
            'basic_stats': {}
        }
        
        # Add basic statistics for numeric columns
        numeric_columns = df.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            preview['basic_stats'] = df[numeric_columns].describe().to_dict()
        
        return preview 