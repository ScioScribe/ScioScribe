"""
Variable Identification Agent for the experiment planning system.

This agent helps researchers identify and define the independent, dependent,
and control variables for their experiment based on the established objective.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate

from ..factory import add_chat_message
from ..models import VariableOutput
from ..prompts.variable_prompts import (
    VARIABLE_SYSTEM_PROMPT,
    validate_variable_set,
)
from ..state import ExperimentPlanState
from .base_agent import BaseAgent


class VariableAgent(BaseAgent):
    """
    Agent for identifying and defining experimental variables.
    
    This agent uses the experiment objective and hypothesis to guide the user
    in defining the independent, dependent, and control variables. It leverages
    a structured LLM to ensure all necessary variable details are captured.
    """

    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Variable Identification Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging.
            log_level: Logging level for this agent.
        """
        super().__init__(
            agent_name="variable_agent",
            stage="variable_identification",
            debugger=debugger,
            log_level=log_level,
        )
        from ..llm_config import get_llm
        llm = get_llm()
        self.structured_llm = llm.with_structured_output(VariableOutput)
        self.logger.info("VariableAgent initialized with structured LLM.")

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to define or refine experimental variables.
        
        This method uses a structured LLM call to interpret the user's input
        and the current plan state, generating comprehensive lists of variables.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with refined variable definitions.
        """
        self.logger.info(f"Processing state for experiment: {state.get('experiment_id')}")
        
        from ..graph.helpers import get_latest_user_input
        user_input = get_latest_user_input(state)
        chat_history = state.get("chat_history", [])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", VARIABLE_SYSTEM_PROMPT),
            ("human", 
             """Here is the relevant context for our experiment:
                Objective: {objective}
                Hypothesis: {hypothesis}
                
                Current variables identified:
                Independent: {independent_variables}
                Dependent: {dependent_variables}
                Control: {control_variables}
                
                Relevant chat history:
                {chat_history}
                
                Your task is to analyze my latest input and the current plan to define or refine all experimental variables.
                My latest input: "{user_input}"
             """
            )
        ])
        
        chain = prompt | self.structured_llm
        
        try:
            response: VariableOutput = chain.invoke({
                "objective": state.get("experiment_objective"),
                "hypothesis": state.get("hypothesis"),
                "independent_variables": state.get("independent_variables", []),
                "dependent_variables": state.get("dependent_variables", []),
                "control_variables": state.get("control_variables", []),
                "chat_history": "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]]),
                "user_input": user_input
            })

            # Update state with Pydantic model dicts
            state['independent_variables'] = [var.dict() for var in response.independent_variables]
            state['dependent_variables'] = [var.dict() for var in response.dependent_variables]
            state['control_variables'] = [var.dict() for var in response.control_variables]
            
            agent_response_text = self._create_variable_summary(state)
            self.logger.info("Successfully updated state with structured variable output.")
            
        except Exception as e:
            self.logger.error(f"Error invoking structured LLM for variables: {e}", exc_info=True)
            agent_response_text = "I had trouble understanding the variable details. Could you please clarify or provide them in a more structured way?"

        # Add agent response to chat history so it appears in the AI chat
        state = add_chat_message(state, "assistant", agent_response_text)
        self.logger.info(f"Variable agent response: {agent_response_text}")
        
        return state

    def validate_stage_requirements(
        self, state: ExperimentPlanState
    ) -> Tuple[bool, List[str]]:
        """
        Validate that the variable identification stage requirements are met.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            A tuple containing a boolean indicating if the stage is valid and a list of missing requirements.
        """
        independent_vars = state.get("independent_variables", [])
        dependent_vars = state.get("dependent_variables", [])
        
        validation_results = validate_variable_set(
            independent_vars, dependent_vars
        )
        
        is_valid = validation_results.get("is_complete", False)
        missing_requirements = validation_results.get("missing_elements", [])

        if not is_valid and not missing_requirements:
            missing_requirements.append(
                "The plan needs at least one independent and one dependent variable with all fields completed."
            )

        return is_valid, missing_requirements

    def _create_variable_summary(self, state: ExperimentPlanState) -> str:
        """Create a formatted summary of the variable definitions."""
        summary_parts = ["Great! I've updated the variable definitions in the plan:\n"]
        
        # Independent variables
        independent_vars = state.get('independent_variables', [])
        if independent_vars:
            summary_parts.append("**Independent Variables:**")
            for var in independent_vars:
                name = var.get('name', 'Unnamed')
                description = var.get('description', 'No description')
                summary_parts.append(f"- **{name}**: {description}")
        
        # Dependent variables  
        dependent_vars = state.get('dependent_variables', [])
        if dependent_vars:
            summary_parts.append("\n**Dependent Variables:**")
            for var in dependent_vars:
                name = var.get('name', 'Unnamed')
                description = var.get('description', 'No description')
                summary_parts.append(f"- **{name}**: {description}")
        
        # Control variables
        control_vars = state.get('control_variables', [])
        if control_vars:
            summary_parts.append("\n**Control Variables:**")
            for var in control_vars:
                name = var.get('name', 'Unnamed')
                description = var.get('description', 'No description')
                summary_parts.append(f"- **{name}**: {description}")
        
        return "\n".join(summary_parts)

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