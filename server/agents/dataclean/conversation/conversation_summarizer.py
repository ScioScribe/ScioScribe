"""
Conversation Summarization & Context Compression Engine

This module provides simple conversation summarization capabilities:
- Automatic summarization when conversations get long
- Context compression to maintain performance
- Key information retention across conversation turns
- Integration with existing conversation system
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .state_schema import ConversationState, Intent
from config import get_openai_client

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """
    Simple conversation summarization engine for managing long conversations.
    """
    
    def __init__(self):
        """Initialize the conversation summarizer."""
        self.openai_client = get_openai_client()
        self.max_history_length = 20  # Trigger summarization after 20 turns
        self.max_compressed_length = 8  # Keep 8 most recent turns after compression
        self.summary_cache = {}  # Cache summaries to avoid re-computation
        
        logger.info("Initialized conversation summarizer")
    
    async def should_summarize_conversation(self, state: ConversationState) -> bool:
        """
        Check if conversation should be summarized.
        
        Args:
            state: Current conversation state
            
        Returns:
            True if conversation should be summarized
        """
        conversation_history = state.get("conversation_history", [])
        history_length = len(conversation_history)
        
        # Summarize if conversation is getting long
        if history_length >= self.max_history_length:
            return True
        
        # Check if we have memory/performance issues
        session_id = state.get("session_id", "")
        if session_id in self.summary_cache:
            # Already summarized, check if we need to re-summarize
            last_summary_length = self.summary_cache[session_id].get("turns_at_summary", 0)
            if history_length - last_summary_length >= self.max_history_length:
                return True
        
        return False
    
    async def summarize_conversation(self, state: ConversationState) -> Dict[str, Any]:
        """
        Summarize conversation history and compress context.
        
        Args:
            state: Current conversation state
            
        Returns:
            Dictionary with summarized conversation and compressed history
        """
        try:
            conversation_history = state.get("conversation_history", [])
            
            if len(conversation_history) <= self.max_compressed_length:
                # No need to summarize short conversations
                return {
                    "summary": None,
                    "compressed_history": conversation_history,
                    "compression_performed": False
                }
            
            # Split history into parts to summarize and parts to keep
            history_to_summarize = conversation_history[:-self.max_compressed_length]
            recent_history = conversation_history[-self.max_compressed_length:]
            
            # Generate summary of older conversation turns
            conversation_summary = await self._generate_conversation_summary(
                history_to_summarize, state
            )
            
            # Extract key information from summarized portion
            key_info = await self._extract_key_information(history_to_summarize, state)
            
            # Cache the summary
            session_id = state.get("session_id", "")
            self.summary_cache[session_id] = {
                "summary": conversation_summary,
                "key_info": key_info,
                "turns_at_summary": len(conversation_history),
                "created_at": datetime.now()
            }
            
            logger.info(f"Summarized {len(history_to_summarize)} conversation turns")
            
            return {
                "summary": conversation_summary,
                "key_info": key_info,
                "compressed_history": recent_history,
                "compression_performed": True,
                "turns_summarized": len(history_to_summarize),
                "turns_kept": len(recent_history)
            }
            
        except Exception as e:
            logger.error(f"Error in conversation summarization: {str(e)}")
            # Return original history if summarization fails
            return {
                "summary": None,
                "compressed_history": conversation_history,
                "compression_performed": False,
                "error": str(e)
            }
    
    async def get_conversation_context_for_llm(self, state: ConversationState) -> str:
        """
        Get optimized conversation context for LLM prompts.
        
        Args:
            state: Current conversation state
            
        Returns:
            Formatted conversation context string
        """
        try:
            session_id = state.get("session_id", "")
            conversation_history = state.get("conversation_history", [])
            
            # Check if we have a cached summary
            if session_id in self.summary_cache:
                summary_info = self.summary_cache[session_id]
                
                # Build context with summary + recent history
                context_parts = []
                
                # Add conversation summary
                if summary_info.get("summary"):
                    context_parts.append(f"CONVERSATION SUMMARY:\n{summary_info['summary']}")
                
                # Add key information
                if summary_info.get("key_info"):
                    key_info = summary_info["key_info"]
                    if key_info.get("data_operations"):
                        context_parts.append(f"DATA OPERATIONS: {', '.join(key_info['data_operations'])}")
                    if key_info.get("user_preferences"):
                        context_parts.append(f"USER PREFERENCES: {key_info['user_preferences']}")
                
                # Add recent conversation turns
                recent_turns = conversation_history[-self.max_compressed_length:]
                if recent_turns:
                    recent_context = self._format_conversation_turns(recent_turns)
                    context_parts.append(f"RECENT CONVERSATION:\n{recent_context}")
                
                return "\n\n".join(context_parts)
            
            else:
                # No summary available, use recent history only
                recent_turns = conversation_history[-10:]  # Last 10 turns
                return self._format_conversation_turns(recent_turns)
                
        except Exception as e:
            logger.error(f"Error building conversation context: {str(e)}")
            return "Conversation context unavailable"
    
    async def update_conversation_state_with_summary(
        self, 
        state: ConversationState,
        summary_result: Dict[str, Any]
    ) -> ConversationState:
        """
        Update conversation state with summarization results.
        
        Args:
            state: Current conversation state
            summary_result: Results from summarization
            
        Returns:
            Updated conversation state
        """
        if not summary_result.get("compression_performed"):
            return state
        
        # Update conversation history with compressed version
        updated_state = {
            **state,
            "conversation_history": summary_result["compressed_history"],
            "conversation_summary": summary_result.get("summary"),
            "conversation_key_info": summary_result.get("key_info"),
            "compression_performed": True,
            "turns_summarized": summary_result.get("turns_summarized", 0),
            "last_compression_time": datetime.now().isoformat()
        }
        
        return updated_state
    
    # Private helper methods
    
    async def _generate_conversation_summary(
        self, 
        conversation_turns: List[Dict[str, Any]], 
        state: ConversationState
    ) -> str:
        """Generate a summary of conversation turns."""
        if not self.openai_client or not conversation_turns:
            return await self._generate_basic_summary(conversation_turns, state)
        
        try:
            # Format conversation for summarization
            formatted_conversation = self._format_conversation_turns(conversation_turns)
            
            # Get data context
            artifact_id = state.get("artifact_id")
            data_context = state.get("data_context", {})
            
            prompt = f"""Summarize this data cleaning conversation in 2-3 sentences, focusing on:
