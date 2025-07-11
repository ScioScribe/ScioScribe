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

from ..state import ExperimentPlanState, PLANNING_STAGES
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
from .helpers import determine_section_to_edit, get_latest_user_input
from ..factory import add_chat_message
from ..transitions import transition_to_stage

logger = logging.getLogger(__name__)


def create_agent_node(agent_class, stage: str):
    """Create a simple LangGraph node from an agent class."""
    def agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
        # 🔍 DEBUG LOG 10: Agent node execution with state preservation
        logger.info(f"🔍 DEBUG 10 - AGENT NODE EXECUTION ({stage}):")
        logger.info(f"   Agent: {agent_class.__name__}")
        logger.info(f"   Target stage: '{stage}'")
        logger.info(f"   Input state stage: '{state.get('current_stage', 'unknown')}'")
        logger.info(f"   Return to stage in input: '{state.get('return_to_stage', 'not set')}'")
        
        # Preserve critical state flags before agent execution
        critical_state = {
            'return_to_stage': state.get('return_to_stage'),
            'experiment_id': state.get('experiment_id'),
            'edit_context': state.get('edit_context'),
            'chat_history': state.get('chat_history', []).copy() if state.get('chat_history') else []
        }
        
        logger.info(f"🔍 DEBUG 10a - PRESERVING CRITICAL STATE:")
        logger.info(f"   Preserved return_to_stage: '{critical_state['return_to_stage']}'")
        logger.info(f"   Preserved experiment_id: '{critical_state['experiment_id']}'")
        logger.info(f"   Preserved chat_history length: {len(critical_state['chat_history'])}")
        
        # Get user input and execute agent
        user_input = get_latest_user_input(state)
        agent = agent_class()
        result = agent.execute(state, user_input)
        
        logger.info(f"🔍 DEBUG 10b - AGENT EXECUTION COMPLETE:")
        logger.info(f"   Result stage: '{result.get('current_stage', 'unknown')}'")
        logger.info(f"   Return to stage in result: '{result.get('return_to_stage', 'not set')}'")
        logger.info(f"   Agent changed return_to_stage: {critical_state['return_to_stage'] != result.get('return_to_stage')}")
        
        # Restore critical state if it was lost during agent execution
        if critical_state['return_to_stage'] and not result.get('return_to_stage'):
            logger.info(f"🔍 DEBUG 10c - RESTORING LOST return_to_stage:")
            logger.info(f"   Restoring: '{critical_state['return_to_stage']}'")
            result['return_to_stage'] = critical_state['return_to_stage']
        
        # Preserve other critical flags
        if critical_state['edit_context'] and not result.get('edit_context'):
            result['edit_context'] = critical_state['edit_context']
            logger.info(f"🔍 DEBUG 10d - RESTORED edit_context")
        
        # Ensure correct stage is set
        if result.get('current_stage') != stage:
            logger.info(f"🔍 DEBUG 10e - CORRECTING STAGE:")
            logger.info(f"   Expected: '{stage}', Got: '{result.get('current_stage')}'")
            result = transition_to_stage(result, stage)
            
            # Re-restore return_to_stage after transition (in case transition clears it)
            if critical_state['return_to_stage']:
                result['return_to_stage'] = critical_state['return_to_stage']
                logger.info(f"🔍 DEBUG 10f - RE-RESTORED return_to_stage after transition")
        
        logger.info(f"🔍 DEBUG 10g - FINAL AGENT NODE STATE:")
        logger.info(f"   Final stage: '{result.get('current_stage', 'unknown')}'")
        logger.info(f"   Final return_to_stage: '{result.get('return_to_stage', 'not set')}'")
        logger.info(f"   State preservation successful: {bool(critical_state['return_to_stage'] == result.get('return_to_stage'))}")
        
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
        
        # 🔍 DEBUG LOG 6: Return router analysis
        logger.info(f"🔍 DEBUG 6 - RETURN ROUTER ANALYSIS:")
        logger.info(f"   Current stage: '{state.get('current_stage', 'unknown')}'")
        logger.info(f"   Return to stage: '{return_to_stage}'")
        logger.info(f"   Return stage type: {type(return_to_stage)}")
        logger.info(f"   Is return stage valid: {return_to_stage in PLANNING_STAGES if return_to_stage else False}")
        logger.info(f"   Available stages: {PLANNING_STAGES}")
        logger.info(f"   State keys: {list(state.keys())}")
        
        # Check if there's chat history for context
        chat_history = state.get('chat_history', [])
        logger.info(f"   Chat history length: {len(chat_history)}")
        if chat_history:
            logger.info(f"   Last chat message: '{chat_history[-1].get('content', 'no content')[:100]}...'")
        
        if return_to_stage and return_to_stage in PLANNING_STAGES:
            logger.info(f"[RETURN] Returning to original stage: {return_to_stage}")
            logger.info(f"🔍 DEBUG 6a - VALID RETURN: Proceeding with return to '{return_to_stage}'")
            
            # Clear the return_to_stage flag first
            updated_state = state.copy() if hasattr(state, 'copy') else dict(state)
            updated_state.pop('return_to_stage', None)
            
            logger.info(f"🔍 DEBUG 6b - RETURN CLEANUP:")
            logger.info(f"   Cleared return_to_stage flag")
            logger.info(f"   State after cleanup: {updated_state.get('return_to_stage', 'successfully cleared')}")
            
            # Add system message about returning
            updated_state = add_chat_message(
                updated_state,
                "system",
                f"✅ Edit completed! Returning to the {return_to_stage.replace('_', ' ')} stage."
            )
            
            # Transition back to the original stage
            updated_state = transition_to_stage(updated_state, return_to_stage)
            
            logger.info(f"🔍 DEBUG 6c - RETURN TRANSITION:")
            logger.info(f"   Transitioned back to: '{updated_state.get('current_stage', 'unknown')}'")
            logger.info(f"   Transition successful: {updated_state.get('current_stage') == return_to_stage}")
            
            logger.info(f"[RETURN] Successfully returned to {return_to_stage}")
            return updated_state
        else:
            # Fallback: if no return stage specified, go to objective_setting
            logger.warning(f"[RETURN] No valid return_to_stage found (was: {return_to_stage}), defaulting to objective_setting")
            logger.info(f"🔍 DEBUG 6d - FALLBACK RETURN:")
            logger.info(f"   Invalid return_to_stage: '{return_to_stage}'")
            logger.info(f"   Reason: {'not in PLANNING_STAGES' if return_to_stage else 'None/empty'}")
            logger.info(f"   Falling back to: 'objective_setting'")
            
            # Clear any invalid return_to_stage flag
            updated_state = state.copy() if hasattr(state, 'copy') else dict(state)
            updated_state.pop('return_to_stage', None)
            
            # Add system message about fallback
            updated_state = add_chat_message(
                updated_state,
                "system",
                "Edit completed! Continuing with the planning process."
            )
            
            # Transition to objective_setting as fallback
            updated_state = transition_to_stage(updated_state, "objective_setting")
            
            logger.info(f"🔍 DEBUG 6e - FALLBACK RESULT:")
            logger.info(f"   Final stage: '{updated_state.get('current_stage', 'unknown')}'")
            
            return updated_state
    
    return return_router_node


