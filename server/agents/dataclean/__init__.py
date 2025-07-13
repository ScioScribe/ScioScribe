"""
Data Cleaning Agent Package - Simplified Version

This package provides a simple data processing service with 5 core tools:
- Analyze data for quality issues
- Clean data with standard operations
- Describe data overview
- Add rows to data
- Delete rows from data
"""

from .simple_processor import SimpleDataProcessor

__all__ = [
    'SimpleDataProcessor',
]

__version__ = '2.0.0'