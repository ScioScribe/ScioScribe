"""
Data models for the data cleaning agent system.

This module defines the Pydantic models used throughout the data cleaning pipeline.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProcessingStatus(str, Enum):
    """Status of data artifact processing."""
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    READY_FOR_ANALYSIS = "ready_for_analysis"
    ERROR = "error"


class SuggestionType(str, Enum):
    """Types of data quality suggestions."""
    STANDARDIZE_CATEGORICAL = "standardize_categorical"
    CONVERT_DATATYPE = "convert_datatype"
    HANDLE_OUTLIERS = "handle_outliers"
    FILL_MISSING_VALUES = "fill_missing_values"
    FORMAT_STANDARDIZATION = "format_standardization"


class FileMetadata(BaseModel):
    """Metadata for uploaded files."""
    name: str
    path: str
    size: int
    mime_type: str
    uploaded_at: datetime


class ProcessingResult(BaseModel):
    """Result of file processing."""
    success: bool
    data_preview: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None


class QualityIssue(BaseModel):
    """Represents a data quality issue."""
    issue_id: str
    column: str
    issue_type: str
    description: str
    severity: str  # "low", "medium", "high"
    affected_rows: int


class Suggestion(BaseModel):
    """AI-generated suggestion for data improvement."""
    suggestion_id: str
    type: SuggestionType
    column: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: str  # "low", "medium", "high"
    transformation: Dict[str, Any]
    explanation: str


class DataArtifact(BaseModel):
    """Main data artifact model."""
    artifact_id: str
    experiment_id: str
    owner_id: str
    status: ProcessingStatus
    original_file: FileMetadata
    cleaned_file: Optional[FileMetadata] = None
    suggestions: List[Suggestion] = []
    quality_score: Optional[float] = None
    notes: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApplySuggestionRequest(BaseModel):
    """Request to apply a suggestion."""
    artifact_id: str
    suggestion_id: str
    action: str  # "accept" or "reject"


class UpdateNotesRequest(BaseModel):
    """Request to update notes."""
    artifact_id: str
    notes: str 