"""
Main LangGraph orchestration for the experiment planning agent system.

This module creates and manages the StateGraph that orchestrates all individual
planning agents into a cohesive conversational flow, implementing the sequential
processing with conditional routing and loop-back capabilities as defined in the PRD.
"""

from typing import Dict, Any, List, Optional, Literal
import logging
import traceback
from contextlib import contextmanager
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

from .state import ExperimentPlanState, PLANNING_STAGES
from .agents import (
    ObjectiveAgent,
    VariableAgent, 
    DesignAgent,
    MethodologyAgent,
    DataAgent,
    ReviewAgent
)
from .validation import validate_experiment_plan_state, StateValidationError
from .transitions import (
    transition_to_stage,
    check_stage_completion,
    get_available_transitions,
    TransitionError
)
from .debug import StateDebugger, get_global_debugger
from .factory import add_chat_message, update_state_timestamp, add_error

logger = logging.getLogger(__name__)


@contextmanager
def error_recovery_context(node_name: str, state: ExperimentPlanState):
    """
    Context manager for comprehensive error handling and recovery in LangGraph nodes.
    
    Args:
        node_name: Name of the node being executed
        state: Current experiment plan state
        
    Yields:
        None
        
    Handles:
        - All exceptions during node execution
        - State validation errors
        - Transition errors
        - Agent execution failures
    """
    try:
        logger.info(f"Starting {node_name} execution")
        yield
        logger.info(f"Successfully completed {node_name} execution")
        
    except StateValidationError as e:
        logger.error(f"State validation error in {node_name}: {e}")
        error_message = f"State validation failed in {node_name}: {e.message}"
        add_error(state, error_message)
        add_chat_message(state, "system", f"I encountered a validation issue: {e.message}. Let me try to recover...")
        
    except TransitionError as e:
        logger.error(f"State transition error in {node_name}: {e}")
        error_message = f"State transition failed in {node_name}: {str(e)}"
        add_error(state, error_message)
        add_chat_message(state, "system", f"I had trouble transitioning between stages: {str(e)}. Let me continue with the current stage...")
        
    except Exception as e:
        logger.error(f"Unexpected error in {node_name}: {str(e)}\n{traceback.format_exc()}")
        error_message = f"Unexpected error in {node_name}: {str(e)}"
        add_error(state, error_message)
        add_chat_message(state, "system", f"I encountered an unexpected issue in {node_name}. Let me try to recover and continue...")
        
        # Save debug snapshot for error analysis
        debugger = get_global_debugger()
        if debugger:
            debugger.save_debug_snapshot(
                state, 
                f"{node_name}_error",
                {"error": str(e), "traceback": traceback.format_exc()}
            )


