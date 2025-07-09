"""
Conversation State Schema for LangGraph Data Cleaning

This module defines the state schema used by LangGraph to manage conversation
context, data processing state, and file format information for CSV/Excel files.
"""

from typing import TypedDict, Optional, Dict, Any, List, Tuple
from enum import Enum


class FileFormat(str, Enum):
    """Supported file formats for conversational processing."""
    CSV = "csv"
    EXCEL = "excel"


class Intent(str, Enum):
    """Classification of user intents for data operations."""
    # Data Exploration
    EXPLORE = "explore"
    SHOW_DATA = "show_data"
    DESCRIBE = "describe"
    
    # Data Cleaning
    CLEAN = "clean"
    FIX = "fix"
    REMOVE = "remove"
    STANDARDIZE = "standardize"
    
    # Data Transformation
    CONVERT = "convert"
    CHANGE = "change"
    FORMAT = "format"
    
    # Quality Analysis
    ANALYZE = "analyze"
    FIND_ISSUES = "find_issues"
    QUALITY_CHECK = "quality_check"
    
    # Session Management
    UNDO = "undo"
    SAVE = "save"
    EXPORT = "export"
    
    # File-Specific Operations
    SELECT_SHEET = "select_sheet"
    DETECT_DELIMITER = "detect_delimiter"
    ENCODING_ISSUE = "encoding_issue"
    
    # Fallback
    UNKNOWN = "unknown"


class ConversationState(TypedDict):
    """
    State schema for LangGraph conversation management.
    
    This state structure maintains all necessary context for conversational
    data cleaning operations while integrating with existing components.
    """
    
    # Session Management
    session_id: str
    artifact_id: Optional[str]  # Links to existing DataArtifact
    user_id: str
    
    # File Context (CSV/Excel focused)
    file_format: Optional[FileFormat]
    file_path: Optional[str]
    sheet_name: Optional[str]  # Excel sheets
    delimiter: Optional[str]  # CSV delimiter
    encoding: Optional[str]  # File encoding
    csv_excel_context: Optional[Dict[str, Any]]  # Enhanced CSV/Excel specific context
    
    # Conversation Flow
    user_message: str
    intent: Intent
    response: str
    conversation_history: List[Dict[str, str]]
    extracted_parameters: Dict[str, Any]
    
    # Phase 1.3: Enhanced Intent Classification
    intent_confidence: float
    intent_reasoning: str
    alternative_intents: List[Tuple[Intent, float]]
    
    # Data Context (from existing memory_store)
    data_context: Optional[Dict[str, Any]]
    current_dataframe: Optional[str]
    dataframe_info: Optional[Dict[str, Any]]
    
    # Processing State
    pending_operation: Optional[Dict[str, Any]]
    confirmation_required: bool
    operation_result: Optional[Dict[str, Any]]
    last_operation: Optional[str]
    
    # Error Handling
    error_message: Optional[str]
    error_type: Optional[str]
    retry_count: int
    
    # Response Context
    response_type: str  # "info", "confirmation", "result", "error"
    next_steps: Optional[List[str]]
    suggestions: Optional[List[str]]


class MessageContext(TypedDict):
    """Context for processing individual messages."""
    raw_message: str
    processed_message: str
    extracted_parameters: Dict[str, Any]
    confidence_score: float
    
    
class OperationContext(TypedDict):
    """Context for data processing operations."""
    operation_type: str
    parameters: Dict[str, Any]
    target_columns: Optional[List[str]]
    preview_data: Optional[Dict[str, Any]]
    risk_level: str  # "low", "medium", "high"
    confirmation_message: Optional[str]


class ResponseContext(TypedDict):
    """Context for generating conversational responses."""
    response_template: str
    data_summary: Optional[Dict[str, Any]]
    operation_status: str
    follow_up_questions: Optional[List[str]]
    action_items: Optional[List[str]] 