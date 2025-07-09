"""
Agent node handlers for the experiment planning graph system.

This module provides the LangGraph node wrapper functions that execute
individual planning agents with consistent error handling and state management.
Each function serves as a standardized interface between the graph and agents.
"""

from typing import Dict, Any
import logging

from ..state import ExperimentPlanState
from ..agents import (
    ObjectiveAgent,
    VariableAgent,
    DesignAgent,
    MethodologyAgent,
    DataAgent,
    ReviewAgent
)
from .error_handling import error_recovery_context, safe_agent_execution
from ..validation import validate_experiment_plan_state
from ..transitions import transition_to_stage
from ..factory import add_chat_message, add_error, update_state_timestamp
from .helpers import get_latest_user_input, determine_section_to_edit

logger = logging.getLogger(__name__)


def objective_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Execute the objective setting agent with comprehensive error handling.
    
    This node handles the first stage of experiment planning, helping users
    clarify their research objectives and develop testable hypotheses.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with refined objectives
    """
    with error_recovery_context("objective_agent", state):
        return safe_agent_execution(
            ObjectiveAgent,
            "objective_agent",
            "objective_setting",
            state
        )


def variable_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Execute the variable identification agent with comprehensive error handling.
    
    This node handles the second stage of experiment planning, helping users
    identify and define independent, dependent, and control variables.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with defined variables
    """
    with error_recovery_context("variable_agent", state):
        return safe_agent_execution(
            VariableAgent,
            "variable_agent",
            "variable_identification",
            state
        )


def design_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Execute the experimental design agent with comprehensive error handling.
    
    This node handles the third stage of experiment planning, helping users
    design experimental groups, controls, and calculate appropriate sample sizes.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with experimental design
    """
    with error_recovery_context("design_agent", state):
        return safe_agent_execution(
            DesignAgent,
            "design_agent",
            "experimental_design",
            state
        )


def methodology_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Execute the methodology and protocol agent with comprehensive error handling.
    
    This node handles the fourth stage of experiment planning, helping users
    develop detailed protocols and comprehensive materials lists.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with methodology and protocols
    """
    with error_recovery_context("methodology_agent", state):
        return safe_agent_execution(
            MethodologyAgent,
            "methodology_agent",
            "methodology_protocol",
            state
        )


def data_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Execute the data planning and QA agent with comprehensive error handling.
    
    This node handles the fifth stage of experiment planning, helping users
    plan data collection, analysis approaches, and identify potential pitfalls.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with data planning details
    """
    with error_recovery_context("data_agent", state):
        return safe_agent_execution(
            DataAgent,
            "data_agent",
            "data_planning",
            state
        )


def review_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Execute the final review and export agent with comprehensive error handling.
    
    This node handles the final stage of experiment planning, helping users
    review, validate, and export their complete experiment plan.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with final review and export options
    """
    with error_recovery_context("review_agent", state):
        return safe_agent_execution(
            ReviewAgent,
            "review_agent",
            "final_review",
            state
        )


def router_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Router node for handling loop-back navigation to specific sections.
    
    This node processes user requests to edit specific sections of the plan
    and updates the state to navigate back to the appropriate agent stage.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with navigation to target section
    """
    with error_recovery_context("router", state):
        try:
            # Validate input state
            validate_experiment_plan_state(state)
            
            user_input = get_latest_user_input(state)
            
            # Determine which section the user wants to edit with fallback
            section_to_edit = determine_section_to_edit(user_input, state)
            
            # Validate the section choice
            from .state import PLANNING_STAGES
            if section_to_edit not in PLANNING_STAGES:
                logger.warning(f"Invalid section determined: {section_to_edit}, defaulting to objective_setting")
                section_to_edit = "objective_setting"
            
            # Add a message indicating the routing decision
            routing_message = f"Navigating to {section_to_edit.replace('_', ' ')} section for editing..."
            updated_state = add_chat_message(state, "system", routing_message)
            
            # Update the current stage to the target section
            updated_state = transition_to_stage(updated_state, section_to_edit)
            updated_state = update_state_timestamp(updated_state)
            
            # Validate output state
            validate_experiment_plan_state(updated_state)
            
            logger.info(f"Router node completed - directing to {section_to_edit}")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Router node execution failed: {str(e)}")
            
            # Create recovery state with error handling
            recovery_state = state.copy() if hasattr(state, 'copy') else dict(state)
            recovery_state = add_error(recovery_state, f"Router navigation failed: {str(e)}")
            recovery_state = add_chat_message(
                recovery_state,
                "system",
                "I had trouble understanding which section you want to edit. Let me start from the beginning."
            )
            
            # Default to objective setting as fallback
            try:
                recovery_state = transition_to_stage(recovery_state, "objective_setting")
                recovery_state = update_state_timestamp(recovery_state)
            except Exception as transition_error:
                logger.error(f"Fallback transition failed: {transition_error}")
                # Minimal state changes if transition fails
                recovery_state = add_error(recovery_state, f"Fallback failed: {transition_error}")
            
            return recovery_state


# Node registry for dynamic access
NODE_REGISTRY: Dict[str, Any] = {
    "objective_agent": objective_agent_node,
    "variable_agent": variable_agent_node,
    "design_agent": design_agent_node,
    "methodology_agent": methodology_agent_node,
    "data_agent": data_agent_node,
    "review_agent": review_agent_node,
    "router": router_node
}


def get_node_handler(node_name: str) -> Any:
    """
    Get a node handler function by name.
    
    Args:
        node_name: Name of the node handler to retrieve
        
    Returns:
        Node handler function
        
    Raises:
        KeyError: If node name is not found in registry
    """
    if node_name not in NODE_REGISTRY:
        raise KeyError(f"Node handler '{node_name}' not found in registry")
    
    return NODE_REGISTRY[node_name]


def get_available_nodes() -> list[str]:
    """
    Get list of available node names.
    
    Returns:
        List of available node handler names
    """
    return list(NODE_REGISTRY.keys()) 