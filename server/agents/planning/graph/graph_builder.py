"""
Simplified graph builder for experiment planning with LangGraph HITL.

This module creates a clean, linear planning graph using LangGraph's
built-in interrupt_before mechanism and direct agent instances.
"""

import logging
from typing import Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from ..state import ExperimentPlanState
from ..agents import (
    ObjectiveAgent,
    VariableAgent,
    DesignAgent,
    MethodologyAgent,
    DataAgent,
    ReviewAgent
)
from .routing import (
    objective_completion_check,
    variable_completion_check,
    design_completion_check,
    methodology_completion_check,
    data_completion_check,
    review_completion_check,
    route_to_section
)
from .helpers import determine_section_to_edit
from .error_handling import get_latest_user_input
from ..factory import add_chat_message
from ..transitions import transition_to_stage

logger = logging.getLogger(__name__)


def create_agent_node(agent_class, stage: str):
    """Create a simple LangGraph node from an agent class."""
    def agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
        # Get user input and execute agent
        user_input = get_latest_user_input(state)
        agent = agent_class()
        result = agent.execute(state, user_input)
        
        # Ensure correct stage
        if result.get('current_stage') != stage:
            result = transition_to_stage(result, stage)
        
        return result
    
    return agent_node


def create_router_node():
    """Create a simple router node for section editing."""
    def router_node(state: ExperimentPlanState) -> ExperimentPlanState:
        user_input = get_latest_user_input(state)
        section_to_edit = determine_section_to_edit(user_input, state)
        
        # Add routing message and transition
        updated_state = add_chat_message(
            state, 
            "system", 
            f"Navigating to {section_to_edit.replace('_', ' ')} section for editing..."
        )
        return transition_to_stage(updated_state, section_to_edit)
    
    return router_node


def create_return_router_node():
    """Create a return router node that routes back to the original stage after an edit."""
    def return_router_node(state: ExperimentPlanState) -> ExperimentPlanState:
        return_to_stage = state.get('return_to_stage')
        if return_to_stage:
            logger.info(f"[RETURN] Returning to original stage: {return_to_stage}")
            
            # Clear the return_to_stage flag
            updated_state = state.copy()
            updated_state.pop('return_to_stage', None)
            
            # Add system message about returning
            updated_state = add_chat_message(
                updated_state,
                "system",
                f"Edit completed! Returning to the {return_to_stage.replace('_', ' ')} stage."
            )
            
            # Transition back to the original stage
            return transition_to_stage(updated_state, return_to_stage)
        else:
            # Fallback to objective if no return stage specified
            logger.warning("[RETURN] No return_to_stage found, defaulting to objective_setting")
            return transition_to_stage(state, "objective_setting")
    
    return return_router_node


def create_stage_return_router():
    """Create a router that determines which stage to return to based on return_to_stage."""
    def stage_return_router(state: ExperimentPlanState) -> str:
        return_to_stage = state.get('return_to_stage')
        if not return_to_stage:
            return "objective"
        
        # Map stages to routing keys
        stage_routing_map = {
            "objective_setting": "objective",
            "variable_identification": "variables",
            "experimental_design": "design",
            "methodology_protocol": "methodology",
            "data_planning": "data_planning",
            "final_review": "review"
        }
        
        routing_key = stage_routing_map.get(return_to_stage, "objective")
        logger.info(f"[RETURN_ROUTER] Routing back to {routing_key} (stage: {return_to_stage})")
        return routing_key
    
    return stage_return_router


def create_planning_graph(
    debugger: Optional = None,
    log_level: str = "INFO",
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> StateGraph:
    """
    Create a simplified planning graph with HITL capabilities.
    
    Args:
        debugger: Optional debugger (unused in simplified version)
        log_level: Logging level
        checkpointer: State persistence (defaults to MemorySaver)
        
    Returns:
        Compiled StateGraph with HITL capabilities
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    logger.info("Creating simplified planning graph")
    
    # Initialize graph
    graph = StateGraph(ExperimentPlanState)
    
    # Add agent nodes
    graph.add_node("objective_agent", create_agent_node(ObjectiveAgent, "objective_setting"))
    graph.add_node("variable_agent", create_agent_node(VariableAgent, "variable_identification"))
    graph.add_node("design_agent", create_agent_node(DesignAgent, "experimental_design"))
    graph.add_node("methodology_agent", create_agent_node(MethodologyAgent, "methodology_protocol"))
    graph.add_node("data_agent", create_agent_node(DataAgent, "data_planning"))
    graph.add_node("review_agent", create_agent_node(ReviewAgent, "final_review"))
    graph.add_node("router", create_router_node())
    graph.add_node("return_router", create_return_router_node())
    
    # Set entry point
    graph.set_entry_point("objective_agent")
    
    # Add linear flow with completion checks (now including return_to_original)
    graph.add_conditional_edges("objective_agent", objective_completion_check, 
                               {"continue": "variable_agent", "retry": "objective_agent", "return_to_original": "return_router"})
    graph.add_conditional_edges("variable_agent", variable_completion_check, 
                               {"continue": "design_agent", "retry": "variable_agent", "return_to_original": "return_router"})
    graph.add_conditional_edges("design_agent", design_completion_check, 
                               {"continue": "methodology_agent", "retry": "design_agent", "return_to_original": "return_router"})
    graph.add_conditional_edges("methodology_agent", methodology_completion_check, 
                               {"continue": "data_agent", "retry": "methodology_agent", "return_to_original": "return_router"})
    graph.add_conditional_edges("data_agent", data_completion_check, 
                               {"continue": "review_agent", "retry": "data_agent", "return_to_original": "return_router"})
    graph.add_conditional_edges("review_agent", review_completion_check, 
                               {"complete": END, "edit_section": "router"})
    
    # Router for section editing
    graph.add_conditional_edges("router", route_to_section, {
        "objective": "objective_agent",
        "variables": "variable_agent", 
        "design": "design_agent",
        "methodology": "methodology_agent",
        "data_planning": "data_agent",
        "review": "review_agent"
    })
    
    # Return router for returning to original stage after edits
    graph.add_conditional_edges("return_router", create_stage_return_router(), {
        "objective": "objective_agent",
        "variables": "variable_agent",
        "design": "design_agent", 
        "methodology": "methodology_agent",
        "data_planning": "data_agent",
        "review": "review_agent"
    })
    
    # Compile with interrupts for user approval
    compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["variable_agent", "design_agent", "methodology_agent", "data_agent", "review_agent"]
    )
    
    logger.info("Simplified planning graph compiled successfully")
    return compiled_graph 