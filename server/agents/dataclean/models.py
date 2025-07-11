"""
Data models for the data cleaning agent system.

This module defines the Pydantic models used throughout the data cleaning pipeline.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
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


class TransformationAction(str, Enum):
    """Types of transformation actions."""
    REPLACE_VALUES = "replace_values"
    CONVERT_TYPE = "convert_type"
    FILL_MISSING = "fill_missing"
    REMOVE_OUTLIERS = "remove_outliers"
    STANDARDIZE_FORMAT = "standardize_format"
    ADD_ROW = "add_row"
    DELETE_ROW = "delete_row"


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


# === Phase 2.5: Interactive Transformation Models ===

class ValueMapping(BaseModel):
    """Mapping for transforming values in a column."""
    original_value: Any
    new_value: Any
    count: int = 0  # How many rows will be affected


class CustomTransformation(BaseModel):
    """User-defined transformation specification."""
    transformation_id: str
    column: str
    action: TransformationAction
    value_mappings: List[ValueMapping] = []
    parameters: Dict[str, Any] = {}  # Additional parameters for the transformation
    description: str
    created_by: str
    created_at: datetime


class TransformationPreview(BaseModel):
    """Preview of how a transformation will affect the data."""
    transformation_id: str
    column: str
    total_rows: int
    affected_rows: int
    before_sample: List[Dict[str, Any]]  # Sample rows before transformation
    after_sample: List[Dict[str, Any]]   # Sample rows after transformation
    impact_summary: Dict[str, Any]       # Summary of changes


class TransformationRule(BaseModel):
    """Reusable transformation rule that can be saved and applied."""
    rule_id: str
    name: str
    description: str
    column_pattern: str  # Pattern to match column names (e.g., "gender", "*_status")
    action: TransformationAction
    value_mappings: List[ValueMapping]
    parameters: Dict[str, Any] = {}
    created_by: str
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0


class DataVersion(BaseModel):
    """Version history for tracking data changes."""
    version_id: str
    artifact_id: str
    version_number: int
    description: str
    transformations_applied: List[str]  # List of transformation IDs
    data_hash: str  # Hash of the data for integrity checking
    created_at: datetime
    created_by: str


class TransformationHistory(BaseModel):
    """History of transformations applied to a data artifact."""
    artifact_id: str
    current_version: int
    versions: List[DataVersion]
    can_undo: bool
    can_redo: bool


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
    
    # OCR-specific fields
    ocr_confidence: Optional[float] = None
    processing_notes: Optional[List[str]] = None
    
    # Phase 2.5 additions
    custom_transformations: List[CustomTransformation] = []
    transformation_history: Optional[TransformationHistory] = None
    saved_rules: List[str] = []  # IDs of rules saved from this artifact


# === Request/Response Models ===

class ApplySuggestionRequest(BaseModel):
    """Request to apply a suggestion."""
    artifact_id: str
    suggestion_id: str
    action: str  # "accept" or "reject"


class UpdateNotesRequest(BaseModel):
    """Request to update notes."""
    artifact_id: str
    notes: str


class CreateCustomTransformationRequest(BaseModel):
    """Request to create a custom transformation."""
    artifact_id: str
    column: str
    action: TransformationAction
    value_mappings: List[ValueMapping]
    parameters: Dict[str, Any] = {}
    description: str


class PreviewTransformationRequest(BaseModel):
    """Request to preview a transformation."""
    artifact_id: str
    transformation_id: str


class ApplyTransformationRequest(BaseModel):
    """Request to apply a custom transformation."""
    artifact_id: str
    transformation_id: str
    save_as_rule: bool = False
    rule_name: Optional[str] = None
    rule_description: Optional[str] = None


class SaveTransformationRuleRequest(BaseModel):
    """Request to save a transformation as a reusable rule."""
    transformation_id: str
    rule_name: str
    rule_description: str
    column_pattern: str


class UndoTransformationRequest(BaseModel):
    """Request to undo the last transformation."""
    artifact_id: str
    target_version: Optional[int] = None  # If None, undo last change


class RedoTransformationRequest(BaseModel):
    """Request to redo a previously undone transformation."""
    artifact_id: str
    target_version: Optional[int] = None  # If None, redo next change


class SearchRulesRequest(BaseModel):
    """Request to search for transformation rules."""
    column_name: Optional[str] = None
    action: Optional[TransformationAction] = None
    search_term: Optional[str] = None
    owner_id: Optional[str] = None


class TransformationSuggestion(BaseModel):
    """Enhanced suggestion with customization options."""
    suggestion_id: str
    type: SuggestionType
    column: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: str
    explanation: str
    
    # Phase 2.5 additions
    suggested_mappings: List[ValueMapping] = []
    customization_options: Dict[str, Any] = {}
    similar_rules: List[str] = []  # IDs of similar saved rules
    can_customize: bool = True


# === Process File Complete Models ===

class ProcessFileCompleteRequest(BaseModel):
    """Request for complete file processing in one call."""
    experiment_id: str = "demo-experiment"
    auto_apply_suggestions: bool = True
    max_suggestions_to_apply: int = 10  # Limit to prevent over-processing
    confidence_threshold: float = 0.7  # Only apply high-confidence suggestions
    include_processing_details: bool = True
    user_id: str = "demo-user"


class ProcessingSummary(BaseModel):
    """Summary of processing steps performed."""
    file_processing: Dict[str, Any]
    quality_analysis: Dict[str, Any]
    suggestions_generated: int
    suggestions_applied: int
    suggestions_skipped: int
    transformations_performed: List[str]
    processing_time_seconds: float
    quality_score_before: Optional[float] = None
    quality_score_after: Optional[float] = None


class ProcessFileCompleteResponse(BaseModel):
    """Response from complete file processing."""
    success: bool
    artifact_id: str
    cleaned_data: Union[List[Dict[str, Any]], str]  # JSON array or CSV string
    data_shape: List[int]  # [rows, columns]
    column_names: List[str]
    processing_summary: ProcessingSummary
    unapplied_suggestions: List[Suggestion] = []
    error_message: Optional[str] = None
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}


# === NEW CSV-BASED MODELS (Task 1.1) ===

class CSVMessageRequest(BaseModel):
    """Request for CSV-based conversation message."""
    csv_data: str = Field(..., description="CSV data as a string")
    user_message: str = Field(..., description="User's natural language message")
    session_id: str = Field(..., description="Conversation session identifier")
    user_id: str = Field(default="demo-user", description="User identifier")


class CSVProcessingResponse(BaseModel):
    """Response from CSV processing conversation."""
    success: bool = Field(..., description="Whether processing was successful")
    original_csv: str = Field(..., description="Original CSV data")
    cleaned_csv: Optional[str] = Field(None, description="Cleaned CSV data if changes were made")
    changes_made: List[str] = Field(default_factory=list, description="List of changes applied")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    requires_approval: bool = Field(default=False, description="Whether user approval is needed")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in processing")
    session_id: str = Field(..., description="Session identifier")
    conversation_active: bool = Field(default=True, description="Whether conversation is active")
    response_message: Optional[str] = Field(None, description="Assistant's response message")
    intent: Optional[str] = Field(None, description="Detected user intent")
    pending_transformations: List[str] = Field(default_factory=list, description="Transformations awaiting approval")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class CSVConversationState(BaseModel):
    """State management for CSV-based conversations."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    original_csv: str = Field(..., description="Original CSV data")
    current_csv: str = Field(..., description="Current state of CSV data")
    user_message: str = Field(..., description="Latest user message")
    intent: Optional[str] = Field(None, description="Detected user intent")
    response: Optional[str] = Field(None, description="Assistant's response")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Full conversation history")
    pending_transformations: List[str] = Field(default_factory=list, description="Transformations awaiting approval")
    awaiting_approval: bool = Field(default=False, description="Whether waiting for user approval")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    applied_transformations: List[str] = Field(default_factory=list, description="Successfully applied transformations")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence score")
    created_at: datetime = Field(default_factory=datetime.now, description="When conversation started")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class CSVTransformationRequest(BaseModel):
    """Request for CSV transformation approval."""
    session_id: str = Field(..., description="Session identifier")
    transformation_id: str = Field(..., description="Transformation identifier")
    approved: bool = Field(..., description="Whether transformation is approved")
    user_feedback: Optional[str] = Field(None, description="Optional user feedback")


class CSVAnalysisResult(BaseModel):
    """Result of CSV data analysis."""
    data_shape: List[int] = Field(..., description="Rows and columns count")
    column_names: List[str] = Field(..., description="Column names")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Analysis confidence")
    analysis_notes: List[str] = Field(default_factory=list, description="Analysis notes")


# === Header Generation Models ===

class GenerateHeadersRequest(BaseModel):
    """Request model for generating CSV headers from experimental plan."""
    plan: str = Field(..., description="Full experimental plan text")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID to persist the CSV")


class GenerateHeadersResponse(BaseModel):
    """Response model for header generation."""
    success: bool = Field(..., description="Whether the operation succeeded")
    headers: List[str] = Field(default_factory=list, description="Generated column headers")
    csv_data: str = Field(default="", description="CSV header row")
    error_message: Optional[str] = Field(None, description="Error message if failed") 