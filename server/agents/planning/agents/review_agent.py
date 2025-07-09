"""
Final Review & Export Agent for the experiment planning system.

This agent specializes in conducting comprehensive validation of complete experiment plans,
identifying gaps and inconsistencies, and generating export-ready documents in multiple formats.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
from pydantic import ValidationError

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.review_prompts import REVIEW_SYSTEM_PROMPT
from ..models import ReviewOutput


class ReviewAgent(BaseAgent):
    """
    Agent responsible for the final, holistic review of the experiment plan.
    
    This agent leverages an LLM with structured output capabilities to:
    - Perform a comprehensive validation of the entire plan.
    - Assign a quality score based on completeness, coherence, and scientific rigor.
    - Identify key strengths and actionable suggestions for improvement.
    - Generate a final, export-ready summary of the plan.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Final Review Agent.
        
        Args:
            llm: Optional LangChain ChatOpenAI instance.
            debugger: Optional StateDebugger instance for logging.
            log_level: Logging level for this agent.
        """
        super().__init__(
            agent_name="review_agent",
            stage="final_review",
            debugger=debugger,
            log_level=log_level
        )
        from ..llm_config import get_llm
        self.llm = llm or get_llm()
        self.logger.info("ReviewAgent initialized for final review stage")

    def _create_context_for_llm(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Create a comprehensive context dictionary for the LLM prompt by serializing the state.

        Args:
            state: The current experiment plan state.

        Returns:
            A dictionary containing the full experiment plan for review.
        """
        # Create a serializable copy of the state, excluding sensitive or large items
        plan_for_review = {
            "Objective & Hypothesis": {
                "objective": state.get('experiment_objective'),
                "hypothesis": state.get('hypothesis')
            },
            "Variables": {
                "independent": state.get('independent_variables'),
                "dependent": state.get('dependent_variables'),
                "control": state.get('control_variables')
            },
            "Experimental Design": {
                "groups": state.get('experimental_groups'),
                "controls": state.get('control_groups'),
                "sample_size": state.get('sample_size')
            },
            "Methodology": {
                "steps": state.get('methodology_steps'),
                "materials": state.get('materials_equipment')
            },
            "Data & Analysis": {
                "collection_plan": state.get('data_collection_plan'),
                "analysis_plan": state.get('data_analysis_plan'),
                "expected_outcomes": state.get('expected_outcomes'),
                "pitfalls": state.get('potential_pitfalls')
            }
        }
        
        # Convert the dictionary to a JSON string for cleaner prompting
        return {"full_experiment_plan": json.dumps(plan_for_review, indent=2)}

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to conduct a final, holistic review of the entire plan.
        
        This method invokes an LLM with a structured output model (`ReviewOutput`)
        to generate a comprehensive assessment of the plan's quality and completeness.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with the final review.
        """
        self.logger.info(f"Processing final review for experiment: {state.get('experiment_id')}")

        context = self._create_context_for_llm(state)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", REVIEW_SYSTEM_PROMPT),
            ("human", """
Please conduct a final, comprehensive review of the entire experimental plan provided below.
Assess its overall quality, scientific rigor, completeness, and coherence.

**Full Experiment Plan:**
{full_experiment_plan}

Based on your review, please provide a quality score, identify the plan's greatest strengths, offer specific, actionable suggestions for improvement, and write a final executive summary.
Adhere strictly to the required output format.
            """),
        ])
        
        runnable = prompt | self.llm.with_structured_output(ReviewOutput)
        
        try:
            self.logger.info("Invoking LLM with structured output for final review.")
            review_output = runnable.invoke(context)
            
            # Add the entire review object to a new 'review' field in the state
            state['review'] = review_output.dict()
            
            summary_message = self._create_review_summary(state)
            state = add_chat_message(state, "assistant", summary_message)
            self.logger.info("Successfully updated state with the final plan review.")

        except ValidationError as e:
            error_message = f"LLM output failed validation for ReviewOutput: {e}"
            self.logger.error(error_message)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "I encountered an issue while finalizing the review. The output didn't have the correct structure. Let's try again.")
        
        except Exception as e:
            error_message = f"An unexpected error occurred during the final review: {e}"
            self.logger.error(error_message, exc_info=True)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "An unexpected error occurred during the final review. Please check the details and we can try again.")

        return update_state_timestamp(state)
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the final review stage requirements are met.
        
        For this agent, completion simply means the review has been successfully generated.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            A tuple of (is_valid, list_of_missing_requirements).
        """
        missing_requirements = []
        
        if not state.get('review'):
            missing_requirements.append("A final, comprehensive review of the plan.")
            
        is_valid = not missing_requirements
        return is_valid, missing_requirements

    def _create_review_summary(self, state: ExperimentPlanState) -> str:
        """Create a human-readable summary of the final review."""
        review = state.get('review', {})
        score = review.get('quality_score', 'N/A')
        strengths = review.get('strengths', [])
        suggestions = review.get('suggestions_for_improvement', [])

        summary = [
            f"I've completed a full review of your experimental plan and gave it a quality score of **{score}/100**.",
            "\nHere are its main strengths:",
        ]
        summary.extend([f"- {s}" for s in strengths])
        
        summary.append("\nHere are my suggestions for improvement:")
        summary.extend([f"- {s}" for s in suggestions])
        
        summary.append("\nThis plan is now complete. You can ask for modifications or export the final summary.")
        
        return "\n".join(summary)

    def __repr__(self) -> str:
        return f"ReviewAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 