"""
Simplified Conversation Templates for Common Data Tasks

This module provides simple template suggestions for common data cleaning scenarios.
Templates are collections of helpful suggestions rather than enforced workflows,
making them easy to use and robust.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

from .state_schema import ConversationState, Intent

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    """Categories of conversation templates."""
    GETTING_STARTED = "getting_started"
    DATA_QUALITY = "data_quality"
    DATA_CLEANING = "data_cleaning"
    DATA_EXPLORATION = "data_exploration"


class SimpleConversationTemplates:
    """
    Simple conversation templates that provide helpful suggestions for common data tasks.
    
    Templates are collections of suggested commands that users can follow (or not).
    No complex workflow state management - just helpful guidance.
    """
    
    def __init__(self):
        """Initialize the simple conversation templates."""
        self.templates = self._load_simple_templates()
        logger.info("Initialized simple conversation templates")
    
    def get_templates_for_context(self, state: ConversationState) -> List[Dict[str, Any]]:
        """
        Get relevant template suggestions based on current conversation context.
        
        Args:
            state: Current conversation state
            
        Returns:
            List of relevant template suggestions
        """
        try:
            suggestions = []
            
            # Analyze current context
            data_context = state.get("data_context", {})
            conversation_history = state.get("conversation_history", [])
            
            # Determine what to suggest based on context
            if not data_context or not data_context.get("has_data"):
                # No data - suggest getting started
                suggestions.append(self.templates["getting_started"])
            else:
                # Has data - suggest based on quality and history
                quality_score = data_context.get("quality_score", 1.0)
                
                # Check what user has already done
                recent_intents = [
                    turn.get("intent", "") for turn in conversation_history[-5:] 
                    if turn.get("role") == "user"
                ]
                
                # Suggest quality check if not done yet
                if "analyze" not in recent_intents:
                    suggestions.append(self.templates["check_quality"])
                
                # Suggest cleaning if quality issues found
                if quality_score and quality_score < 0.8:
                    suggestions.append(self.templates["clean_data"])
                
                # Suggest exploration if data looks good
                if not quality_score or quality_score >= 0.8:
                    suggestions.append(self.templates["explore_data"])
            
            return suggestions[:2]  # Return top 2 suggestions
            
        except Exception as e:
            logger.error(f"Error getting template suggestions: {str(e)}")
            return []
    
    def get_template_by_category(self, category: str) -> Optional[Dict[str, Any]]:
        """
        Get template by category.
        
        Args:
            category: Template category
            
        Returns:
            Template dictionary or None
        """
        for template in self.templates.values():
            if template.get("category") == category:
                return template
        return None
    
    def _load_simple_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load simple template suggestions."""
        return {
            "getting_started": {
                "title": "Getting Started with Your Data",
                "category": TemplateCategory.GETTING_STARTED.value,
                "description": "First steps to explore your uploaded data",
                "suggestions": [
                    {
                        "text": "Show me the first few rows",
                        "example": "show me the data",
                        "intent": "show_data",
                        "why": "See what your data looks like"
                    },
                    {
                        "text": "Describe the data structure",
                        "example": "describe the data",
                        "intent": "describe",
                        "why": "Understand columns and data types"
                    },
                    {
                        "text": "Analyze data quality",
                        "example": "analyze the data quality",
                        "intent": "analyze",
                        "why": "Find any issues that need fixing"
                    }
                ],
                "helpful_hints": [
                    "💡 Start by exploring your data before cleaning",
                    "📊 Check for missing values and data types",
                    "🔍 Look for patterns and outliers"
                ]
            },
            
            "check_quality": {
                "title": "Check Your Data Quality",
                "category": TemplateCategory.DATA_QUALITY.value,
                "description": "Identify and understand data quality issues",
                "suggestions": [
                    {
                        "text": "Run quality analysis",
                        "example": "analyze the data quality",
                        "intent": "analyze",
                        "why": "Find missing values, duplicates, and inconsistencies"
                    },
                    {
                        "text": "Show data sample",
                        "example": "show me 20 rows",
                        "intent": "show_data",
                        "why": "See examples of data issues"
                    },
                    {
                        "text": "Describe data structure",
                        "example": "describe the columns",
                        "intent": "describe",
                        "why": "Understand data types and ranges"
                    }
                ],
                "helpful_hints": [
                    "🔍 Quality analysis shows missing values and duplicates",
                    "📈 Check data distributions for outliers",
                    "✅ Good quality data makes analysis easier"
                ]
            },
            
            "clean_data": {
                "title": "Clean Your Data",
                "category": TemplateCategory.DATA_CLEANING.value,
                "description": "Fix data quality issues found in your dataset",
                "suggestions": [
                    {
                        "text": "Clean the data",
                        "example": "clean the data",
                        "intent": "clean",
                        "why": "Fix missing values and inconsistencies"
                    },
                    {
                        "text": "Remove duplicates",
                        "example": "remove duplicate rows",
                        "intent": "remove",
                        "why": "Eliminate redundant entries"
                    },
                    {
                        "text": "Standardize formats",
                        "example": "standardize the date format",
                        "intent": "convert",
                        "why": "Make data consistent"
                    }
                ],
                "helpful_hints": [
                    "🧹 Cleaning improves data quality significantly",
                    "⚠️ Always check results after cleaning",
                    "💾 You can undo changes if needed"
                ]
            },
            
            "explore_data": {
                "title": "Explore Your Data",
                "category": TemplateCategory.DATA_EXPLORATION.value,
                "description": "Discover patterns and insights in your clean data",
                "suggestions": [
                    {
                        "text": "Show data overview",
                        "example": "show me the data overview",
                        "intent": "describe",
                        "why": "Get summary statistics and structure"
                    },
                    {
                        "text": "Analyze specific columns",
                        "example": "analyze the sales column",
                        "intent": "analyze",
                        "why": "Understand distributions and patterns"
                    },
                    {
                        "text": "Find interesting patterns",
                        "example": "show me interesting patterns",
                        "intent": "analyze",
                        "why": "Discover insights in your data"
                    }
                ],
                "helpful_hints": [
                    "📊 Look for trends and correlations",
                    "🎯 Focus on columns relevant to your goals",
                    "💡 Clean data reveals better insights"
                ]
            },
            
            "common_tasks": {
                "title": "Common Data Tasks",
                "category": TemplateCategory.DATA_EXPLORATION.value,
                "description": "Frequently used commands for data work",
                "suggestions": [
                    {
                        "text": "Show first 10 rows",
                        "example": "show me 10 rows",
                        "intent": "show_data",
                        "why": "Quick data preview"
                    },
                    {
                        "text": "Get column info",
                        "example": "describe the columns",
                        "intent": "describe",
                        "why": "Understand data structure"
                    },
                    {
                        "text": "Find data issues",
                        "example": "analyze data quality",
                        "intent": "analyze",
                        "why": "Identify problems to fix"
                    },
                    {
                        "text": "Export clean data",
                        "example": "save the data",
                        "intent": "save",
                        "why": "Download processed results"
                    }
                ],
                "helpful_hints": [
                    "⚡ These commands work with any dataset",
                    "🔄 You can repeat commands as needed",
                    "📋 Try different variations of commands"
                ]
            }
        }
    
    def format_template_for_display(self, template: Dict[str, Any]) -> str:
        """
        Format template for display in conversation.
        
        Args:
            template: Template dictionary
            
        Returns:
            Formatted template string
        """
        try:
            formatted = f"**{template['title']}**\n"
            formatted += f"{template['description']}\n\n"
            
            formatted += "**Try these commands:**\n"
            for suggestion in template['suggestions']:
                formatted += f"• *\"{suggestion['example']}\"* - {suggestion['why']}\n"
            
            if template.get('helpful_hints'):
                formatted += f"\n**Helpful hints:**\n"
                for hint in template['helpful_hints']:
                    formatted += f"{hint}\n"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting template: {str(e)}")
            return f"**{template.get('title', 'Data Task')}**\nTry exploring your data with simple commands."


# Global instance
_simple_conversation_templates = None

def get_simple_conversation_templates() -> SimpleConversationTemplates:
    """Get the global simple conversation templates instance."""
    global _simple_conversation_templates
    if _simple_conversation_templates is None:
        _simple_conversation_templates = SimpleConversationTemplates()
    return _simple_conversation_templates 