"""
Objective Setting Agent for the experiment planning system.

This agent specializes in helping researchers clarify and refine their experimental
objectives, transforming vague ideas into specific, measurable, achievable, relevant,
and time-bound (SMART) goals with testable hypotheses.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import random

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.objective_prompts import (
    OBJECTIVE_SYSTEM_PROMPT,
    INITIAL_CLARIFICATION_QUESTIONS,
    SMART_OBJECTIVE_QUESTIONS,
    HYPOTHESIS_DEVELOPMENT_QUESTIONS,
    OBJECTIVE_CLARIFICATION_RESPONSES,
    ERROR_MESSAGES,
    get_domain_guidance,
    format_objective_response,
    validate_objective_completeness
)


class ObjectiveAgent(BaseAgent):
    """
    Agent responsible for clarifying research objectives and developing SMART goals.
    
    This agent guides users through the process of transforming vague research ideas
    into specific, measurable objectives with clear hypotheses. It uses conversational
    AI to ask clarifying questions and provide domain-specific guidance.
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
        
        self.logger.info("ObjectiveAgent initialized for objective setting stage")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to refine research objectives.
        
        Analyzes the current state and user input to progressively refine
        the experiment objective and hypothesis through guided questioning.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with refined objectives
        """
        self.logger.info(f"Processing state for experiment: {state.get('experiment_id')}")
        
        # Get the latest user input from chat history
        user_input = self._get_latest_user_input(state)
        
        # Analyze current objective completeness
        current_objective = state.get('experiment_objective')
        current_hypothesis = state.get('hypothesis')
        research_query = state.get('research_query', '')
        
        # Validate completeness
        validation_results = validate_objective_completeness(
            current_objective, 
            current_hypothesis, 
            research_query
        )
        
        # Process based on current state and user input
        if not current_objective:
            # First interaction - extract initial objective from user input
            updated_state = self._extract_initial_objective(state, user_input)
        elif validation_results['score'] < 50:
            # Objective needs significant refinement
            updated_state = self._refine_objective(state, user_input, validation_results)
        elif not current_hypothesis:
            # Objective is decent, now develop hypothesis
            updated_state = self._develop_hypothesis(state, user_input)
        else:
            # Both objective and hypothesis exist, validate and refine
            updated_state = self._validate_and_finalize(state, user_input, validation_results)
        
        # Add agent response to chat history
        response = self._generate_agent_response(updated_state, validation_results)
        updated_state = add_chat_message(updated_state, "assistant", response)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        self.logger.info(f"Objective processing complete. Score: {validation_results['score']}")
        
        return updated_state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions based on current state.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of relevant questions for the user
        """
        current_objective = state.get('experiment_objective')
        current_hypothesis = state.get('hypothesis')
        research_query = state.get('research_query', '')
        
        # Get domain-specific guidance
        domain_info = get_domain_guidance(research_query)
        
        if not current_objective:
            # Initial clarification questions
            questions = domain_info['suggested_questions']
            questions.extend(INITIAL_CLARIFICATION_QUESTIONS[:3])
        elif not current_hypothesis:
            # Questions to develop hypothesis
            questions = HYPOTHESIS_DEVELOPMENT_QUESTIONS[:3]
        else:
            # SMART refinement questions
            questions = SMART_OBJECTIVE_QUESTIONS[:3]
        
        # Randomize order to avoid predictability
        random.shuffle(questions)
        
        return questions[:5]  # Return top 5 questions
    
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
        research_query = state.get('research_query', '')
        
        # Validate objective completeness
        validation_results = validate_objective_completeness(
            current_objective, 
            current_hypothesis, 
            research_query
        )
        
        if not validation_results['is_complete']:
            missing_requirements.extend(validation_results['missing_elements'])
            missing_requirements.extend(validation_results['suggestions'])
        
        # Additional specific checks
        if not current_objective or len(current_objective.strip()) < 20:
            missing_requirements.append("Detailed experiment objective")
        
        if not current_hypothesis or len(current_hypothesis.strip()) < 10:
            missing_requirements.append("Testable hypothesis")
        
        # Check for SMART criteria
        if current_objective:
            objective_lower = current_objective.lower()
            
            if not any(word in objective_lower for word in ["measure", "quantify", "assess", "determine"]):
                missing_requirements.append("Measurable outcomes in objective")
            
            if not any(word in objective_lower for word in ["specific", "particular", "examine"]):
                missing_requirements.append("Specific focus in objective")
        
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
    
    def _extract_initial_objective(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Extract and set initial objective from user input."""
        # Use research query as fallback if no user input
        objective_text = user_input or state.get('research_query', '')
        
        if objective_text:
            # Simple extraction - in a real implementation, this would use NLP
            # For now, we'll use the user input as a starting point
            state['experiment_objective'] = objective_text
            
            self.logger.info(f"Extracted initial objective: {objective_text[:50]}...")
        
        return state
    
    def _refine_objective(self, state: ExperimentPlanState, user_input: str, validation_results: Dict[str, Any]) -> ExperimentPlanState:
        """Refine the existing objective based on user input."""
        if user_input:
            current_objective = state.get('experiment_objective', '')
            
            # Append user input to refine objective
            if current_objective:
                refined_objective = f"{current_objective} {user_input}"
            else:
                refined_objective = user_input
            
            state['experiment_objective'] = refined_objective
            
            self.logger.info(f"Refined objective based on user input")
        
        return state
    
    def _develop_hypothesis(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Develop hypothesis based on user input."""
        if user_input:
            # Set hypothesis from user input
            state['hypothesis'] = user_input
            
            self.logger.info(f"Developed hypothesis: {user_input[:50]}...")
        
        return state
    
    def _validate_and_finalize(self, state: ExperimentPlanState, user_input: str, validation_results: Dict[str, Any]) -> ExperimentPlanState:
        """Validate and finalize objectives and hypothesis."""
        if user_input:
            # Process any final refinements
            if "objective" in user_input.lower():
                # User wants to modify objective
                current_objective = state.get('experiment_objective', '')
                state['experiment_objective'] = f"{current_objective} {user_input}"
            elif "hypothesis" in user_input.lower():
                # User wants to modify hypothesis
                current_hypothesis = state.get('hypothesis', '')
                state['hypothesis'] = f"{current_hypothesis} {user_input}"
            else:
                # General refinement
                current_objective = state.get('experiment_objective', '')
                state['experiment_objective'] = f"{current_objective} {user_input}"
        
        return state
    
    def _generate_agent_response(self, state: ExperimentPlanState, validation_results: Dict[str, Any]) -> str:
        """Generate appropriate response based on current state."""
        current_objective = state.get('experiment_objective')
        current_hypothesis = state.get('hypothesis')
        research_query = state.get('research_query', '')
        
        # Get domain guidance
        domain_info = get_domain_guidance(research_query)
        
        if validation_results['is_complete']:
            # Objective is complete
            objective_summary = f"Objective: {current_objective}\nHypothesis: {current_hypothesis}"
            return format_objective_response(
                "completion_ready",
                {"objective_summary": objective_summary}
            )
        
        elif not current_objective:
            # Need initial objective
            return format_objective_response(
                "vague_initial",
                {
                    "research_area": research_query,
                    "clarification_focus": "what specific aspect you want to study"
                }
            )
        
        elif not current_hypothesis:
            # Need hypothesis
            return format_objective_response(
                "hypothesis_prompt",
                {
                    "objective": current_objective,
                    "hypothesis_guidance": "What outcome do you predict based on your research?"
                }
            )
        
        else:
            # Need refinement
            suggestions = validation_results.get('suggestions', [])
            missing_elements = validation_results.get('missing_elements', [])
            
            if suggestions:
                return format_objective_response(
                    "needs_specificity",
                    {
                        "specific_guidance": suggestions[0],
                        "follow_up_question": self._get_follow_up_question(missing_elements)
                    }
                )
            
            return "Let's continue refining your objective. What additional details can you provide?"
    
    def _get_follow_up_question(self, missing_elements: List[str]) -> str:
        """Get appropriate follow-up question based on missing elements."""
        if not missing_elements:
            return "What other details would be helpful to specify?"
        
        element = missing_elements[0]
        
        if "objective" in element.lower():
            return "Could you be more specific about what you want to measure or observe?"
        elif "hypothesis" in element.lower():
            return "What outcome do you expect to see in your experiment?"
        else:
            return f"Could you provide more information about {element.lower()}?"
    
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
            "completion_score": validation_results['score'],
            "is_complete": validation_results['is_complete'],
            "missing_elements": validation_results['missing_elements'],
            "suggestions": validation_results['suggestions'],
            "domain_guidance": get_domain_guidance(research_query)
        }
    
    def __repr__(self) -> str:
        return f"ObjectiveAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 