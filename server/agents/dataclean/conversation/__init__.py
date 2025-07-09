"""
LangGraph Integration for Conversational Data Cleaning

This module provides the LangGraph orchestration layer for converting
ScioScribe's existing data cleaning system into a conversational AI assistant.

The LangGraph system serves as a conversation orchestrator that coordinates
existing backend components without replacing them.

Phase 3 Enhancement: Advanced Multi-Turn Conversation Management
"""

from .conversation_graph import ConversationGraph
from .conversation_graph_enhanced import EnhancedConversationGraph
from .state_schema import ConversationState, ConversationContext
from .conversation_session_manager import ConversationSessionManager
from .intent_classifier import EnhancedIntentClassifier, IntentClassificationResult
from .advanced_context_manager import AdvancedContextManager, get_advanced_context_manager
from .proactive_suggestions import ProactiveSuggestionsEngine, get_proactive_suggestions_engine
from .error_recovery_engine import EnhancedErrorRecoveryEngine, get_error_recovery_engine
from .conversation_summarizer import ConversationSummarizer, get_conversation_summarizer
from .conversation_templates import SimpleConversationTemplates, get_simple_conversation_templates
from .nodes_simple import (
    message_parser_node,
    context_loader_node,
    processing_router_node,
    response_generator_node,
)
from .nodes_enhanced import (
    enhanced_context_loader,
    enhanced_response_composer,
    enhanced_error_recovery,
    conversation_branch_handler,
    template_suggestion_handler,
    conversation_flow_coordinator,
    enhanced_data_processing,
)
from .nodes import (
    message_parser_node as basic_message_parser_node,
    context_loader_node as basic_context_loader_node,
    processing_router_node as basic_processing_router_node,
    response_generator_node as basic_response_generator_node,
)

__all__ = [
    # Basic Phase 1.1 & 1.2 Components
    "ConversationGraph",
    "ConversationState",
    "ConversationSessionManager",
    "message_parser_node",
    "context_loader_node", 
    "processing_router_node",
    "response_generator_node",
    
    # Enhanced Phase 1.3 Components
    "EnhancedConversationGraph",
    "EnhancedIntentClassifier",
    "IntentClassificationResult",
    "enhanced_message_parser_node",
    "enhanced_context_loader_node",
    "enhanced_processing_router_node",
    "enhanced_response_generator_node",
    
    # Phase 3: Advanced Multi-Turn Conversation Management
    "ConversationContext",
    "AdvancedContextManager",
    "get_advanced_context_manager",
    
    # Phase 3: Proactive Suggestions & Next-Step Recommendations
    "ProactiveSuggestionsEngine",
    "get_proactive_suggestions_engine",
    
    # Phase 3: Enhanced Error Recovery & Conversation Repair
    "EnhancedErrorRecoveryEngine",
    "get_error_recovery_engine",
    
    # Phase 3: Conversation Summarization & Context Compression
    "ConversationSummarizer",
    "get_conversation_summarizer",
    
    # Phase 3: Conversation Templates & Guided Workflows
    "SimpleConversationTemplates",
    "get_conversation_templates_engine",
    
    # Basic nodes (aliased for compatibility)
    "basic_message_parser_node",
    "basic_context_loader_node",
    "basic_processing_router_node",
    "basic_response_generator_node",
] 