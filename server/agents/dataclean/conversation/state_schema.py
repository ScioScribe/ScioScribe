"""
Enhanced State Schema for Advanced Multi-Turn Conversation Management

This module provides the state structure for Phase 3 advanced conversation features,
including multi-turn context management, conversation summarization, and proactive suggestions.
"""

from typing import TypedDict, Optional, Dict, Any, List, Tuple
from enum import Enum
from datetime import datetime


class Intent(Enum):
    """Intent classification for user messages."""
    SHOW_DATA = "show_data"
    DESCRIBE = "describe"
    ANALYZE = "analyze"
    CLEAN = "clean"
    REMOVE = "remove"
    CONVERT = "convert"
    SELECT_SHEET = "select_sheet"
    DETECT_DELIMITER = "detect_delimiter"
    ENCODING_ISSUE = "encoding_issue"
    UNDO = "undo"
    SAVE = "save"
    UNKNOWN = "unknown"


class FileFormat(Enum):
    """File format types for data processing."""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    IMAGE = "image"
    PDF = "pdf"
    UNKNOWN = "unknown"


class ConversationContext(TypedDict):
    """Enhanced conversation context for multi-turn management."""
    # Context Summary
    conversation_summary: str
    key_topics: List[str]
    mentioned_entities: Dict[str, List[str]]  # entity_type -> [entity_values]
    
    # Reference Tracking
    last_data_operation: Optional[Dict[str, Any]]
    referenced_columns: List[str]
    current_focus: Optional[str]  # What the user is currently focused on
    
    # Context Compression
    compressed_history: List[Dict[str, Any]]  # Summarized important turns
    context_window_size: int
    
    # User Preferences (learned from conversation)
    preferred_data_display: str  # "table", "summary", "sample"
    confirmation_preference: str  # "always", "risky_only", "never"
    detail_level: str  # "brief", "detailed", "technical"


class ConversationState(TypedDict):
    """
    Enhanced state schema for advanced multi-turn conversation management.
    
    This state structure maintains comprehensive context for conversational
    data cleaning operations with Phase 3 advanced features.
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
    
    # Phase 3: Advanced Multi-Turn Context Management
    conversation_context: Optional[ConversationContext]
    context_references: Dict[str, Any]  # "it", "that", "the data" -> resolved references
    conversation_flow_state: str  # "exploring", "cleaning", "analyzing", "confirming"
    multi_turn_operation: Optional[Dict[str, Any]]  # Complex operations across turns
    
    # Data Context (from existing memory_store)
    data_context: Optional[Dict[str, Any]]
    current_dataframe: Optional[str]
    dataframe_info: Optional[Dict[str, Any]]
    available_operations: Optional[List[str]]  # Available operations based on context
    
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
    
    # Phase 3: Proactive Suggestions
    proactive_suggestions: Optional[List[Dict[str, Any]]]
    context_aware_hints: Optional[List[str]]

    # Phase 3: Conversation Summarization & Context Compression
    conversation_summary: Optional[str]  # Summary of older conversation turns
    conversation_key_info: Optional[Dict[str, Any]]  # Key information extracted from history
    compression_performed: Optional[bool]  # Whether compression was performed
    turns_summarized: Optional[int]  # Number of turns that were summarized
    last_compression_time: Optional[str]  # ISO timestamp of last compression
    conversation_context_for_llm: Optional[str]  # Optimized context for LLM prompts

    # Phase 3: Conversation Templates & Guided Workflows
    template_workflow: Optional[Dict[str, Any]]  # Active template workflow state
    template_suggestions: Optional[List[Dict[str, Any]]]  # Suggested templates for context
    workflow_active: Optional[bool]  # Whether a guided workflow is currently active
    current_workflow_step: Optional[int]  # Current step in the workflow
    workflow_update: Optional[Dict[str, Any]]  # Updates to workflow state

    # Phase 3: Conversation Branching Fields
    # Confirmation Handling
    confirmation_response: Optional[str]  # "confirmed", "cancelled", "needs_clarification"
    confirmation_message: Optional[str]
    processing_confirmed: Optional[bool]
    
    # Error Recovery
    recovery_strategy: Optional[str]  # "retry_operation", "alternative_approach", "give_up"
    recovery_message: Optional[str]
    error_recovered: Optional[bool]
    
    # Phase 3: Enhanced Error Recovery Fields
    error_severity: Optional[str]  # "low", "medium", "high", "critical"
    recovery_success_rate: Optional[float]  # 0.0 to 1.0
    requires_user_action: Optional[bool]
    recovery_steps: Optional[List[str]]
    fallback_strategy: Optional[str]
    next_recovery_step: Optional[str]
    
    # Phase 3: Recovery-Specific Fields
    degraded_mode: Optional[bool]
    limitations: Optional[str]
    guidance_steps: Optional[List[str]]
    context_repaired: Optional[bool]
    reset_performed: Optional[bool]
    
    # Multi-Step Operation Support
    step_action: Optional[str]  # "continue_steps", "complete_operation", "need_user_input"
    step_message: Optional[str]
    current_step: Optional[int]
    next_step: Optional[int]
    total_steps: Optional[int]
    operation_type: Optional[str]


class MessageContext(TypedDict):
    """Context for processing individual messages."""
    raw_message: str
    processed_message: str
    extracted_parameters: Dict[str, Any]
    confidence_score: float
    
    # Phase 3: Enhanced message context
    resolved_references: Dict[str, Any]  # Resolved "it", "that", etc.
    implicit_context: Dict[str, Any]  # Implied context from conversation
    conversation_continuity: bool  # Whether this continues previous topic 