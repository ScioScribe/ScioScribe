"""
Base agent class for the experiment planning system.

This module provides the foundational BaseAgent class that all specialized
planning agents inherit from, ensuring consistent behavior, logging, and
state management across the entire multi-agent system.
"""

from typing import Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod
from datetime import datetime
import logging

from ..state import ExperimentPlanState, PLANNING_STAGES
from ..validation import StateValidationError, validate_experiment_plan_state
from ..factory import update_state_timestamp, add_chat_message, add_error
from ..debug import StateDebugger, performance_monitor, log_agent_interaction
from ..serialization import serialize_state_to_dict, deserialize_state_from_dict


class BaseAgent(ABC):
    """
    Base class for all experiment planning agents.
    
    Provides common functionality for state management, logging, validation,
    and user interaction that all specialized agents can inherit and extend.
    """
    
    def __init__(
        self,
        agent_name: str,
        stage: str,
        debugger: Optional[StateDebugger] = None,
        log_level: str = "INFO"
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_name: Unique name for this agent
            stage: The planning stage this agent handles
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        self.agent_name = agent_name
        self.stage = stage
        self.debugger = debugger or StateDebugger(log_level)
        
        # Set up logging
        self.logger = logging.getLogger(f"agents.planning.{agent_name}")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Validate stage
        if stage not in PLANNING_STAGES:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of: {PLANNING_STAGES}")
        
        self.logger.info(f"Initialized {agent_name} for stage: {stage}")
    
    @abstractmethod
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state and return updated state.
        
        This is the main method that each agent must implement to handle
        their specific planning stage responsibilities.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState
            
        Raises:
            StateValidationError: If state validation fails
        """
        pass
    
    @abstractmethod
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions for the user based on current state.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of questions to ask the user
        """
        pass
    
    @abstractmethod
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the state meets this agent's stage requirements.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        pass
    
    def execute(self, state: ExperimentPlanState, user_input: str = "") -> ExperimentPlanState:
        """
        Main execution method with comprehensive logging and error handling.
        
        Args:
            state: Current experiment plan state
            user_input: Optional user input/feedback
            
        Returns:
            Updated ExperimentPlanState
            
        Raises:
            StateValidationError: If state validation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate input state
            self._validate_input_state(state)
            
            # Log user input if provided
            if user_input.strip():
                state = add_chat_message(state, "user", user_input)
                self.logger.info(f"User input received: {user_input[:100]}...")
            
            # Process state with performance monitoring
            with performance_monitor(f"{self.agent_name}_process", self.debugger):
                updated_state = self.process_state(state)
            
            # Validate output state
            self._validate_output_state(updated_state)
            
            # Log successful execution
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._log_execution_success(state, updated_state, duration)
            
            return updated_state
            
        except StateValidationError as e:
            self.logger.error(f"State validation error in {self.agent_name}: {e}")
            state = add_error(state, f"{self.agent_name} validation error: {e}")
            return state
            
        except Exception as e:
            self.logger.error(f"Unexpected error in {self.agent_name}: {e}")
            state = add_error(state, f"{self.agent_name} execution error: {e}")
            return state
    
    def can_process_stage(self, state: ExperimentPlanState) -> bool:
        """
        Check if this agent can process the current stage.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            bool: True if agent can process current stage
        """
        return state.get("current_stage") == self.stage
    
    def get_stage_progress(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get progress information for this agent's stage.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Progress information dictionary
        """
        is_valid, missing_requirements = self.validate_stage_requirements(state)
        
        return {
            "stage": self.stage,
            "agent": self.agent_name,
            "is_complete": is_valid,
            "missing_requirements": missing_requirements,
            "completion_percentage": self._calculate_completion_percentage(state),
            "can_advance": is_valid and len(missing_requirements) == 0
        }
    
    def generate_response(self, state: ExperimentPlanState, user_input: str = "") -> str:
        """
        Generate a conversational response for the user.
        
        Args:
            state: Current experiment plan state
            user_input: User's input/feedback
            
        Returns:
            Agent's response message
        """
        try:
            # Check if stage is complete
            is_complete, missing_requirements = self.validate_stage_requirements(state)
            
            if is_complete:
                return self._generate_completion_response(state)
            
            # Generate questions if stage is not complete
            questions = self.generate_questions(state)
            
            if missing_requirements:
                return self._generate_requirements_response(missing_requirements, questions)
            
            return self._generate_standard_response(state, questions)
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return f"I encountered an error while processing your request. Please try again."
    
    def _validate_input_state(self, state: ExperimentPlanState) -> None:
        """Validate the input state structure."""
        if not isinstance(state, dict):
            raise StateValidationError("State must be a dictionary")
        
        validate_experiment_plan_state(state)
        
        # Log state validation
        self.debugger.log_state_change(
            state,
            f"{self.agent_name}_input_validation",
            {"stage": self.stage, "valid": True}
        )
    
    def _validate_output_state(self, state: ExperimentPlanState) -> None:
        """Validate the output state structure."""
        validate_experiment_plan_state(state)
        
        # Ensure state timestamp is updated
        if state.get("updated_at") is None:
            state = update_state_timestamp(state)
        
        # Log state validation
        self.debugger.log_state_change(
            state,
            f"{self.agent_name}_output_validation",
            {"stage": self.stage, "valid": True}
        )
    
    def _log_execution_success(
        self,
        input_state: ExperimentPlanState,
        output_state: ExperimentPlanState,
        duration: float
    ) -> None:
        """Log successful agent execution."""
        log_agent_interaction(
            self.agent_name,
            output_state,
            {"current_stage": input_state.get("current_stage")},
            {"updated_stage": output_state.get("current_stage")},
            duration,
            self.debugger
        )
    
    def _calculate_completion_percentage(self, state: ExperimentPlanState) -> float:
        """Calculate completion percentage for this agent's stage."""
        is_valid, missing_requirements = self.validate_stage_requirements(state)
        
        if is_valid:
            return 100.0
        
        # Calculate based on missing requirements
        if not missing_requirements:
            return 100.0
        
        # Estimate based on fields - this is a simple heuristic
        stage_fields = self._get_stage_fields()
        if not stage_fields:
            return 0.0
        
        completed_fields = len(stage_fields) - len(missing_requirements)
        return (completed_fields / len(stage_fields)) * 100.0
    
    def _get_stage_fields(self) -> List[str]:
        """Get the fields relevant to this agent's stage."""
        stage_fields = {
            "objective_setting": ["experiment_objective", "hypothesis"],
            "variable_identification": ["independent_variables", "dependent_variables", "control_variables"],
            "experimental_design": ["experimental_groups", "control_groups", "sample_size"],
            "methodology_protocol": ["methodology_steps", "materials_equipment"],
            "data_planning": ["data_collection_plan", "data_analysis_plan", "potential_pitfalls"],
            "final_review": ["expected_outcomes", "ethical_considerations", "timeline"]
        }
        return stage_fields.get(self.stage, [])
    
    def _generate_completion_response(self, state: ExperimentPlanState) -> str:
        """Generate response when stage is complete."""
        return f"Great! I've completed the {self.stage.replace('_', ' ')} stage. We can now move to the next part of your experiment plan."
    
    def _generate_requirements_response(self, missing_requirements: List[str], questions: List[str]) -> str:
        """Generate response highlighting missing requirements."""
        response = f"To complete the {self.stage.replace('_', ' ')} stage, I need more information:\n\n"
        
        for i, requirement in enumerate(missing_requirements[:3], 1):  # Limit to top 3
            response += f"{i}. {requirement}\n"
        
        if questions:
            response += f"\nLet me ask you: {questions[0]}"
        
        return response
    
    def _generate_standard_response(self, state: ExperimentPlanState, questions: List[str]) -> str:
        """Generate standard conversational response."""
        if questions:
            return f"I'm working on the {self.stage.replace('_', ' ')} stage. {questions[0]}"
        
        return f"I'm ready to help with the {self.stage.replace('_', ' ')} stage. Please provide more details about your experiment."
    
    def get_debug_info(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """Get debug information for this agent."""
        return {
            "agent_name": self.agent_name,
            "stage": self.stage,
            "can_process": self.can_process_stage(state),
            "progress": self.get_stage_progress(state),
            "state_summary": self.debugger.get_state_summary(state)
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_name='{self.agent_name}', stage='{self.stage}')" 