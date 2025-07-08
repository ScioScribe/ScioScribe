"""
Variable Identification Agent for the experiment planning system.

This agent specializes in helping researchers identify and define experimental variables,
including independent variables (manipulated factors), dependent variables (measured outcomes),
and control variables (factors held constant) with appropriate measurement methods.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json

from .base_agent import BaseAgent
from ..state import ExperimentPlanState, VARIABLE_REQUIRED_FIELDS
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.variable_prompts import (
    VARIABLE_SYSTEM_PROMPT,
    INDEPENDENT_VARIABLE_QUESTIONS,
    DEPENDENT_VARIABLE_QUESTIONS,
    CONTROL_VARIABLE_QUESTIONS,
    VARIABLE_RESPONSE_TEMPLATES,
    VARIABLE_VALIDATION_CRITERIA,
    VARIABLE_TYPES,
    get_variable_domain_guidance,
    format_variable_response,
    validate_variable_set,
    suggest_measurement_methods,
    get_variable_examples
)


class VariableAgent(BaseAgent):
    """
    Agent responsible for identifying and defining experimental variables.
    
    This agent guides users through the systematic identification of:
    - Independent variables (factors being manipulated)
    - Dependent variables (outcomes being measured)
    - Control variables (factors held constant)
    
    It provides domain-specific guidance and ensures variables are properly defined
    with appropriate measurement methods.
    """
    
    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Variable Identification Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        super().__init__(
            agent_name="variable_agent",
            stage="variable_identification",
            debugger=debugger,
            log_level=log_level
        )
        
        self.logger.info("VariableAgent initialized for variable identification stage")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to identify and define experimental variables.
        
        Analyzes the current state and user input to systematically identify
        independent, dependent, and control variables with measurement methods.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with defined variables
        """
        self.logger.info(f"Processing variable identification for experiment: {state.get('experiment_id')}")
        
        # Get the latest user input from chat history
        user_input = self._get_latest_user_input(state)
        
        # Get current variables
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        # Validate current variable set
        validation_results = validate_variable_set(independent_vars, dependent_vars, control_vars)
        
        # Determine what variables are needed based on current state
        next_action = self._determine_next_action(state, validation_results)
        
        # Process user input based on current needs
        if next_action == "independent":
            updated_state = self._process_independent_variables(state, user_input)
        elif next_action == "dependent":
            updated_state = self._process_dependent_variables(state, user_input)
        elif next_action == "control":
            updated_state = self._process_control_variables(state, user_input)
        elif next_action == "refinement":
            updated_state = self._refine_variables(state, user_input)
        else:
            updated_state = self._finalize_variables(state, user_input)
        
        # Generate agent response
        response = self._generate_variable_response(updated_state, next_action)
        updated_state = add_chat_message(updated_state, "assistant", response)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        self.logger.info(f"Variable identification processing complete. Next action: {next_action}")
        
        return updated_state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions based on current variable identification needs.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of relevant questions for the user
        """
        # Get domain guidance
        research_query = state.get('research_query', '')
        objective = state.get('experiment_objective', '')
        domain_guidance = get_variable_domain_guidance(research_query, objective)
        
        # Get current variables
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        # Determine what questions to ask
        if not independent_vars:
            return domain_guidance['suggested_questions'].get('independent', INDEPENDENT_VARIABLE_QUESTIONS[:3])
        elif not dependent_vars:
            return domain_guidance['suggested_questions'].get('dependent', DEPENDENT_VARIABLE_QUESTIONS[:3])
        elif not control_vars:
            return domain_guidance['suggested_questions'].get('control', CONTROL_VARIABLE_QUESTIONS[:3])
        else:
            # Refinement questions
            return [
                "Are all your variables clearly defined with measurement methods?",
                "Do you need to add any additional variables?",
                "Are there any confounding variables we should control for?"
            ]
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the variable identification stage requirements are met.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Get current variables
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        # Validate using the variable validation function
        validation_results = validate_variable_set(independent_vars, dependent_vars, control_vars)
        
        if not validation_results['is_complete']:
            missing_requirements.extend(validation_results['missing_elements'])
            missing_requirements.extend(validation_results['suggestions'])
        
        # Detailed validation of each variable type
        if not independent_vars:
            missing_requirements.append("At least one independent variable")
        else:
            for i, var in enumerate(independent_vars):
                if not self._validate_variable_fields(var, 'independent'):
                    missing_requirements.append(f"Complete definition for independent variable {i+1}")
        
        if not dependent_vars:
            missing_requirements.append("At least one dependent variable")
        else:
            for i, var in enumerate(dependent_vars):
                if not self._validate_variable_fields(var, 'dependent'):
                    missing_requirements.append(f"Complete definition for dependent variable {i+1}")
        
        if not control_vars:
            missing_requirements.append("At least one control variable")
        else:
            for i, var in enumerate(control_vars):
                if not self._validate_variable_fields(var, 'control'):
                    missing_requirements.append(f"Complete definition for control variable {i+1}")
        
        is_valid = len(missing_requirements) == 0 and validation_results['score'] >= 80
        
        return is_valid, missing_requirements
    
    def _get_latest_user_input(self, state: ExperimentPlanState) -> str:
        """Extract the latest user input from chat history."""
        chat_history = state.get('chat_history', [])
        
        # Find the most recent user message
        for message in reversed(chat_history):
            if message.get('role') == 'user':
                return message.get('content', '')
        
        return ''
    
    def _determine_next_action(self, state: ExperimentPlanState, validation_results: Dict[str, Any]) -> str:
        """Determine what action to take next based on current state."""
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        if not independent_vars:
            return "independent"
        elif not dependent_vars:
            return "dependent"
        elif not control_vars:
            return "control"
        elif validation_results['score'] < 80:
            return "refinement"
        else:
            return "finalize"
    
    def _process_independent_variables(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Process user input to identify independent variables."""
        if not user_input:
            return state
        
        # Extract variable information from user input
        variable_info = self._extract_variable_info(user_input, "independent")
        
        if variable_info:
            # Add to existing independent variables
            independent_vars = state.get('independent_variables', [])
            independent_vars.append(variable_info)
            state['independent_variables'] = independent_vars
            
            self.logger.info(f"Added independent variable: {variable_info.get('name', 'unnamed')}")
        
        return state
    
    def _process_dependent_variables(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Process user input to identify dependent variables."""
        if not user_input:
            return state
        
        # Extract variable information from user input
        variable_info = self._extract_variable_info(user_input, "dependent")
        
        if variable_info:
            # Add to existing dependent variables
            dependent_vars = state.get('dependent_variables', [])
            dependent_vars.append(variable_info)
            state['dependent_variables'] = dependent_vars
            
            self.logger.info(f"Added dependent variable: {variable_info.get('name', 'unnamed')}")
        
        return state
    
    def _process_control_variables(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Process user input to identify control variables."""
        if not user_input:
            return state
        
        # Extract variable information from user input
        variable_info = self._extract_variable_info(user_input, "control")
        
        if variable_info:
            # Add to existing control variables
            control_vars = state.get('control_variables', [])
            control_vars.append(variable_info)
            state['control_variables'] = control_vars
            
            self.logger.info(f"Added control variable: {variable_info.get('name', 'unnamed')}")
        
        return state
    
    def _refine_variables(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Refine existing variables based on user input."""
        if not user_input:
            return state
        
        # Simple refinement - in a real implementation, this would use NLP
        # to understand what the user wants to modify
        input_lower = user_input.lower()
        
        if "independent" in input_lower:
            # User wants to modify independent variables
            # This is a simplified implementation - would need more sophisticated parsing
            pass
        elif "dependent" in input_lower:
            # User wants to modify dependent variables
            pass
        elif "control" in input_lower:
            # User wants to modify control variables
            pass
        
        return state
    
    def _finalize_variables(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Finalize variables and prepare for next stage."""
        # Any final processing or validation
        return state
    
    def _extract_variable_info(self, user_input: str, variable_type: str) -> Optional[Dict[str, Any]]:
        """
        Extract variable information from user input.
        
        This is a simplified implementation. In a real system, this would use
        NLP to parse the user input and extract structured variable information.
        """
        if not user_input:
            return None
        
        # Basic extraction - in reality, this would be much more sophisticated
        variable_info = {
            "name": user_input.strip(),
            "type": self._infer_variable_type(user_input),
            "description": user_input.strip()
        }
        
        # Add required fields based on variable type
        if variable_type == "independent":
            variable_info.update({
                "units": "",  # Would be extracted from input
                "levels": []  # Would be extracted from input
            })
        elif variable_type == "dependent":
            variable_info.update({
                "units": "",  # Would be extracted from input
                "measurement_method": ""  # Would be extracted from input
            })
        elif variable_type == "control":
            variable_info.update({
                "reason": "",  # Would be extracted from input
                "control_method": ""  # Would be extracted from input
            })
        
        return variable_info
    
    def _infer_variable_type(self, user_input: str) -> str:
        """Infer the data type of a variable from user input."""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["concentration", "dose", "amount", "level"]):
            return "continuous"
        elif any(word in input_lower for word in ["type", "strain", "condition", "group"]):
            return "categorical"
        elif any(word in input_lower for word in ["positive", "negative", "present", "absent"]):
            return "binary"
        else:
            return "continuous"  # Default
    
    def _validate_variable_fields(self, variable: Dict[str, Any], variable_type: str) -> bool:
        """Validate that a variable has all required fields."""
        required_fields = VARIABLE_REQUIRED_FIELDS.get(variable_type, [])
        return all(field in variable and variable[field] for field in required_fields)
    
    def _generate_variable_response(self, state: ExperimentPlanState, next_action: str) -> str:
        """Generate appropriate response based on current state and next action."""
        research_query = state.get('research_query', '')
        objective = state.get('experiment_objective', '')
        domain_guidance = get_variable_domain_guidance(research_query, objective)
        
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        if next_action == "independent":
            if not independent_vars:
                # Need to start identifying independent variables
                questions = domain_guidance['suggested_questions'].get('independent', INDEPENDENT_VARIABLE_QUESTIONS[:1])
                return format_variable_response(
                    "independent_needed",
                    {"specific_question": questions[0] if questions else "What will you be manipulating in your experiment?"}
                )
            else:
                # Ask for more independent variables
                return "Great! Do you have any other independent variables you'll be manipulating?"
        
        elif next_action == "dependent":
            if not dependent_vars:
                # Need to start identifying dependent variables
                questions = domain_guidance['suggested_questions'].get('dependent', DEPENDENT_VARIABLE_QUESTIONS[:1])
                return format_variable_response(
                    "dependent_needed",
                    {"measurement_question": questions[0] if questions else "What will you be measuring as your outcome?"}
                )
            else:
                # Ask for more dependent variables
                return "Excellent! Are there any other outcomes you'll be measuring?"
        
        elif next_action == "control":
            if not control_vars:
                # Need to start identifying control variables
                questions = domain_guidance['suggested_questions'].get('control', CONTROL_VARIABLE_QUESTIONS[:1])
                return format_variable_response(
                    "control_needed",
                    {"control_question": questions[0] if questions else "What factors need to remain constant?"}
                )
            else:
                # Ask for more control variables
                return "Good! Are there any other factors you need to control for?"
        
        elif next_action == "refinement":
            # Need to refine existing variables
            validation_results = validate_variable_set(independent_vars, dependent_vars, control_vars)
            if validation_results['suggestions']:
                return f"Let's refine your variables. {validation_results['suggestions'][0]}"
            else:
                return "Let's review and refine your variables to ensure they're complete."
        
        else:
            # Finalization
            variable_summary = self._create_variable_summary(independent_vars, dependent_vars, control_vars)
            return format_variable_response(
                "completion_summary",
                {"variable_summary": variable_summary}
            )
    
    def _create_variable_summary(self, independent_vars: List[Dict[str, Any]], 
                                dependent_vars: List[Dict[str, Any]], 
                                control_vars: List[Dict[str, Any]]) -> str:
        """Create a summary of all variables."""
        summary = []
        
        if independent_vars:
            summary.append("Independent Variables:")
            for var in independent_vars:
                summary.append(f"  - {var.get('name', 'Unnamed')}")
        
        if dependent_vars:
            summary.append("Dependent Variables:")
            for var in dependent_vars:
                summary.append(f"  - {var.get('name', 'Unnamed')}")
        
        if control_vars:
            summary.append("Control Variables:")
            for var in control_vars:
                summary.append(f"  - {var.get('name', 'Unnamed')}")
        
        return "\n".join(summary)
    
    def get_variable_summary(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get a summary of the current variable identification progress.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Summary dictionary with variable details
        """
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        validation_results = validate_variable_set(independent_vars, dependent_vars, control_vars)
        
        research_query = state.get('research_query', '')
        objective = state.get('experiment_objective', '')
        domain_guidance = get_variable_domain_guidance(research_query, objective)
        
        return {
            "stage": "variable_identification",
            "independent_variables": independent_vars,
            "dependent_variables": dependent_vars,
            "control_variables": control_vars,
            "completion_score": validation_results['score'],
            "is_complete": validation_results['is_complete'],
            "missing_elements": validation_results['missing_elements'],
            "suggestions": validation_results['suggestions'],
            "domain_guidance": domain_guidance,
            "variable_examples": {
                "independent": get_variable_examples(domain_guidance['domain'], 'independent'),
                "dependent": get_variable_examples(domain_guidance['domain'], 'dependent'),
                "control": get_variable_examples(domain_guidance['domain'], 'control')
            }
        }
    
    def suggest_variables_for_domain(self, state: ExperimentPlanState) -> Dict[str, List[Dict[str, Any]]]:
        """
        Suggest variables based on the research domain.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Dictionary with suggested variables for each type
        """
        research_query = state.get('research_query', '')
        objective = state.get('experiment_objective', '')
        domain_guidance = get_variable_domain_guidance(research_query, objective)
        
        return {
            "independent": get_variable_examples(domain_guidance['domain'], 'independent'),
            "dependent": get_variable_examples(domain_guidance['domain'], 'dependent'),
            "control": get_variable_examples(domain_guidance['domain'], 'control')
        }
    
    def __repr__(self) -> str:
        return f"VariableAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 