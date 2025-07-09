"""
Objective Setting Agent for the experiment planning system.

This agent specializes in helping researchers clarify and refine their experimental
objectives, transforming vague ideas into specific, measurable, achievable, relevant,
and time-bound (SMART) goals with testable hypotheses.
"""

from typing import Dict, Any, Optional, Tuple, List
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message, update_state_timestamp
from ..models import ObjectiveOutput
from ..prompts.objective_prompts import (
    OBJECTIVE_SYSTEM_PROMPT,
    format_objective_response,
    validate_objective_completeness,
)


class ObjectiveAgent(BaseAgent):
    """
    Agent responsible for clarifying research objectives and developing SMART goals.
    
    This agent guides users through the process of transforming vague research ideas
    into specific, measurable objectives with clear hypotheses. It uses a structured
    LLM call to ensure reliable output.
    """
    
    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Objective Setting Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        super().__init__(
            agent_name="objective_agent",
            stage="objective_setting",
            debugger=debugger,
            log_level=log_level
        )
        # Configure the LLM for structured output
        from ..llm_config import get_llm
        llm = get_llm()
        self.structured_llm = llm.with_structured_output(ObjectiveOutput)
        self.logger.info("ObjectiveAgent initialized with structured LLM for objective setting.")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to define or refine the research objective and hypothesis.
        
        This method uses a structured LLM call to interpret the user's input and
        the current plan state, generating a validated objective and hypothesis.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with a refined objective and hypothesis.
        """
        self.logger.info(f"Processing state for experiment: {state.get('experiment_id')}")
        
        user_input = self._get_latest_user_input(state)
        chat_history = state.get("chat_history", [])
        
        # Create the prompt for the LLM
        prompt = ChatPromptTemplate.from_messages([
            ("system", OBJECTIVE_SYSTEM_PROMPT),
            ("human", 
             """Here is the relevant chat history: {chat_history}.
                Current research query: {research_query}
                Current objective: {objective}
                Current hypothesis: {hypothesis}
                
                Your task is to analyze my latest input and the current plan to define or refine the experiment objective and hypothesis.
                My latest input: "{user_input}"
             """
            )
        ])
        
        chain = prompt | self.structured_llm
        
        # Invoke the LLM to get a structured response
        try:
            response: ObjectiveOutput = chain.invoke({
                "chat_history": "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]]),
                "research_query": state.get("research_query"),
                "objective": state.get("experiment_objective"),
                "hypothesis": state.get("hypothesis"),
                "user_input": user_input
            })
            
            # Update the state with the structured output
            state['experiment_objective'] = response.experiment_objective
            state['hypothesis'] = response.hypothesis
            
            agent_response_text = f"Great, I've updated the plan:\n\n**Objective:** {response.experiment_objective}\n\n**Hypothesis:** {response.hypothesis}"
            self.logger.info("Successfully updated state with structured LLM output.")
            
        except Exception as e:
            self.logger.error(f"Error invoking structured LLM: {e}", exc_info=True)
            agent_response_text = "I had trouble understanding that. Could you please rephrase your request or provide more specific details about the objective and hypothesis?"

        # Add agent response to chat history and update timestamp
        updated_state = add_chat_message(state, "assistant", agent_response_text)
        updated_state = update_state_timestamp(updated_state)
        
        return updated_state
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the objective setting stage requirements are met.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        missing_requirements = []
        
        current_objective = state.get('experiment_objective')
        current_hypothesis = state.get('hypothesis')
        
        if not current_objective or len(current_objective.strip()) < 20:
            missing_requirements.append("A specific and detailed experiment objective is required.")
        
        if not current_hypothesis or len(current_hypothesis.strip()) < 10:
            missing_requirements.append("A clear, testable hypothesis is required.")
        
        # Use the validation function for a score-based check as well
        validation_results = validate_objective_completeness(
            current_objective, 
            current_hypothesis, 
            state.get('research_query', '')
        )
        
        is_valid = not missing_requirements and validation_results.get('score', 0) >= 80
        
        if not is_valid and not missing_requirements:
             missing_requirements.append("The objective and hypothesis need more detail to be considered complete. Please refine them further.")

        return is_valid, missing_requirements
    
    def _get_latest_user_input(self, state: ExperimentPlanState) -> str:
        """Extract the latest user input from chat history."""
        chat_history = state.get('chat_history', [])
        for message in reversed(chat_history):
            if message.get('role') == 'user':
                return message.get('content', '')
        return ''

    def get_objective_summary(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get a summary of the current objective setting progress.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Summary dictionary with objective details
        """
        current_objective = state.get('experiment_objective')
        current_hypothesis = state.get('hypothesis')
        research_query = state.get('research_query', '')
        
        validation_results = validate_objective_completeness(
            current_objective, 
            current_hypothesis, 
            research_query
        )
        
        return {
            "stage": "objective_setting",
            "research_query": research_query,
            "experiment_objective": current_objective,
            "hypothesis": current_hypothesis,
            "completion_score": validation_results.get('score', 0),
            "is_complete": validation_results.get('is_complete', False),
            "missing_elements": validation_results.get('missing_elements', []),
            "suggestions": validation_results.get('suggestions', [])
        }
    
    def __repr__(self) -> str:
        return f"ObjectiveAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 