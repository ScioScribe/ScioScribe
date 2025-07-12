"""
Data Cleaning Agent System

This module contains the data cleaning and processing agents for ScioScribe:
- File processing for various formats (CSV, images, PDFs)
- OCR capabilities for extracting data from images
- Data quality analysis and suggestions
- Conversation-based data cleaning workflows
- Memory storage for data artifacts
"""

from .file_processor import FileProcessingAgent
from .quality_agent import DataQualityAgent
from .transformation_engine import TransformationEngine
from .complete_processor import CompleteFileProcessor
from .easyocr_processor import EasyOCRProcessor
from .csv_processor import CSVDirectProcessor

__all__ = [
    'FileProcessingAgent',
    'DataQualityAgent', 
    'TransformationEngine',
    'CompleteFileProcessor',
    'EasyOCRProcessor',
    'CSVDirectProcessor'
]