"""
Advanced Context Manager for Multi-Turn Conversation Management

This module provides Phase 3 advanced conversation features:
- Multi-turn context tracking and summarization
- Reference resolution ("it", "that", "the data")
- Conversation flow state management
- Context compression for long conversations
- Proactive suggestion generation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re

from .state_schema import ConversationState, ConversationContext, Intent
from ..memory_store import get_data_store
from config import get_openai_client

logger = logging.getLogger(__name__)


class AdvancedContextManager:
    """
    Advanced context manager for Phase 3 multi-turn conversation features.
    
    This class handles:
    - Conversation context tracking across multiple turns
    - Reference resolution (pronouns, implicit references)
    - Context compression and summarization
    - Proactive suggestion generation
    - Conversation flow state management
    """
    
    def __init__(self):
        """Initialize the advanced context manager."""
        self.openai_client = get_openai_client()
        self.max_context_window = 10  # Maximum conversation turns to keep in full detail
        self.compression_threshold = 15  # Compress when history exceeds this
        
        # Reference patterns for resolution
        self.reference_patterns = {
            "it": r"\b(it|its)\b",
            "that": r"\b(that|those)\b",
            "them": r"\b(them|these)\b",
            "the_data": r"\b(the data|this data|my data)\b",
            "the_file": r"\b(the file|this file|my file)\b",
            "the_column": r"\b(the column|this column|that column)\b",
            "the_result": r"\b(the result|this result|that result)\b",
            "previous": r"\b(previous|last|earlier)\b"
        }
        
        logger.info("Initialized advanced context manager")
    
    async def build_enhanced_conversation_context(
        self, 
        state: ConversationState
    ) -> ConversationContext:
        """
        Build enhanced conversation context for multi-turn management.
        
        Args:
            state: Current conversation state
            
        Returns:
            Enhanced conversation context with summaries and reference tracking
        """
        try:
            conversation_history = state.get("conversation_history", [])
            
            # Build conversation summary
            conversation_summary = await self._generate_conversation_summary(
                conversation_history, state
            )
            
            # Extract key topics and entities
            key_topics = await self._extract_key_topics(conversation_history)
            mentioned_entities = await self._extract_mentioned_entities(conversation_history)
            
            # Track references and focus
            last_data_operation = self._get_last_data_operation(conversation_history)
            referenced_columns = self._get_referenced_columns(conversation_history)
            current_focus = await self._determine_current_focus(conversation_history, state)
            
            # Handle context compression
            compressed_history = await self._compress_conversation_history(
                conversation_history
            )
            
            # Determine user preferences
            user_preferences = self._learn_user_preferences(conversation_history)
            
            return ConversationContext(
                conversation_summary=conversation_summary,
                key_topics=key_topics,
                mentioned_entities=mentioned_entities,
                last_data_operation=last_data_operation,
                referenced_columns=referenced_columns,
                current_focus=current_focus,
                compressed_history=compressed_history,
                context_window_size=self.max_context_window,
                preferred_data_display=user_preferences.get("data_display", "table"),
                confirmation_preference=user_preferences.get("confirmation", "risky_only"),
                detail_level=user_preferences.get("detail_level", "detailed")
            )
            
        except Exception as e:
            logger.error(f"Error building enhanced conversation context: {str(e)}")
            return ConversationContext(
                conversation_summary="",
                key_topics=[],
                mentioned_entities={},
                last_data_operation=None,
                referenced_columns=[],
                current_focus=None,
                compressed_history=[],
                context_window_size=self.max_context_window,
                preferred_data_display="table",
                confirmation_preference="risky_only",
                detail_level="detailed"
            )
    
    async def resolve_references(
        self, 
        user_message: str, 
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Resolve references in user message using conversation context.
        
        Args:
            user_message: User's message potentially containing references
            state: Current conversation state
            
        Returns:
            Dictionary mapping reference types to resolved values
        """
        try:
            resolved_references = {}
            conversation_context = state.get("conversation_context", {})
            
            # Check for each reference pattern
            for ref_type, pattern in self.reference_patterns.items():
                if re.search(pattern, user_message, re.IGNORECASE):
                    resolved_value = await self._resolve_reference(
                        ref_type, user_message, state, conversation_context
                    )
                    if resolved_value:
                        resolved_references[ref_type] = resolved_value
            
            # Use LLM for complex reference resolution if available
            if self.openai_client and resolved_references:
                enhanced_resolution = await self._llm_enhance_reference_resolution(
                    user_message, resolved_references, state
                )
                resolved_references.update(enhanced_resolution)
            
            return resolved_references
            
        except Exception as e:
            logger.error(f"Error resolving references: {str(e)}")
            return {}
    
    async def update_conversation_flow_state(
        self, 
        state: ConversationState
    ) -> str:
        """
        Update conversation flow state based on recent interactions.
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated conversation flow state
        """
        try:
            intent = state.get("intent")
            conversation_history = state.get("conversation_history", [])
            
            # Determine flow state based on intent and history
            if intent in [Intent.SHOW_DATA, Intent.DESCRIBE]:
                flow_state = "exploring"
            elif intent in [Intent.CLEAN, Intent.REMOVE]:
                flow_state = "cleaning"
            elif intent in [Intent.ANALYZE]:
                flow_state = "analyzing"
            elif state.get("confirmation_required"):
                flow_state = "confirming"
            else:
                # Analyze recent conversation pattern
                recent_intents = [
                    turn.get("intent", "unknown") 
                    for turn in conversation_history[-5:] 
                    if turn.get("role") == "user"
                ]
                
                if any("clean" in intent for intent in recent_intents):
                    flow_state = "cleaning"
                elif any("analyze" in intent for intent in recent_intents):
                    flow_state = "analyzing"
                else:
                    flow_state = "exploring"
            
            return flow_state
            
        except Exception as e:
            logger.error(f"Error updating conversation flow state: {str(e)}")
            return "exploring"
    
    async def generate_proactive_suggestions(
        self, 
        state: ConversationState
    ) -> List[Dict[str, Any]]:
        """
        Generate proactive suggestions based on conversation context.
        
        Args:
            state: Current conversation state
            
        Returns:
            List of proactive suggestions
        """
        try:
            suggestions = []
            conversation_context = state.get("conversation_context", {})
            data_context = state.get("data_context", {})
            
            # Analyze current context for suggestions
            current_focus = conversation_context.get("current_focus")
            flow_state = state.get("conversation_flow_state", "exploring")
            
            # Generate context-aware suggestions
            if flow_state == "exploring" and data_context:
                suggestions.extend(await self._generate_exploration_suggestions(
                    data_context, conversation_context
                ))
            
            elif flow_state == "cleaning":
                suggestions.extend(await self._generate_cleaning_suggestions(
                    data_context, conversation_context
                ))
            
            elif flow_state == "analyzing":
                suggestions.extend(await self._generate_analysis_suggestions(
                    data_context, conversation_context
                ))
            
            # Use LLM for advanced suggestion generation
            if self.openai_client and suggestions:
                enhanced_suggestions = await self._llm_enhance_suggestions(
                    suggestions, state
                )
                suggestions.extend(enhanced_suggestions)
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating proactive suggestions: {str(e)}")
            return []
    
    async def compress_conversation_context(
        self, 
        state: ConversationState
    ) -> ConversationState:
        """
        Compress conversation context when it becomes too long.
        
        Args:
            state: Current conversation state
            
        Returns:
            State with compressed conversation context
        """
        try:
            conversation_history = state.get("conversation_history", [])
            
            if len(conversation_history) > self.compression_threshold:
                # Compress older conversation turns
                compressed_history = await self._compress_conversation_history(
                    conversation_history
                )
                
                # Update conversation context
                conversation_context = state.get("conversation_context", {})
                conversation_context["compressed_history"] = compressed_history
                
                # Keep only recent full turns
                recent_history = conversation_history[-self.max_context_window:]
                
                return {
                    **state,
                    "conversation_history": recent_history,
                    "conversation_context": conversation_context
                }
            
            return state
            
        except Exception as e:
            logger.error(f"Error compressing conversation context: {str(e)}")
            return state
    
    # Private helper methods
    
    async def _generate_conversation_summary(
        self, 
        conversation_history: List[Dict[str, Any]], 
        state: ConversationState
    ) -> str:
        """Generate a summary of the conversation."""
        if not conversation_history:
            return "New conversation started"
        
        if self.openai_client:
            return await self._llm_generate_summary(conversation_history, state)
        else:
            # Simple rule-based summary
            return f"Conversation with {len(conversation_history)} turns"
    
    async def _extract_key_topics(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key topics from conversation history."""
        topics = set()
        
        for turn in conversation_history:
            content = turn.get("content", "").lower()
            
            # Extract data-related topics
            if "data" in content:
                topics.add("data_exploration")
            if any(word in content for word in ["clean", "fix", "correct"]):
                topics.add("data_cleaning")
            if any(word in content for word in ["analyze", "analysis", "quality"]):
                topics.add("data_analysis")
            if any(word in content for word in ["column", "field"]):
                topics.add("data_structure")
        
        return list(topics)
    
    async def _extract_mentioned_entities(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extract mentioned entities from conversation history."""
        entities = {
            "columns": [],
            "operations": [],
            "file_formats": [],
            "data_types": []
        }
        
        for turn in conversation_history:
            content = turn.get("content", "")
            
            # Extract column mentions (simple pattern matching)
            column_matches = re.findall(r"column\s+['\"]?(\w+)['\"]?", content, re.IGNORECASE)
            entities["columns"].extend(column_matches)
            
            # Extract operation mentions
            operation_matches = re.findall(r"\b(clean|remove|convert|analyze|show)\b", content, re.IGNORECASE)
            entities["operations"].extend(operation_matches)
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def _get_last_data_operation(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Get the last data operation from conversation history."""
        for turn in reversed(conversation_history):
            if turn.get("role") == "assistant" and turn.get("metadata", {}).get("operation_result"):
                return turn.get("metadata", {}).get("operation_result")
        return None
    
    def _get_referenced_columns(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> List[str]:
        """Get columns referenced in the conversation."""
        columns = []
        
        for turn in conversation_history:
            content = turn.get("content", "")
            # Extract column references
            column_matches = re.findall(r"column\s+['\"]?(\w+)['\"]?", content, re.IGNORECASE)
            columns.extend(column_matches)
        
        return list(set(columns))
    
    async def _determine_current_focus(
        self, 
        conversation_history: List[Dict[str, Any]], 
        state: ConversationState
    ) -> Optional[str]:
        """Determine what the user is currently focused on."""
        if not conversation_history:
            return None
        
        # Get the last user message
        last_turn = conversation_history[-1] if conversation_history else {}
        
        if last_turn.get("role") == "user":
            content = last_turn.get("content", "").lower()
            
            if "column" in content:
                return "column_operations"
            elif any(word in content for word in ["clean", "fix"]):
                return "data_cleaning"
            elif any(word in content for word in ["analyze", "quality"]):
                return "data_analysis"
            elif any(word in content for word in ["show", "display", "view"]):
                return "data_exploration"
        
        return None
    
    async def _compress_conversation_history(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compress conversation history to key points."""
        if len(conversation_history) <= self.max_context_window:
            return conversation_history
        
        # Keep first few and last few turns, compress middle
        compressed = []
        
        # Keep first turns
        compressed.extend(conversation_history[:3])
        
        # Compress middle turns
        middle_turns = conversation_history[3:-self.max_context_window]
        if middle_turns:
            compressed.append({
                "timestamp": datetime.now().isoformat(),
                "role": "system",
                "content": f"[Compressed {len(middle_turns)} conversation turns]",
                "metadata": {"compressed": True, "original_count": len(middle_turns)}
            })
        
        # Keep recent turns
        compressed.extend(conversation_history[-self.max_context_window:])
        
        return compressed
    
    def _learn_user_preferences(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Learn user preferences from conversation history."""
        preferences = {
            "data_display": "table",
            "confirmation": "risky_only",
            "detail_level": "detailed"
        }
        
        # Simple preference learning
        for turn in conversation_history:
            if turn.get("role") == "user":
                content = turn.get("content", "").lower()
                
                if "just show" in content or "quick" in content:
                    preferences["detail_level"] = "brief"
                elif "detailed" in content or "explain" in content:
                    preferences["detail_level"] = "detailed"
                    
                if "don't ask" in content or "just do it" in content:
                    preferences["confirmation"] = "never"
                elif "ask me" in content or "confirm" in content:
                    preferences["confirmation"] = "always"
        
        return preferences
    
    async def _resolve_reference(
        self, 
        ref_type: str, 
        user_message: str, 
        state: ConversationState,
        conversation_context: Dict[str, Any]
    ) -> Optional[Any]:
        """Resolve a specific reference type."""
        if ref_type == "it":
            # "it" usually refers to the last data operation or current focus
            return conversation_context.get("last_data_operation") or conversation_context.get("current_focus")
        
        elif ref_type == "that":
            # "that" usually refers to the last mentioned entity
            return conversation_context.get("last_data_operation")
        
        elif ref_type == "the_data":
            # "the data" refers to the current dataset
            return state.get("data_context", {}).get("artifact_id")
        
        elif ref_type == "the_column":
            # "the column" refers to the last mentioned column
            referenced_columns = conversation_context.get("referenced_columns", [])
            return referenced_columns[-1] if referenced_columns else None
        
        elif ref_type == "the_result":
            # "the result" refers to the last operation result
            return conversation_context.get("last_data_operation")
        
        return None
    
    async def _generate_exploration_suggestions(
        self, 
        data_context: Dict[str, Any], 
        conversation_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for data exploration."""
        suggestions = []
        
        # Basic exploration suggestions
        suggestions.append({
            "type": "exploration",
            "action": "show_data",
            "description": "Show sample data",
            "confidence": 0.8
        })
        
        suggestions.append({
            "type": "exploration",
            "action": "describe",
            "description": "Get data overview",
            "confidence": 0.7
        })
        
        return suggestions
    
    async def _generate_cleaning_suggestions(
        self, 
        data_context: Dict[str, Any], 
        conversation_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for data cleaning."""
        suggestions = []
        
        suggestions.append({
            "type": "cleaning",
            "action": "analyze",
            "description": "Analyze data quality",
            "confidence": 0.9
        })
        
        return suggestions
    
    async def _generate_analysis_suggestions(
        self, 
        data_context: Dict[str, Any], 
        conversation_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for data analysis."""
        suggestions = []
        
        suggestions.append({
            "type": "analysis",
            "action": "quality_check",
            "description": "Check data quality",
            "confidence": 0.8
        })
        
        return suggestions
    
    async def _llm_generate_summary(
        self, 
        conversation_history: List[Dict[str, Any]], 
        state: ConversationState
    ) -> str:
        """Use LLM to generate conversation summary."""
        if not self.openai_client:
            return "Conversation in progress"
        
        try:
            # Create prompt for conversation summary
            recent_turns = conversation_history[-10:]  # Last 10 turns
            conversation_text = "\n".join([
                f"{turn.get('role', 'unknown')}: {turn.get('content', '')}"
                for turn in recent_turns
            ])
            
            prompt = f"""Summarize this data cleaning conversation in 1-2 sentences:

{conversation_text}

Focus on:
- What data operations were discussed
- Current state of the data processing
- Next steps or current focus

Summary:"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating LLM summary: {str(e)}")
            return "Conversation in progress"
    
    async def _llm_enhance_reference_resolution(
        self, 
        user_message: str, 
        resolved_references: Dict[str, Any], 
        state: ConversationState
    ) -> Dict[str, Any]:
        """Use LLM to enhance reference resolution."""
        # Placeholder for advanced LLM-based reference resolution
        return {}
    
    async def _llm_enhance_suggestions(
        self, 
        suggestions: List[Dict[str, Any]], 
        state: ConversationState
    ) -> List[Dict[str, Any]]:
        """Use LLM to enhance suggestions."""
        # Placeholder for advanced LLM-based suggestion enhancement
        return []


# Global instance
_context_manager = None

def get_advanced_context_manager() -> AdvancedContextManager:
    """Get the global advanced context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = AdvancedContextManager()
    return _context_manager 