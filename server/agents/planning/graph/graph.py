"""
Main LangGraph orchestration for the experiment planning agent system.

This module provides the public API for the experiment planning graph system,
exposing all the core functionality through a clean interface. The actual
implementation is distributed across specialized modules for better maintainability.

This refactored version organizes the original 1000+ line file into focused modules:
- error_handling.py: Error recovery and safe execution
- node_handlers.py: Agent node wrapper functions  
- routing.py: Conditional routing logic
- graph_builder.py: Graph construction and compilation
- executor.py: Execution management and monitoring
- helpers.py: Utility functions
"""

from typing import Dict, Any, List, Optional, Tuple
import logging

# Core imports from focused modules
from .graph_builder import create_planning_graph
from .executor import PlanningGraphExecutor
from .error_handling import safe_conditional_check, get_latest_user_input
from .routing import (
    objective_completion_check,
    variable_completion_check,
    design_completion_check,
    methodology_completion_check,
    data_completion_check,
    review_completion_check,
    route_to_section,
    validate_stage_completion,
    get_incomplete_stages,
    get_routing_options,
    should_allow_stage_transition
)
from .helpers import (
    determine_section_to_edit,
    get_stage_routing_map,
    get_stage_descriptions,

    extract_user_intent,
    validate_stage_name,
    get_next_stage,
    get_previous_stage,
    calculate_progress_percentage,
    format_stage_name,
    is_terminal_stage
)

# State and configuration imports
from ..state import ExperimentPlanState, PLANNING_STAGES
from ..debug import StateDebugger, get_global_debugger

logger = logging.getLogger(__name__)


# ==================== CONVENIENCE FUNCTIONS ====================

def start_new_experiment_planning(research_query: str, experiment_id: str = None):
    """Start a new experiment planning session."""
    from ..factory import create_new_experiment_state
    return create_new_experiment_state(research_query, experiment_id)

def execute_planning_conversation(state, user_input: str):
    """Execute a planning conversation step."""
    # This would integrate with the graph execution
    pass

def get_planning_graph_info():
    """Get information about the planning graph structure."""
    return {
        "stages": ["objective_setting", "variable_identification", "experimental_design", 
                  "methodology_protocol", "data_planning", "final_review"],
        "agents": ["ObjectiveAgent", "VariableAgent", "DesignAgent", 
                  "MethodologyAgent", "DataAgent", "ReviewAgent"],
        "features": ["Human-in-the-loop", "Checkpointing", "Error recovery"]
    }

def create_planning_session():
    """Create a new planning session."""
    return create_planning_graph()

def validate_planning_system():
    """Validate the planning system setup."""
    try:
        graph = create_planning_graph()
        return {"status": "valid", "graph": graph is not None}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}


# ==================== EXPORTS ====================

__all__ = [
    # Core graph functionality
    "create_planning_graph",
    "PlanningGraphExecutor",
    
    # Node handlers
    "objective_agent_node",
    "variable_agent_node", 
    "design_agent_node",
    "methodology_agent_node",
    "data_agent_node",
    "review_agent_node",
    "router_node",
    "NODE_REGISTRY",
    "get_node_handler",
    "get_available_nodes",
    
    # Routing logic
    "objective_completion_check",
    "variable_completion_check",
    "design_completion_check", 
    "methodology_completion_check",
    "data_completion_check",
    "review_completion_check",
    "route_to_section",
    "validate_stage_completion",
    "get_incomplete_stages",
    "get_routing_options",
    "should_allow_stage_transition",
    
    # Error handling
    "error_recovery_context",
    "safe_agent_execution",
    "safe_conditional_check",
    
    # Helper functions
    "get_latest_user_input",
    "determine_section_to_edit",
    "get_stage_routing_map",
    "get_stage_descriptions",

    "extract_user_intent",
    "validate_stage_name",
    "get_next_stage",
    "get_previous_stage",
    "calculate_progress_percentage",
    "format_stage_name",
    "is_terminal_stage",
    
    # Convenience functions
    "start_new_experiment_planning",
    "execute_planning_conversation",
    "get_planning_graph_info",
    "create_planning_session",
    "validate_planning_system",
    
    # HITL-specific functions
    "check_user_approval",
    
    # State and configuration
    "ExperimentPlanState",
    "PLANNING_STAGES",
    "StateDebugger",
    "get_global_debugger"
] 