def create_stage_return_router():
    """Create a return router function that determines where to route after completing an edit."""
    def stage_return_router(state: ExperimentPlanState) -> str:
        """Route back to the original stage after completing an edit."""
        return_to_stage = state.get('return_to_stage')
        
        # 🔍 DEBUG LOG 7: Stage return router routing decision
        logger.info(f"🔍 DEBUG 7 - STAGE RETURN ROUTER:")
        logger.info(f"   Current stage: '{state.get('current_stage', 'unknown')}'")
        logger.info(f"   Return to stage: '{return_to_stage}'")
        logger.info(f"   Return stage valid: {return_to_stage in PLANNING_STAGES if return_to_stage else False}")
        
        if return_to_stage and return_to_stage in PLANNING_STAGES:
            logger.info(f"[RETURN] Routing back to original stage: {return_to_stage}")
            # Map stage to routing key
            stage_routing_map = {
                "objective_setting": "objective",
                "variable_identification": "variables",
                "experimental_design": "design",
                "methodology_protocol": "methodology",
                "data_planning": "data_planning",
                "final_review": "review"
            }
            
            routing_key = stage_routing_map.get(return_to_stage, "objective")
            logger.info(f"🔍 DEBUG 7a - ROUTING DECISION:")
            logger.info(f"   Stage to route to: '{return_to_stage}'")
            logger.info(f"   Routing key: '{routing_key}'")
            logger.info(f"   Routing map: {stage_routing_map}")
            
            return routing_key
        else:
            logger.warning(f"[RETURN] No valid return_to_stage, defaulting to objective")
            logger.info(f"🔍 DEBUG 7b - DEFAULT ROUTING:")
            logger.info(f"   No valid return stage found")
            logger.info(f"   Defaulting to: 'objective'")
            return "objective"
    
    return stage_return_router


def create_dispatcher_node():
    """Create a dispatcher node that routes to the correct agent based on current_stage."""
    def dispatcher_node(state: ExperimentPlanState) -> ExperimentPlanState:
        current_stage = state.get('current_stage', 'objective_setting')
        
        logger.info(f"🔍 DISPATCHER - Routing to stage: '{current_stage}'")
        logger.info(f"   Available stages: {PLANNING_STAGES}")
        logger.info(f"   Return to stage: '{state.get('return_to_stage', 'not set')}'")
        
        # Just pass through the state - the conditional routing will handle the rest
        return state
    
    return dispatcher_node


def create_dispatcher_router():
    """Create a router function that determines which agent to run based on current_stage."""
    def dispatcher_router(state: ExperimentPlanState) -> str:
        current_stage = state.get('current_stage', 'objective_setting')
        
        # Map stage to routing key
        stage_routing_map = {
            "objective_setting": "objective",
            "variable_identification": "variables",
            "experimental_design": "design",
            "methodology_protocol": "methodology",
            "data_planning": "data_planning",
            "final_review": "review"
        }
        
        routing_key = stage_routing_map.get(current_stage, "objective")
        logger.info(f"🔍 DISPATCHER ROUTER - Stage: '{current_stage}' -> Route: '{routing_key}'")
        
        return routing_key
    
    return dispatcher_router


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
    graph.add_node("dispatcher", create_dispatcher_node())
    
    # Set entry point
    graph.set_entry_point("dispatcher")
    
    # Add dispatcher routing to correct agent based on current_stage
    graph.add_conditional_edges("dispatcher", create_dispatcher_router(), {
        "objective": "objective_agent",
        "variables": "variable_agent", 
        "design": "design_agent",
        "methodology": "methodology_agent",
        "data_planning": "data_agent",
        "review": "review_agent"
    })
    
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