- What data operations were performed
- Key issues discovered and resolved
- User's main goals and preferences

DATA CONTEXT:
- File: {artifact_id or "No file loaded"}
- Data info: {data_context.get('description', 'Unknown')}

CONVERSATION TO SUMMARIZE:
{formatted_conversation}

Provide a concise summary that captures the essential information:"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error in LLM summarization: {str(e)}")
            return await self._generate_basic_summary(conversation_turns, state)
    
    async def _generate_basic_summary(
        self, 
        conversation_turns: List[Dict[str, Any]], 
        state: ConversationState
    ) -> str:
        """Generate a basic summary without LLM."""
        if not conversation_turns:
            return "No conversation history"
        
        # Count different types of operations
        intents = [turn.get("intent", "") for turn in conversation_turns if turn.get("role") == "user"]
        unique_intents = list(set(intents))
        
        # Get data context
        artifact_id = state.get("artifact_id", "unknown file")
        
        summary_parts = [
            f"Conversation about {artifact_id}",
            f"Performed {len(conversation_turns)} conversation turns",
            f"Operations: {', '.join(unique_intents[:3])}" + ("..." if len(unique_intents) > 3 else "")
        ]
        
        return ". ".join(summary_parts) + "."
    
    async def _extract_key_information(
        self, 
        conversation_turns: List[Dict[str, Any]], 
        state: ConversationState
    ) -> Dict[str, Any]:
        """Extract key information from conversation turns."""
        key_info = {
            "data_operations": [],
            "user_preferences": {},
            "important_results": [],
            "error_patterns": []
        }
        
        try:
            for turn in conversation_turns:
                # Extract data operations
                intent = turn.get("intent", "")
                if intent and intent not in key_info["data_operations"]:
                    key_info["data_operations"].append(intent)
                
                # Extract important results
                if turn.get("role") == "assistant" and turn.get("type") == "result":
                    operation_result = turn.get("operation_result", {})
                    if operation_result.get("status") == "success":
                        key_info["important_results"].append({
                            "operation": intent,
                            "timestamp": turn.get("timestamp", "")
                        })
                
                # Extract error patterns
                if turn.get("role") == "assistant" and turn.get("type") == "error":
                    error_type = turn.get("error_type", "unknown")
                    if error_type not in key_info["error_patterns"]:
                        key_info["error_patterns"].append(error_type)
            
            # Extract user preferences from conversation context
            conversation_context = state.get("conversation_context", {})
            if conversation_context:
                key_info["user_preferences"] = {
                    "data_display": conversation_context.get("preferred_data_display", "table"),
                    "confirmation": conversation_context.get("confirmation_preference", "risky_only"),
                    "detail_level": conversation_context.get("detail_level", "detailed")
                }
            
        except Exception as e:
            logger.error(f"Error extracting key information: {str(e)}")
        
        return key_info
    
    def _format_conversation_turns(self, conversation_turns: List[Dict[str, Any]]) -> str:
        """Format conversation turns for display or summarization."""
        formatted_turns = []
        
        for turn in conversation_turns:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            timestamp = turn.get("timestamp", "")
            
            if role == "user":
                intent = turn.get("intent", "")
                formatted_turns.append(f"USER: {content} (Intent: {intent})")
            elif role == "assistant":
                turn_type = turn.get("type", "")
                formatted_turns.append(f"ASSISTANT ({turn_type}): {content}")
        
        return "\n".join(formatted_turns)
    
    def clear_cache(self, session_id: Optional[str] = None):
        """Clear summary cache for a session or all sessions."""
        if session_id:
            self.summary_cache.pop(session_id, None)
        else:
            self.summary_cache.clear()
        logger.info(f"Cleared summary cache for session: {session_id or 'all'}")


# Global instance
_conversation_summarizer = None

def get_conversation_summarizer() -> ConversationSummarizer:
    """Get the global conversation summarizer instance."""
    global _conversation_summarizer
    if _conversation_summarizer is None:
        _conversation_summarizer = ConversationSummarizer()
    return _conversation_summarizer 