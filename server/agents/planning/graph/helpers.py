"""
Helper utility functions for the experiment planning graph system.

This module provides common utility functions used across the planning system
for input processing, section determination, and other shared functionality.
"""

from typing import Dict, List, Any
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
    they want to navigate to for editing. Uses enhanced keyword matching 
    and context analysis with fallback logic.
    
    Args:
        user_input: User's input message
        state: Current experiment plan state
        
    Returns:
        Planning stage name to navigate to
    """
    user_input_lower = user_input.lower().strip()
    
    # Enhanced section keywords mapping with more comprehensive coverage
    section_keywords = {
        "objective_setting": [
            "objective", "goal", "hypothesis", "purpose", "aim", "research question",
            "what we're trying", "what we want", "main goal", "research aim",
            "study objective", "experimental objective"
        ],
        "variable_identification": [
            "variable", "independent", "dependent", "control", "measure", "measurement",
            "what we're measuring", "what we're changing", "factors", "parameters",
            "iv", "dv", "controlled variable", "confounding"
        ],
        "experimental_design": [
            "design", "groups", "control group", "experimental group", "sample", 
            "statistical", "power", "replicates", "randomization", "treatment",
            "control condition", "experimental condition", "group size", "n=",
            "power analysis", "sample size"
        ],
        "methodology_protocol": [
            "protocol", "method", "procedure", "steps", "materials", "equipment",
            "how to", "protocol steps", "experimental procedure", "methodology",
            "materials list", "reagents", "instruments", "step by step"
        ],
        "data_planning": [
            "data", "analysis", "statistics", "visualization", "pitfalls", "collection",
            "statistical test", "data analysis", "graphs", "charts", "results",
            "statistical analysis", "data collection", "potential problems"
        ],
        "final_review": [
            "review", "export", "summary", "complete", "finalize", "overview",
            "final plan", "export plan", "summary report", "complete plan",
            "plan review", "final summary"
        ]
    }
    
    # Check for specific section keywords with scoring
    section_scores = {}
    for section, keywords in section_keywords.items():
        score = sum(1 for keyword in keywords if keyword in user_input_lower)
        if score > 0:
            section_scores[section] = score
    
    # If we found matches, return the highest scoring section
    if section_scores:
        best_section = max(section_scores, key=section_scores.get)
        logger.info(f"Determined section to edit: {best_section} (score: {section_scores[best_section]})")
        return best_section
    
    # Context-based fallback: analyze what might be incomplete
    incomplete_stages = []
    
    # Check each stage for completeness
    if not state.get('experiment_objective') or not state.get('hypothesis'):
        incomplete_stages.append("objective_setting")
    
    if not state.get('independent_variables') or not state.get('dependent_variables'):
        incomplete_stages.append("variable_identification")
    
    if not state.get('experimental_groups') or not state.get('control_groups'):
        incomplete_stages.append("experimental_design")
    
    if not state.get('methodology_steps') or not state.get('materials_equipment'):
        incomplete_stages.append("methodology_protocol")
    
    if not state.get('data_collection_plan') or not state.get('data_analysis_plan'):
        incomplete_stages.append("data_planning")
    
    # If there are incomplete stages, suggest the first one
    if incomplete_stages:
        suggested_section = incomplete_stages[0]
        logger.info(f"No specific section identified, suggesting incomplete stage: {suggested_section}")
        return suggested_section
    
    # Final fallback: if everything seems complete, go to review
    if all([
        state.get('experiment_objective'),
        state.get('independent_variables'),
        state.get('experimental_groups'),
        state.get('methodology_steps'),
        state.get('data_collection_plan')
    ]):
        logger.info("All stages appear complete, directing to final review")
        return "final_review"
    
    # Ultimate fallback
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
    Extract the user's intent from their input message using improved NLP.
    
    Args:
        user_input: User's input message
        
    Returns:
        Intent category: 'approval', 'edit', or 'unclear'
    """
    user_input_lower = user_input.lower().strip()
    
    # Enhanced keyword sets for better detection
    approval_keywords = [
        "approve", "approved", "yes", "confirm", "complete", "finalize", 
        "done", "finished", "good", "looks good", "perfect", "ready",
        "export", "save", "accept", "ok", "okay", "great", "excellent",
        "thanks", "thank you", "that's all", "all set"
    ]
    
    edit_keywords = [
        "edit", "modify", "change", "update", "revise", "go back",
        "fix", "adjust", "improve", "refine", "alter", "correct",
        "want to change", "need to", "let me", "can we", "should we"
    ]
    
    # Strong approval phrases (higher priority)
    strong_approval_phrases = [
        "looks good", "looks great", "that's perfect", "ready to go",
        "ready to export", "ready to save", "all done", "we're done",
        "that's it", "that's all", "thank you"
    ]
    
    # Check for strong approval phrases first
    for phrase in strong_approval_phrases:
        if phrase in user_input_lower:
            return "approval"
    
    # Check for explicit approval/edit keywords
    approval_count = sum(1 for keyword in approval_keywords if keyword in user_input_lower)
    edit_count = sum(1 for keyword in edit_keywords if keyword in user_input_lower)
    
    # If user mentions specific sections, likely wants to edit
    section_mentions = ["objective", "variable", "design", "methodology", "data", "protocol"]
    if any(section in user_input_lower for section in section_mentions) and edit_count > 0:
        return "edit"
    
    # Determine intent based on keyword counts
    if approval_count > edit_count and approval_count > 0:
        return "approval"
    elif edit_count > approval_count and edit_count > 0:
        return "edit"
    elif approval_count > 0:
        return "approval"
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


def is_graph_complete(state_snapshot) -> bool:
    """
    Check if the LangGraph has reached completion (END state).
    
    Args:
        state_snapshot: LangGraph state snapshot from aget_state()
        
    Returns:
        True if graph is complete, False otherwise
    """
    if not state_snapshot:
        return False
    
    # If there are no next nodes, the graph has completed
    if not state_snapshot.next:
        return True
    
    # Check if next nodes is empty list (also indicates completion)
    if isinstance(state_snapshot.next, list) and len(state_snapshot.next) == 0:
        return True
    
    return False


def detect_session_completion(session_id: str, graph_components: Dict[str, Any]) -> bool:
    """
    Detect if a planning session has reached completion.
    
    Args:
        session_id: Session identifier
        graph_components: Graph components dictionary
        
    Returns:
        True if session is complete, False otherwise
    """
    try:
        import asyncio
        
        # This is a synchronous wrapper for async detection
        async def _async_detect():
            graph = graph_components["graph"]
            config = graph_components["config"]
            
            state_snapshot = await graph.aget_state(config)
            return is_graph_complete(state_snapshot)
        
        # Run the async function
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use this approach
            # Return False as fallback
            return False
        else:
            return loop.run_until_complete(_async_detect())
            
    except Exception as e:
        logger.error(f"Error detecting session completion: {e}")
        return False 