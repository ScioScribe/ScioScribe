"""
Graph orchestration module for the experiment planning system.

This module organizes all graph-related functionality including error handling,
node management, routing logic, graph construction, and execution management
into a clean, modular structure.
"""

# Import all public APIs from the organized modules
from .graph import (
    # Core graph functionality
    create_planning_graph,
    PlanningGraphExecutor,
    
    # Node handlers
    objective_agent_node,
    variable_agent_node, 
    design_agent_node,
    methodology_agent_node,
    data_agent_node,
    review_agent_node,
    router_node,
    NODE_REGISTRY,
    get_node_handler,
    get_available_nodes,
    
    # Routing logic
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
    should_allow_stage_transition,
    
    # Error handling
    error_recovery_context,
    safe_agent_execution,
    safe_conditional_check,
    
    # Helper functions
    get_latest_user_input,
    determine_section_to_edit,
    get_stage_routing_map,
    get_stage_descriptions,
    get_completion_keywords,
    extract_user_intent,
    validate_stage_name,
    get_next_stage,
    get_previous_stage,
    calculate_progress_percentage,
    format_stage_name,
    is_terminal_stage,
    
    # Convenience functions
    start_new_experiment_planning,
    execute_planning_conversation,
    get_planning_graph_info,
    create_planning_session,
    validate_planning_system
)

# Import individual modules for direct access if needed
from . import error_handling
from . import node_handlers
from . import routing
from . import graph_builder
from . import executor
from . import helpers

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
    "get_completion_keywords",
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
    
    # Individual modules for direct access
    "error_handling",
    "node_handlers", 
    "routing",
    "graph_builder",
    "executor",
    "helpers"
] 