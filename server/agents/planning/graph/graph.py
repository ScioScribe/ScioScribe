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
from .graph_builder import (
    create_planning_graph,
    check_user_approval
)
from .executor import PlanningGraphExecutor
from .error_handling import error_recovery_context, safe_agent_execution, safe_conditional_check
from .node_handlers import (
    objective_agent_node,
    variable_agent_node,
    design_agent_node,
    methodology_agent_node,
    data_agent_node,
    review_agent_node,
    router_node,
    NODE_REGISTRY,
    get_node_handler,
    get_available_nodes
)
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
    is_terminal_stage
)

# State and configuration imports
from ..state import ExperimentPlanState, PLANNING_STAGES
from ..debug import StateDebugger, get_global_debugger

logger = logging.getLogger(__name__)


# ==================== CONVENIENCE FUNCTIONS ====================

def start_new_experiment_planning(
    research_query: str, 
    experiment_id: Optional[str] = None,
    debugger: Optional[StateDebugger] = None,
    log_level: str = "INFO"
) -> Tuple[PlanningGraphExecutor, ExperimentPlanState]:
    """
    Convenience function to start a new experiment planning session.
    
    This function initializes a complete planning system with executor
    and initial state, ready for user interaction.
    
    Args:
        research_query: User's initial research question
        experiment_id: Optional experiment ID (auto-generated if not provided)
        debugger: Optional StateDebugger instance for logging
        log_level: Logging level for the system
        
    Returns:
        Tuple of (executor, initial_state) ready for planning
        
    Raises:
        RuntimeError: If initialization fails
    """
    try:
        # Create and initialize executor
        executor = PlanningGraphExecutor(debugger=debugger, log_level=log_level)
        executor.initialize_graph()
        
        # Create initial state
        initial_state = executor.create_initial_state(research_query, experiment_id)
        
        logger.info(f"Started new experiment planning session: {initial_state['experiment_id']}")
        
        return executor, initial_state
        
    except Exception as e:
        logger.error(f"Failed to start new experiment planning: {str(e)}")
        raise RuntimeError(f"Planning session initialization failed: {str(e)}") from e


def execute_planning_conversation(
    research_query: str,
    user_inputs: List[str],
    experiment_id: Optional[str] = None,
    debugger: Optional[StateDebugger] = None,
    log_level: str = "INFO"
) -> ExperimentPlanState:
    """
    Execute a complete planning conversation with predefined user inputs.
    
    This function is useful for automated testing or batch processing
    of planning conversations with known input sequences.
    
    Args:
        research_query: Initial research question
        user_inputs: List of user inputs for the conversation
        experiment_id: Optional experiment ID (auto-generated if not provided)
        debugger: Optional StateDebugger instance for logging
        log_level: Logging level for the system
        
    Returns:
        Final ExperimentPlanState after processing all inputs
        
    Raises:
        RuntimeError: If conversation execution fails
    """
    try:
        # Start new planning session
        executor, state = start_new_experiment_planning(
            research_query, experiment_id, debugger, log_level
        )
        
        # Execute initial step to get first agent response
        state = executor.execute_step(state)
        
        # Process each user input in sequence
        for i, user_input in enumerate(user_inputs):
            if user_input.strip():
                logger.info(f"Processing user input {i+1}/{len(user_inputs)}: {user_input[:50]}...")
                state = executor.execute_step(state, user_input)
        
        logger.info(f"Completed planning conversation for experiment: {state['experiment_id']}")
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to execute planning conversation: {str(e)}")
        raise RuntimeError(f"Conversation execution failed: {str(e)}") from e