def safe_agent_execution(agent_class, node_name: str, stage: str, state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Safely execute an agent with comprehensive error handling and recovery.
    
    Args:
        agent_class: The agent class to instantiate
        node_name: Name of the node for logging
        stage: The planning stage for this agent
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with results or error recovery
    """
    debugger = get_global_debugger()
    
    try:
        # Pre-execution state validation
        validate_experiment_plan_state(state)
        
        # Initialize and execute the agent
        agent = agent_class(debugger=debugger)
        user_input = _get_latest_user_input(state)
        
        # Execute the agent with error handling
        updated_state = agent.execute(state, user_input)
        
        # Post-execution validation
        validate_experiment_plan_state(updated_state)
        
        # Transition to the appropriate stage (if not already set)
        if updated_state.get('current_stage') != stage:
            updated_state = transition_to_stage(updated_state, stage)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        logger.info(f"Safe execution of {node_name} completed successfully")
        return updated_state
        
    except Exception as e:
        logger.error(f"Agent execution failed in {node_name}: {str(e)}")
        
        # Create recovery state
        recovery_state = state.copy() if hasattr(state, 'copy') else dict(state)
        
        # Add error information
        error_message = f"Agent execution failed in {node_name}: {str(e)}"
        recovery_state = add_error(recovery_state, error_message)
        
        # Add user-friendly message
        user_message = f"I encountered an issue while processing the {stage.replace('_', ' ')} stage. Please provide more information or try rephrasing your input."
        recovery_state = add_chat_message(recovery_state, "assistant", user_message)
        
        # Ensure we're in a valid state
        try:
            recovery_state = update_state_timestamp(recovery_state)
            validate_experiment_plan_state(recovery_state)
        except Exception as validation_error:
            logger.error(f"Recovery state validation failed: {validation_error}")
            # Fallback to original state with minimal changes
            recovery_state = state
            recovery_state = add_error(recovery_state, f"Recovery failed in {node_name}")
        
        return recovery_state


def safe_conditional_check(check_function, state: ExperimentPlanState, check_name: str, fallback_result: str):
    """
    Safely execute a conditional check function with error handling.
    
    Args:
        check_function: The check function to execute
        state: Current experiment plan state
        check_name: Name of the check for logging
        fallback_result: Default result if check fails
        
    Returns:
        Check result or fallback result
    """
    try:
        result = check_function(state)
        logger.info(f"Conditional check {check_name} completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Conditional check {check_name} failed: {str(e)}")
        logger.info(f"Using fallback result for {check_name}: {fallback_result}")
        return fallback_result


def create_planning_graph(
    debugger: Optional[StateDebugger] = None,
    log_level: str = "INFO"
) -> StateGraph:
    """
    Create the main planning graph with all agents and routing logic.
    
    This function constructs the StateGraph that orchestrates the six specialized
    planning agents according to the conversational flow defined in the PRD.
    
    Args:
        debugger: Optional StateDebugger instance for logging
        log_level: Logging level for the graph
        
    Returns:
        Compiled StateGraph ready for execution
    """
    if debugger is None:
        debugger = get_global_debugger()
    
    logger.info("Creating planning graph with StateGraph")
    
    # Initialize the StateGraph with ExperimentPlanState
    graph = StateGraph(ExperimentPlanState)
    
    # Initialize all agents
    objective_agent = ObjectiveAgent(debugger=debugger, log_level=log_level)
    variable_agent = VariableAgent(debugger=debugger, log_level=log_level)
    design_agent = DesignAgent(debugger=debugger, log_level=log_level)
    methodology_agent = MethodologyAgent(debugger=debugger, log_level=log_level)
    data_agent = DataAgent(debugger=debugger, log_level=log_level)
    review_agent = ReviewAgent(debugger=debugger, log_level=log_level)
    
    # Add agent nodes to the graph
    graph.add_node("objective_agent", objective_agent_node)
    graph.add_node("variable_agent", variable_agent_node)
    graph.add_node("design_agent", design_agent_node)
    graph.add_node("methodology_agent", methodology_agent_node)
    graph.add_node("data_agent", data_agent_node)
    graph.add_node("review_agent", review_agent_node)
    
    # Add routing and decision nodes
    graph.add_node("router", router_node)
    
    # Set entry point
    graph.set_entry_point("objective_agent")
    
    # Add conditional edges for sequential flow with validation
    graph.add_conditional_edges(
        "objective_agent",
        objective_completion_check,
        {
            "continue": "variable_agent",
            "retry": "objective_agent"
        }
    )
    
    graph.add_conditional_edges(
        "variable_agent", 
        variable_completion_check,
        {
            "continue": "design_agent",
            "retry": "variable_agent"
        }
    )
    
    graph.add_conditional_edges(
        "design_agent",
        design_completion_check,
        {
            "continue": "methodology_agent",
            "retry": "design_agent"
        }
    )
    
    graph.add_conditional_edges(
        "methodology_agent",
        methodology_completion_check,
        {
            "continue": "data_agent",
            "retry": "methodology_agent"
        }
    )
    
    graph.add_conditional_edges(
        "data_agent",
        data_completion_check,
        {
            "continue": "review_agent",
            "retry": "data_agent"
        }
    )
    
    graph.add_conditional_edges(
        "review_agent",
        review_completion_check,
        {
            "complete": END,
            "edit_section": "router"
        }
    )
    
    # Router edges for loop-back functionality
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
    
    logger.info("Planning graph structure created successfully")
    
    # Compile the graph with error handling
    try:
        compiled_graph = graph.compile(
            checkpointer=None,  # Will add checkpointing later if needed
            debug=True if log_level == "DEBUG" else False
        )
        
        logger.info("Planning graph compiled successfully")
        return compiled_graph
        
    except Exception as e:
        logger.error(f"Graph compilation failed: {str(e)}\n{traceback.format_exc()}")
        raise RuntimeError(f"Failed to compile planning graph: {str(e)}") from e


# Agent node functions with comprehensive error handling
def objective_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """Execute the objective setting agent with comprehensive error handling."""
    with error_recovery_context("objective_agent", state):
        return safe_agent_execution(
            ObjectiveAgent, 
            "objective_agent", 
            "objective_setting", 
            state
        )


def variable_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """Execute the variable identification agent with comprehensive error handling."""
    with error_recovery_context("variable_agent", state):
        return safe_agent_execution(
            VariableAgent, 
            "variable_agent", 
            "variable_identification", 
            state
        )


def design_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """Execute the experimental design agent with comprehensive error handling."""
    with error_recovery_context("design_agent", state):
        return safe_agent_execution(
            DesignAgent, 
            "design_agent", 
            "experimental_design", 
            state
        )


def methodology_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """Execute the methodology and protocol agent with comprehensive error handling."""
    with error_recovery_context("methodology_agent", state):
        return safe_agent_execution(
            MethodologyAgent, 
            "methodology_agent", 
            "methodology_protocol", 
            state
        )


def data_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """Execute the data planning and QA agent with comprehensive error handling."""
    with error_recovery_context("data_agent", state):
        return safe_agent_execution(
            DataAgent, 
            "data_agent", 
            "data_planning", 
            state
        )


def review_agent_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """Execute the final review and export agent with comprehensive error handling."""
    with error_recovery_context("review_agent", state):
        return safe_agent_execution(
            ReviewAgent, 
            "review_agent", 
            "final_review", 
            state
        )


def router_node(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Router node for handling loop-back navigation to specific sections with error handling.
    
    This node processes user requests to edit specific sections of the plan
    and updates the state to navigate back to the appropriate agent.
    """
    with error_recovery_context("router", state):
        try:
            # Validate input state
            validate_experiment_plan_state(state)
            
            user_input = _get_latest_user_input(state)
            
            # Determine which section the user wants to edit with fallback
            section_to_edit = _determine_section_to_edit(user_input, state)
            
            # Validate the section choice
            if section_to_edit not in [stage for stage in PLANNING_STAGES]:
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


# Conditional routing functions with error handling
def objective_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """Check if objective setting is complete with error handling."""
    def _check_objective_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        # Check if objective and hypothesis are adequately defined
        objective = state.get('experiment_objective')
        hypothesis = state.get('hypothesis')
        
        if objective and hypothesis:
            logger.info("Objective completion check: PASS")
            return "continue"
        else:
            logger.info("Objective completion check: RETRY")
            return "retry"
    
    return safe_conditional_check(
        _check_objective_completion, 
        state, 
        "objective_completion", 
        "retry"  # Safe fallback to retry if check fails
    )


def variable_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """Check if variable identification is complete with error handling."""
    def _check_variable_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        if independent_vars and dependent_vars and control_vars:
            logger.info("Variable completion check: PASS")
            return "continue"
        else:
            logger.info("Variable completion check: RETRY")
            return "retry"
    
    return safe_conditional_check(
        _check_variable_completion, 
        state, 
        "variable_completion", 
        "retry"
    )


def design_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """Check if experimental design is complete with error handling."""
    def _check_design_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        if experimental_groups and control_groups and sample_size:
            logger.info("Design completion check: PASS")
            return "continue"
        else:
            logger.info("Design completion check: RETRY")
            return "retry"
    
    return safe_conditional_check(
        _check_design_completion, 
        state, 
        "design_completion", 
        "retry"
    )


def methodology_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """Check if methodology and protocol development is complete with error handling."""
    def _check_methodology_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        if methodology_steps and materials_equipment:
            logger.info("Methodology completion check: PASS")
            return "continue"
        else:
            logger.info("Methodology completion check: RETRY")
            return "retry"
    
    return safe_conditional_check(
        _check_methodology_completion, 
        state, 
        "methodology_completion", 
        "retry"
    )


def data_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """Check if data planning is complete with error handling."""
    def _check_data_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        data_collection_plan = state.get('data_collection_plan', {})
        data_analysis_plan = state.get('data_analysis_plan', {})
        
        if data_collection_plan and data_analysis_plan:
            logger.info("Data planning completion check: PASS")
            return "continue"
        else:
            logger.info("Data planning completion check: RETRY")
            return "retry"
    
    return safe_conditional_check(
        _check_data_completion, 
        state, 
        "data_completion", 
        "retry"
    )


def review_completion_check(state: ExperimentPlanState) -> Literal["complete", "edit_section"]:
    """Check if final review is complete and user approves with error handling."""
    def _check_review_completion(state: ExperimentPlanState) -> Literal["complete", "edit_section"]:
        user_input = _get_latest_user_input(state)
        
        # Check for approval keywords
        approval_keywords = ["approve", "approved", "yes", "confirm", "complete", "finalize"]
        edit_keywords = ["edit", "modify", "change", "update", "revise", "go back"]
        
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in approval_keywords):
            logger.info("Review completion check: COMPLETE")
            return "complete"
        elif any(keyword in user_input_lower for keyword in edit_keywords):
            logger.info("Review completion check: EDIT_SECTION")
            return "edit_section"
        else:
            # Default to edit_section if unclear
            logger.info("Review completion check: EDIT_SECTION (default)")
            return "edit_section"
    
    return safe_conditional_check(
        _check_review_completion, 
        state, 
        "review_completion", 
        "edit_section"  # Safe fallback to edit_section
    )


