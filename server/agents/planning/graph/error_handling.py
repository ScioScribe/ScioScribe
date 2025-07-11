"""
Simplified error handling for the experiment planning graph system.

This module provides basic error handling utilities for LangGraph operations.
Most error handling is now delegated to LangGraph's built-in mechanisms.
"""

import logging
from typing import Callable, TypeVar

from ..state import ExperimentPlanState

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_conditional_check(
    check_function: Callable[[ExperimentPlanState], T], 
    state: ExperimentPlanState, 
    check_name: str, 
    fallback_result: T
) -> T:
    """
    Safely execute a conditional check function with fallback.
    
    Args:
        check_function: The check function to execute
        state: Current experiment plan state
        check_name: Name of the check for logging
        fallback_result: Default result if check fails
        
    Returns:
        Check result or fallback result on error
    """
    try:
        result = check_function(state)
        logger.debug(f"Conditional check {check_name} completed: {result}")
        return result
        
    except Exception as e:
        logger.warning(f"Conditional check {check_name} failed: {str(e)}, using fallback: {fallback_result}")
        return fallback_result


# Legacy function stubs for backward compatibility
def error_recovery_context(node_name: str, state: ExperimentPlanState):
    """Legacy function - error handling is now done by LangGraph."""
    from contextlib import nullcontext
    return nullcontext()


def safe_agent_execution(agent_class: type, node_name: str, stage: str, state: ExperimentPlanState):
    """Legacy function - agent execution is now handled directly in graph nodes."""
    logger.warning(f"safe_agent_execution called for {node_name} - this should be handled by graph nodes now")
    return state 