def get_planning_graph_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the planning graph system.
    
    Returns:
        Dictionary with detailed system information
    """
    # Basic graph metadata since get_graph_metadata might not exist in v2
    base_info = {
        "graph_type": "LangGraph StateGraph with HITL",
        "state_type": "ExperimentPlanState",
        "features": ["Human-in-the-loop approval", "Real-time streaming", "State checkpointing"]
    }
    
    # Add additional system information
    system_info = {
        "planning_stages": PLANNING_STAGES,
        "stage_descriptions": get_stage_descriptions(),
        "stage_routing_map": get_stage_routing_map(),
        "completion_keywords": get_completion_keywords(),
        "available_nodes": get_available_nodes(),
        "system_features": [
            "Multi-agent conversational planning",
            "Comprehensive error handling and recovery",
            "State persistence and validation",
            "Loop-back navigation for editing",
            "Progress tracking and metrics",
            "Structured plan export",
            "Domain-specific biotech knowledge",
            "Statistical power calculations",
            "Web search integration (Tavily)",
            "Interactive debugging and monitoring"
        ]
    }
    
    return {**base_info, **system_info}


def create_planning_session(
    research_query: str,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new planning session with optional configuration.
    
    This function provides a higher-level interface for creating
    planning sessions with custom configurations.
    
    Args:
        research_query: User's initial research question
        config: Optional configuration dictionary
        
    Returns:
        Dictionary containing session information and executor
    """
    try:
        # Extract configuration parameters
        config = config or {}
        experiment_id = config.get('experiment_id')
        log_level = config.get('log_level', 'INFO')
        debugger = config.get('debugger')
        
        # Create planning session
        executor, initial_state = start_new_experiment_planning(
            research_query=research_query,
            experiment_id=experiment_id,
            debugger=debugger,
            log_level=log_level
        )
        
        # Get initial status
        status = executor.get_execution_status(initial_state)
        
        session_info = {
            "session_id": initial_state['experiment_id'],
            "executor": executor,
            "initial_state": initial_state,
            "status": status,
            "config": config,
            "created_at": initial_state.get('created_at'),
            "graph_info": executor.get_graph_info()
        }
        
        logger.info(f"Created planning session: {session_info['session_id']}")
        
        return session_info
        
    except Exception as e:
        logger.error(f"Failed to create planning session: {str(e)}")
        raise RuntimeError(f"Session creation failed: {str(e)}") from e


def validate_planning_system() -> Dict[str, Any]:
    """
    Validate the planning system configuration and dependencies.
    
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        "system_status": "healthy",
        "components": {},
        "errors": [],
        "warnings": []
    }
    
    try:
        # Test graph creation
        try:
            graph = create_planning_graph()
            validation_results["components"]["graph_builder"] = "ok"
        except Exception as e:
            validation_results["components"]["graph_builder"] = "failed"
            validation_results["errors"].append(f"Graph creation failed: {str(e)}")
        
        # Test executor initialization
        try:
            executor = PlanningGraphExecutor()
            executor.initialize_graph()
            validation_results["components"]["executor"] = "ok"
        except Exception as e:
            validation_results["components"]["executor"] = "failed"
            validation_results["errors"].append(f"Executor initialization failed: {str(e)}")
        
        # Test state creation
        try:
            from .factory import create_new_experiment_state
            state = create_new_experiment_state("test query")
            validation_results["components"]["state_factory"] = "ok"
        except Exception as e:
            validation_results["components"]["state_factory"] = "failed"
            validation_results["errors"].append(f"State creation failed: {str(e)}")
        
        # Test agent imports
        try:
            from .agents import (
                ObjectiveAgent, VariableAgent, DesignAgent,
                MethodologyAgent, DataAgent, ReviewAgent
            )
            validation_results["components"]["agents"] = "ok"
        except Exception as e:
            validation_results["components"]["agents"] = "failed"
            validation_results["errors"].append(f"Agent imports failed: {str(e)}")
        
        # Test tools
        try:
            from .tools import TavilySearchTool, StatisticalCalculator
            validation_results["components"]["tools"] = "ok"
        except Exception as e:
            validation_results["components"]["tools"] = "failed"
            validation_results["errors"].append(f"Tools import failed: {str(e)}")
        
        # Determine overall status
        if validation_results["errors"]:
            validation_results["system_status"] = "unhealthy"
        elif validation_results["warnings"]:
            validation_results["system_status"] = "warning"
        
        return validation_results
        
    except Exception as e:
        logger.error(f"System validation failed: {str(e)}")
        return {
            "system_status": "critical",
            "error": str(e),
            "components": {},
            "errors": [f"Validation process failed: {str(e)}"],
            "warnings": []
        }


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
    
    # HITL-specific functions
    "check_user_approval",
    
    # State and configuration
    "ExperimentPlanState",
    "PLANNING_STAGES",
    "StateDebugger",
    "get_global_debugger"
] 