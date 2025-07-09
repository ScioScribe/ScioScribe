"""
Helper utility functions for the experiment planning graph system.

This module provides common utility functions used across the planning system
for input processing, section determination, and other shared functionality.
"""

from typing import Dict, List
import logging

from ..state import ExperimentPlanState, PLANNING_STAGES

logger = logging.getLogger(__name__)


def get_latest_user_input(state: ExperimentPlanState) -> str:
    """
    Extract the latest user input from chat history.
    
    This helper function searches through the chat history to find
    the most recent user message for processing by agents.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Latest user input content or empty string if none found
    """
    chat_history = state.get('chat_history', [])
    
    # Find the most recent user message
    for message in reversed(chat_history):
        if message.get('role') == 'user':
            return message.get('content', '')
    
    return ''


def determine_section_to_edit(user_input: str, state: ExperimentPlanState) -> str:
    """
    Determine which section the user wants to edit based on their input.
    
    This function analyzes user input to identify which planning stage
    they want to navigate to for editing. Uses keyword matching with
    fallback to the first stage if no specific section is identified.
    
    Args:
        user_input: User's input message
        state: Current experiment plan state
        
    Returns:
        Planning stage name to navigate to
    """
    user_input_lower = user_input.lower()
    
    # Section keywords mapping
    section_keywords = {
        "objective_setting": ["objective", "goal", "hypothesis", "purpose", "aim"],
        "variable_identification": ["variable", "independent", "dependent", "control", "measure"],
        "experimental_design": ["design", "groups", "control", "sample", "statistical", "power"],
        "methodology_protocol": ["protocol", "method", "procedure", "steps", "materials", "equipment"],
        "data_planning": ["data", "analysis", "statistics", "visualization", "pitfalls"],
        "final_review": ["review", "export", "summary", "complete", "finalize"]
    }
    
    # Check for specific section keywords
    for section, keywords in section_keywords.items():
        if any(keyword in user_input_lower for keyword in keywords):
            logger.info(f"Determined section to edit: {section} (matched keywords)")
            return section
    
    # Default to objective setting if no specific section is identified
    logger.info("No specific section identified, defaulting to objective_setting")
    return "objective_setting"


def get_stage_routing_map() -> Dict[str, str]:
    """
    Get the mapping from planning stages to routing keys.
    
    Returns:
        Dictionary mapping planning stages to router keys
    """
    return {
        "objective_setting": "objective",
        "variable_identification": "variables",
        "experimental_design": "design",
        "methodology_protocol": "methodology",
        "data_planning": "data_planning",
        "final_review": "review"
    }


def get_stage_descriptions() -> Dict[str, str]:
    """
    Get human-readable descriptions for each planning stage.
    
    Returns:
        Dictionary mapping planning stages to descriptions
    """
    return {
        "objective_setting": "Define research objectives and hypothesis",
        "variable_identification": "Identify independent, dependent, and control variables",
        "experimental_design": "Design experimental groups and sample sizes",
        "methodology_protocol": "Create step-by-step procedures and materials list",
        "data_planning": "Plan data collection and analysis methods",
        "final_review": "Review and finalize the complete experiment plan"
    }


def get_completion_keywords() -> Dict[str, List[str]]:
    """
    Get keywords used to identify completion or approval intents.
    
    Returns:
        Dictionary with approval and edit keywords
    """
    return {
        "approval": ["approve", "approved", "yes", "confirm", "complete", "finalize"],
        "edit": ["edit", "modify", "change", "update", "revise", "go back"]
    }


def extract_user_intent(user_input: str) -> str:
    """
    Extract the user's intent from their input message.
    
    Args:
        user_input: User's input message
        
    Returns:
        Intent category: 'approval', 'edit', or 'unclear'
    """
    user_input_lower = user_input.lower()
    keywords = get_completion_keywords()
    
    if any(keyword in user_input_lower for keyword in keywords["approval"]):
        return "approval"
    elif any(keyword in user_input_lower for keyword in keywords["edit"]):
        return "edit"
    else:
        return "unclear"


def validate_stage_name(stage_name: str) -> bool:
    """
    Validate that a stage name is valid.
    
    Args:
        stage_name: Name of the planning stage
        
    Returns:
        True if valid, False otherwise
    """
    return stage_name in PLANNING_STAGES


def get_next_stage(current_stage: str) -> str | None:
    """
    Get the next planning stage after the current one.
    
    Args:
        current_stage: Current planning stage
        
    Returns:
        Next stage name or None if current is the last stage
    """
    try:
        current_index = PLANNING_STAGES.index(current_stage)
        if current_index < len(PLANNING_STAGES) - 1:
            return PLANNING_STAGES[current_index + 1]
        return None
    except ValueError:
        logger.error(f"Invalid current stage: {current_stage}")
        return None


def get_previous_stage(current_stage: str) -> str | None:
    """
    Get the previous planning stage before the current one.
    
    Args:
        current_stage: Current planning stage
        
    Returns:
        Previous stage name or None if current is the first stage
    """
    try:
        current_index = PLANNING_STAGES.index(current_stage)
        if current_index > 0:
            return PLANNING_STAGES[current_index - 1]
        return None
    except ValueError:
        logger.error(f"Invalid current stage: {current_stage}")
        return None


def calculate_progress_percentage(completed_stages: List[str]) -> float:
    """
    Calculate the progress percentage based on completed stages.
    
    Args:
        completed_stages: List of completed stage names
        
    Returns:
        Progress percentage (0.0 to 100.0)
    """
    if not PLANNING_STAGES:
        return 0.0
    
    total_stages = len(PLANNING_STAGES)
    completed_count = len(completed_stages)
    
    return (completed_count / total_stages) * 100.0


def format_stage_name(stage_name: str) -> str:
    """
    Format a stage name for display to users.
    
    Args:
        stage_name: Internal stage name
        
    Returns:
        Formatted stage name for display
    """
    return stage_name.replace('_', ' ').title()


def is_terminal_stage(stage_name: str) -> bool:
    """
    Check if a stage is the terminal (final) stage.
    
    Args:
        stage_name: Name of the planning stage
        
    Returns:
        True if this is the final stage, False otherwise
    """
    return stage_name == PLANNING_STAGES[-1] if PLANNING_STAGES else False 