def route_to_section(state: ExperimentPlanState) -> str:
    """
    Determine which section to route to based on user input with error handling.
    
    This function analyzes the user's request and determines which
    planning stage they want to edit.
    """
    def _determine_route_section(state: ExperimentPlanState) -> str:
        user_input = _get_latest_user_input(state)
        section = _determine_section_to_edit(user_input, state)
        
        # Map stages to routing keys
        stage_routing_map = {
            "objective_setting": "objective",
            "variable_identification": "variables",
            "experimental_design": "design", 
            "methodology_protocol": "methodology",
            "data_planning": "data_planning",
            "final_review": "review"
        }
        
        routing_key = stage_routing_map.get(section, "objective")
        logger.info(f"Routing to section: {routing_key}")
        
        return routing_key
    
    return safe_conditional_check(
        _determine_route_section, 
        state, 
        "route_to_section", 
        "objective"  # Safe fallback to objective
    )


# Helper functions
def _get_latest_user_input(state: ExperimentPlanState) -> str:
    """Extract the latest user input from chat history."""
    chat_history = state.get('chat_history', [])
    
    # Find the most recent user message
    for message in reversed(chat_history):
        if message.get('role') == 'user':
            return message.get('content', '')
    
    return ''


def _determine_section_to_edit(user_input: str, state: ExperimentPlanState) -> str:
    """
    Determine which section the user wants to edit based on their input.
    
    This is a simplified implementation using keyword matching.
    In a production system, this would use more sophisticated NLP.
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
            return section
    
    # Default to objective setting if no specific section is identified
    return "objective_setting"


# ==================== GRAPH EXECUTION LOGIC ====================

class PlanningGraphExecutor:
    """
    Comprehensive execution manager for the planning graph.
    
    This class provides high-level execution utilities, session management,
    and monitoring capabilities for the planning graph.
    """
    
    def __init__(self, debugger: Optional[StateDebugger] = None, log_level: str = "INFO"):
        """
        Initialize the graph executor.
        
        Args:
            debugger: Optional StateDebugger instance
            log_level: Logging level for execution
        """
        self.debugger = debugger or get_global_debugger()
        self.log_level = log_level
        self.graph = None
        self.logger = logging.getLogger(f"planning.executor")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
    def initialize_graph(self) -> None:
        """Initialize and compile the planning graph."""
        try:
            self.graph = create_planning_graph(
                debugger=self.debugger,
                log_level=self.log_level
            )
            self.logger.info("Planning graph initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize planning graph: {str(e)}")
            raise RuntimeError(f"Graph initialization failed: {str(e)}") from e
    
    def create_initial_state(self, research_query: str, experiment_id: Optional[str] = None) -> ExperimentPlanState:
        """
        Create an initial state for a new experiment planning session.
        
        Args:
            research_query: User's initial research question
            experiment_id: Optional experiment ID (auto-generated if not provided)
            
        Returns:
            Initialized ExperimentPlanState
        """
        try:
            from .factory import create_new_experiment_state
            
            # Create new state
            state = create_new_experiment_state(research_query)
            
            # Add initial user message
            state = add_chat_message(state, "user", research_query)
            
            # Add welcome message
            welcome_message = (
                "Hello! I'm your experiment planning assistant. I'll help you develop a comprehensive "
                "experiment plan from your research idea. Let's start by clarifying your research objective."
            )
            state = add_chat_message(state, "assistant", welcome_message)
            
            self.logger.info(f"Created initial state for experiment: {state['experiment_id']}")
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to create initial state: {str(e)}")
            raise RuntimeError(f"State creation failed: {str(e)}") from e
    
    def execute_step(self, state: ExperimentPlanState, user_input: Optional[str] = None) -> ExperimentPlanState:
        """
        Execute a single step in the planning graph.
        
        Args:
            state: Current experiment plan state
            user_input: Optional user input for this step
            
        Returns:
            Updated ExperimentPlanState after execution
        """
        if not self.graph:
            raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
        
        try:
            # Add user input to state if provided
            if user_input and user_input.strip():
                state = add_chat_message(state, "user", user_input)
                self.logger.info(f"Added user input to state: {user_input[:100]}...")
            
            # Execute one step of the graph
            result = self.graph.invoke(state)
            
            self.logger.info(f"Graph step executed successfully for experiment: {result.get('experiment_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Graph execution step failed: {str(e)}")
            
            # Create error recovery state
            error_state = state.copy() if hasattr(state, 'copy') else dict(state)
            error_state = add_error(error_state, f"Execution step failed: {str(e)}")
            error_state = add_chat_message(
                error_state, 
                "system", 
                "I encountered an issue during execution. Let me try to recover..."
            )
            error_state = update_state_timestamp(error_state)
            
            return error_state
    
    def execute_until_completion(
        self, 
        state: ExperimentPlanState, 
        max_steps: int = 50,
        step_callback: Optional[callable] = None
    ) -> ExperimentPlanState:
        """
        Execute the graph until completion or max steps reached.
        
        Args:
            state: Starting experiment plan state
            max_steps: Maximum number of execution steps
            step_callback: Optional callback function called after each step
            
        Returns:
            Final ExperimentPlanState
        """
        if not self.graph:
            raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
        
        current_state = state
        step_count = 0
        
        try:
            self.logger.info(f"Starting graph execution for experiment: {state.get('experiment_id')}")
            
            while step_count < max_steps:
                # Check if we've reached a terminal state
                if self._is_terminal_state(current_state):
                    self.logger.info(f"Reached terminal state after {step_count} steps")
                    break
                
                # Execute one step
                previous_state = current_state
                current_state = self.execute_step(current_state)
                
                step_count += 1
                
                # Call step callback if provided
                if step_callback:
                    try:
                        step_callback(current_state, step_count)
                    except Exception as callback_error:
                        self.logger.warning(f"Step callback failed: {callback_error}")
                
                # Check if state hasn't changed (potential infinite loop)
                if self._states_equivalent(previous_state, current_state):
                    self.logger.warning(f"State unchanged after step {step_count}, may be stuck")
                    break
            
            if step_count >= max_steps:
                self.logger.warning(f"Execution stopped at max steps ({max_steps})")
                current_state = add_chat_message(
                    current_state,
                    "system", 
                    "I've reached the maximum number of processing steps. Let me know if you'd like to continue."
                )
            
            self.logger.info(f"Graph execution completed after {step_count} steps")
            return current_state
            
        except Exception as e:
            self.logger.error(f"Graph execution failed: {str(e)}")
            return add_error(current_state, f"Execution failed: {str(e)}")
    
    def get_execution_status(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get detailed execution status and progress information.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Status information dictionary
        """
        try:
            current_stage = state.get('current_stage', 'unknown')
            completed_stages = state.get('completed_stages', [])
            errors = state.get('errors', [])
            
            # Calculate progress
            total_stages = len(PLANNING_STAGES)
            completed_count = len(completed_stages)
            progress_percentage = (completed_count / total_stages) * 100 if total_stages > 0 else 0
            
            # Determine next stage
            current_stage_index = PLANNING_STAGES.index(current_stage) if current_stage in PLANNING_STAGES else -1
            next_stage = None
            if 0 <= current_stage_index < len(PLANNING_STAGES) - 1:
                next_stage = PLANNING_STAGES[current_stage_index + 1]
            
            status = {
                "experiment_id": state.get('experiment_id'),
                "current_stage": current_stage,
                "completed_stages": completed_stages,
                "next_stage": next_stage,
                "progress": {
                    "completed_count": completed_count,
                    "total_stages": total_stages,
                    "percentage": progress_percentage,
                    "is_complete": progress_percentage >= 100
                },
                "errors": errors,
                "has_errors": len(errors) > 0,
                "last_updated": state.get('updated_at'),
                "created_at": state.get('created_at'),
                "chat_message_count": len(state.get('chat_history', []))
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get execution status: {str(e)}")
            return {
                "error": str(e),
                "experiment_id": state.get('experiment_id', 'unknown')
            }
    
    def _is_terminal_state(self, state: ExperimentPlanState) -> bool:
        """Check if the state represents a terminal (completed) state."""
        try:
            # Check if all stages are completed
            completed_stages = state.get('completed_stages', [])
            if len(completed_stages) >= len(PLANNING_STAGES):
                return True
            
            # Check if we're in final review and approved
            current_stage = state.get('current_stage', '')
            if current_stage == 'final_review':
                # Look for approval in recent chat messages
                chat_history = state.get('chat_history', [])
                recent_messages = chat_history[-5:] if len(chat_history) >= 5 else chat_history
                
                for message in reversed(recent_messages):
                    if message.get('role') == 'user':
                        content = message.get('content', '').lower()
                        approval_keywords = ["approve", "approved", "yes", "confirm", "complete", "finalize"]
                        if any(keyword in content for keyword in approval_keywords):
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking terminal state: {str(e)}")
            return False
    
    def _states_equivalent(self, state1: ExperimentPlanState, state2: ExperimentPlanState) -> bool:
        """Check if two states are equivalent (for loop detection)."""
        try:
            # Compare key fields that should change between steps
            comparison_fields = ['current_stage', 'completed_stages', 'chat_history', 'errors']
            
            for field in comparison_fields:
                if state1.get(field) != state2.get(field):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error comparing states: {str(e)}")
            return False


# ==================== CONVENIENCE FUNCTIONS ====================

def start_new_experiment_planning(
    research_query: str, 
    experiment_id: Optional[str] = None,
    debugger: Optional[StateDebugger] = None,
    log_level: str = "INFO"
) -> tuple[PlanningGraphExecutor, ExperimentPlanState]:
    """
    Convenience function to start a new experiment planning session.
    
    Args:
        research_query: User's initial research question
        experiment_id: Optional experiment ID
        debugger: Optional StateDebugger instance
        log_level: Logging level
        
    Returns:
        Tuple of (executor, initial_state)
    """
    executor = PlanningGraphExecutor(debugger=debugger, log_level=log_level)
    executor.initialize_graph()
    initial_state = executor.create_initial_state(research_query, experiment_id)
    
    return executor, initial_state


def execute_planning_conversation(
    research_query: str,
    user_inputs: List[str],
    experiment_id: Optional[str] = None,
    debugger: Optional[StateDebugger] = None,
    log_level: str = "INFO"
) -> ExperimentPlanState:
    """
    Execute a complete planning conversation with predefined user inputs.
    
    Args:
        research_query: Initial research question
        user_inputs: List of user inputs for the conversation
        experiment_id: Optional experiment ID
        debugger: Optional StateDebugger instance
        log_level: Logging level
        
    Returns:
        Final ExperimentPlanState
    """
    executor, state = start_new_experiment_planning(
        research_query, experiment_id, debugger, log_level
    )
    
    # Execute initial step
    state = executor.execute_step(state)
    
    # Process each user input
    for user_input in user_inputs:
        if user_input.strip():
            state = executor.execute_step(state, user_input)
    
    return state


def get_planning_graph_info() -> Dict[str, Any]:
    """
    Get information about the planning graph structure.
    
    Returns:
        Graph information dictionary
    """
    return {
        "graph_type": "LangGraph StateGraph",
        "state_type": "ExperimentPlanState",
        "planning_stages": PLANNING_STAGES,
        "agent_count": 6,
        "agents": [
            "ObjectiveAgent",
            "VariableAgent", 
            "DesignAgent",
            "MethodologyAgent",
            "DataAgent",
            "ReviewAgent"
        ],
        "features": [
            "Sequential processing with validation",
            "Conditional routing based on completion",
            "Loop-back functionality for editing",
            "Comprehensive error handling",
            "State management and persistence",
            "Router-based navigation",
            "Debug and monitoring capabilities"
        ],
        "entry_point": "objective_agent",
        "terminal_conditions": [
            "All stages completed",
            "User approval in final review"
        ]
    } 