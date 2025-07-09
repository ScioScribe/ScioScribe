"""
Human-in-the-loop enabled graph builder for experiment planning.

This module implements proper LangGraph HITL functionality with interrupts,
checkpoints, and user approval mechanisms for frontend integration.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from ..state import ExperimentPlanState
from ..agents import (
    ObjectiveAgent,
    VariableAgent,
    DesignAgent,
    MethodologyAgent,
    DataAgent,
    ReviewAgent
)
from .node_handlers import (
    objective_agent_node,
    variable_agent_node,
    design_agent_node,
    methodology_agent_node,
    data_agent_node,
    review_agent_node,
    router_node
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
from ..debug import StateDebugger, get_global_debugger

logger = logging.getLogger(__name__)


def create_planning_graph(
    debugger: Optional[StateDebugger] = None,
    log_level: str = "INFO",
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> StateGraph:
    """
    Create a human-in-the-loop enabled planning graph.
    
    This function creates a graph with proper interrupt mechanisms,
    checkpointing, and user approval flows for frontend integration.
    
    Args:
        debugger: Optional StateDebugger instance for logging
        log_level: Logging level for the graph
        checkpointer: Checkpointer for state persistence (defaults to MemorySaver)
        
    Returns:
        Compiled StateGraph with HITL capabilities
    """
    if debugger is None:
        debugger = get_global_debugger()
    
    # Use MemorySaver if no checkpointer is provided
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    logger.info("Creating HITL planning graph with checkpointing")
    
    # Initialize the StateGraph with ExperimentPlanState
    graph = StateGraph(ExperimentPlanState)
    
    # Add agent nodes with human-in-the-loop capabilities
    logger.info("Adding agent nodes with HITL support")
    graph.add_node("objective_agent", objective_agent_node)
    graph.add_node("variable_agent", variable_agent_node)
    graph.add_node("design_agent", design_agent_node)
    graph.add_node("methodology_agent", methodology_agent_node)
    graph.add_node("data_agent", data_agent_node)
    graph.add_node("review_agent", review_agent_node)
    
    # Add approval nodes for user review
    graph.add_node("objective_approval", create_approval_node("objective"))
    graph.add_node("variable_approval", create_approval_node("variables"))
    graph.add_node("design_approval", create_approval_node("design"))
    graph.add_node("methodology_approval", create_approval_node("methodology"))
    graph.add_node("data_approval", create_approval_node("data"))
    graph.add_node("final_approval", create_approval_node("final"))
    
    # Add router for section editing
    graph.add_node("router", router_node)
    
    # Set entry point
    graph.set_entry_point("objective_agent")
    
    # Add edges with human-in-the-loop checkpoints
    logger.info("Adding edges with HITL checkpoints")
    
    # Objective -> Approval -> Variables
    graph.add_conditional_edges(
        "objective_agent",
        objective_completion_check,
        {
            "continue": "objective_approval",
            "retry": "objective_agent"
        }
    )
    
    graph.add_conditional_edges(
        "objective_approval",
        check_user_approval,
        {
            "approved": "variable_agent",
            "rejected": "objective_agent",
            "waiting": "objective_approval"
        }
    )
    
    # Variables -> Approval -> Design
    graph.add_conditional_edges(
        "variable_agent",
        variable_completion_check,
        {
            "continue": "variable_approval",
            "retry": "variable_agent"
        }
    )
    
    graph.add_conditional_edges(
        "variable_approval",
        check_user_approval,
        {
            "approved": "design_agent",
            "rejected": "variable_agent",
            "waiting": "variable_approval"
        }
    )
    
    # Design -> Approval -> Methodology
    graph.add_conditional_edges(
        "design_agent",
        design_completion_check,
        {
            "continue": "design_approval",
            "retry": "design_agent"
        }
    )
    
    graph.add_conditional_edges(
        "design_approval",
        check_user_approval,
        {
            "approved": "methodology_agent",
            "rejected": "design_agent",
            "waiting": "design_approval"
        }
    )
    
    # Methodology -> Approval -> Data
    graph.add_conditional_edges(
        "methodology_agent",
        methodology_completion_check,
        {
            "continue": "methodology_approval",
            "retry": "methodology_agent"
        }
    )
    
    graph.add_conditional_edges(
        "methodology_approval",
        check_user_approval,
        {
            "approved": "data_agent",
            "rejected": "methodology_agent",
            "waiting": "methodology_approval"
        }
    )
    
    # Data -> Approval -> Review
    graph.add_conditional_edges(
        "data_agent",
        data_completion_check,
        {
            "continue": "data_approval",
            "retry": "data_agent"
        }
    )
    
    graph.add_conditional_edges(
        "data_approval",
        check_user_approval,
        {
            "approved": "review_agent",
            "rejected": "data_agent",
            "waiting": "data_approval"
        }
    )
    
    # Review -> Final Approval -> End
    graph.add_conditional_edges(
        "review_agent",
        review_completion_check,
        {
            "complete": "final_approval",
            "edit_section": "router"
        }
    )
    
    graph.add_conditional_edges(
        "final_approval",
        check_user_approval,
        {
            "approved": END,
            "rejected": "router",
            "waiting": "final_approval"
        }
    )
    
    # Router for section editing
    graph.add_conditional_edges(
        "router",
        route_to_section,
        {
            "objective": "objective_agent",
            "variables": "variable_agent",
            "design": "design_agent",
            "methodology": "methodology_agent",
            "data_planning": "data_agent",
            "review": "review_agent"
        }
    )
    
    # Compile graph with checkpointing and interrupts
    logger.info("Compiling HITL graph with checkpointing")
    
    # Set interrupt points for human approval
    compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "objective_approval",
            "variable_approval", 
            "design_approval",
            "methodology_approval",
            "data_approval",
            "final_approval"
        ]
    )
    
    logger.info("HITL planning graph compiled successfully")
    return compiled_graph


def create_approval_node(stage: str):
    """
    Create an approval node for a specific planning stage.
    
    This node waits for user approval before proceeding to the next stage.
    Uses a truly idempotent approach to prevent infinite approval loops.
    """
    def approval_node(state: ExperimentPlanState) -> ExperimentPlanState:
        """Node that waits for user approval."""
        logger.info(f"Approval node for {stage} stage")
        
        # Make a copy of the state to avoid mutating the original
        state = state.copy()
        
        # Initialize approvals dictionary if it doesn't exist
        if 'approvals' not in state:
            state['approvals'] = {}
        
        # CRITICAL: Check if this stage has already been approved (idempotent guard)
        # This prevents infinite loops when LangGraph replays the approval node
        if state['approvals'].get(stage, False):
            logger.info(f"Stage {stage} already approved, returning clean state")
            # Ensure pending_approval is cleared for approved stages
            state['pending_approval'] = None
            return state
        
        # Check if user has provided approval in recent chat history
        chat_history = state.get('chat_history', [])
        
        # Look for recent approval in the last few messages
        for message in reversed(chat_history[-5:]):  # Check last 5 messages
            if message.get('role') == 'user':
                content = message.get('content', '').lower().strip()
                if any(keyword in content for keyword in ['approve', 'approved', 'yes', 'good', 'continue', 'proceed', 'ok', 'okay']):
                    logger.info(f"User has approved {stage} stage, setting approval flag and clearing pending approval")
                    # Set the permanent approval flag
                    state['approvals'][stage] = True
                    # Clear pending approval since we're now approved
                    state['pending_approval'] = None
                    return state
                
                # Check for rejection keywords
                if any(keyword in content for keyword in ['reject', 'rejected', 'no', 'change', 'modify', 'edit', 'revise']):
                    logger.info(f"User has rejected {stage} stage, clearing approval flag")
                    # Clear any approval flag for this stage
                    state['approvals'][stage] = False
                    # Clear pending approval since we're handling the rejection
                    state['pending_approval'] = None
                    return state
                
                # If we found a user message, we've checked the most recent input
                break
        
        # Only create approval request if:
        # 1. Stage hasn't been approved yet
        # 2. There's no pending approval for this stage already
        # 3. User hasn't provided approval/rejection in recent messages
        existing_pending = state.get('pending_approval', {})
        if existing_pending and existing_pending.get('stage') == stage:
            logger.info(f"Approval request for {stage} already exists, returning existing state")
            return state
        
        # Create new approval request
        logger.info(f"Creating new approval request for {stage} stage")
        state['pending_approval'] = {
            'stage': stage,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'waiting'
        }
        
        # Add message to chat history
        approval_message = f"Please review the {stage} section. Do you approve this section to continue?"
        state['chat_history'].append({
            'timestamp': datetime.utcnow(),
            'role': 'system',
            'content': approval_message
        })
        
        return state
    
    return approval_node


def check_user_approval(state: ExperimentPlanState) -> str:
    """
    Check if user has approved the current stage.
    
    This function is called by conditional edges to determine routing.
    It should NOT mutate state since those changes won't be persisted.
    All state mutations should happen in the approval node itself.
    
    Returns:
        "approved" if user approved
        "rejected" if user rejected 
        "waiting" if still waiting for approval
    """
    # Get the stage from pending approval
    pending_approval = state.get('pending_approval', {})
    stage = pending_approval.get('stage') if pending_approval else None
    
    # If there's no pending approval or stage, we're not in an approval state
    if not stage:
        logger.info("No pending approval stage found, returning waiting")
        return "waiting"
    
    # Initialize approvals dictionary if it doesn't exist
    if 'approvals' not in state:
        # Don't mutate state here - this should be handled in the approval node
        logger.info("No approvals dictionary found, returning waiting")
        return "waiting"
    
    # PRIORITY 1: Check if this stage has already been approved (persistent flag)
    # This is the most reliable check and prevents infinite loops
    if state['approvals'].get(stage, False):
        logger.info(f"Stage {stage} already approved via persistent flag, returning approved")
        return "approved"
    
    # PRIORITY 2: Check if this stage has been explicitly rejected
    if state['approvals'].get(stage) is False:
        logger.info(f"Stage {stage} was rejected, returning rejected")
        return "rejected"
    
    # PRIORITY 3: Check latest user input for approval/rejection
    # NOTE: We don't mutate state here - the approval node will handle that
    chat_history = state.get('chat_history', [])
    for message in reversed(chat_history[-5:]):  # Check last 5 messages
        if message.get('role') == 'user':
            content = message.get('content', '').lower().strip()
            
            # Check for approval keywords
            if any(keyword in content for keyword in ['approve', 'approved', 'yes', 'good', 'continue', 'proceed', 'ok', 'okay']):
                logger.info(f"User approved {stage} stage via chat, returning approved")
                # NOTE: Don't set the approval flag here - the approval node will handle it
                return "approved"
            
            # Check for rejection keywords
            if any(keyword in content for keyword in ['reject', 'rejected', 'no', 'change', 'modify', 'edit', 'revise']):
                logger.info(f"User rejected {stage} stage via chat, returning rejected")
                # NOTE: Don't set the rejection flag here - the approval node will handle it
                return "rejected"
            
            # If we found a user message, we've checked the most recent input
            break
    
    # Default: still waiting for approval
    logger.info(f"Still waiting for approval for stage {stage}")
    return "waiting" 