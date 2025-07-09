"""
Data Planning & QA Agent for the experiment planning system.

This agent specializes in developing comprehensive data collection plans,
recommending statistical analysis approaches, identifying potential pitfalls,
and creating troubleshooting guides for robust experimental execution.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from pydantic import ValidationError

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.data_prompts import DATA_SYSTEM_PROMPT
from ..models import DataOutput


class DataAgent(BaseAgent):
    """
    Agent responsible for data collection and analysis planning.
    
    This agent leverages an LLM with structured output capabilities to:
    - Develop a comprehensive data collection and quality control plan.
    - Define a detailed data analysis and visualization strategy.
    - Identify potential experimental pitfalls and their mitigation strategies.
    - Articulate the expected outcomes of the experiment.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Data Planning & QA Agent.
        
        Args:
            llm: Optional LangChain ChatOpenAI instance.
            debugger: Optional StateDebugger instance for logging.
            log_level: Logging level for this agent.
        """
        super().__init__(
            agent_name="data_agent",
            stage="data_planning",
            debugger=debugger,
            log_level=log_level
        )
        from ..llm_config import get_llm
        self.llm = llm or get_llm()
        self.logger.info("DataAgent initialized for data planning stage")

    def _create_context_for_llm(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Create a comprehensive context dictionary for the LLM prompt.

        Args:
            state: The current experiment plan state.

        Returns:
            A dictionary containing the necessary context for the data planning prompt.
        """
        # Create summaries of previous stages to provide context
        design_summary = self._summarize_list(state.get('experimental_groups', []), "Experimental Groups") + "\n" + self._summarize_list(state.get('control_groups', []), "Control Groups")
        methodology_summary = self._summarize_list(state.get('methodology_steps', []), "Methodology Steps")

        return {
            "objective": state.get('experiment_objective', 'Not defined'),
            "hypothesis": state.get('hypothesis', 'Not defined'),
            "experimental_design": design_summary,
            "methodology": methodology_summary,
            "chat_history": self._format_chat_history(state.get('chat_history', [])),
        }

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to generate a complete data collection and analysis plan.
        
        This method invokes an LLM with a structured output model (`DataOutput`)
        to generate the entire data plan in a single, validated step.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with the generated data plan.
        """
        self.logger.info(f"Processing data plan for experiment: {state.get('experiment_id')}")

        context = self._create_context_for_llm(state)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", DATA_SYSTEM_PROMPT),
            ("human", """
Based on the provided context, please generate a comprehensive data collection plan, data analysis plan, a list of potential pitfalls, and the expected outcomes.

**Experiment Context:**
- **Objective:** {objective}
- **Hypothesis:** {hypothesis}
- **Experimental Design Summary:**
{experimental_design}
- **Methodology Summary:**
{methodology}

**Conversation History:**
{chat_history}

Please generate a detailed, logical, and complete data plan.
Adhere strictly to the required output format.
            """),
        ])
        
        runnable = prompt | self.llm.with_structured_output(DataOutput)
        
        try:
            self.logger.info("Invoking LLM with structured output for data planning.")
            data_output = runnable.invoke(context)
            
            # Update state with the structured output
            state['data_collection_plan'] = data_output.data_collection_plan.dict()
            state['data_analysis_plan'] = data_output.data_analysis_plan.dict()
            state['expected_outcomes'] = data_output.expected_outcomes
            state['potential_pitfalls'] = [pitfall.dict() for pitfall in data_output.potential_pitfalls]
            
            summary_message = self._create_data_plan_summary(state)
            state = add_chat_message(state, "assistant", summary_message)
            self.logger.info("Successfully updated state with new data plan.")

        except ValidationError as e:
            error_message = f"LLM output failed validation for DataOutput: {e}"
            self.logger.error(error_message)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "I had trouble structuring the data plan. The output was not in the correct format. Let's try to regenerate it.")
        
        except Exception as e:
            error_message = f"An unexpected error occurred during data plan generation: {e}"
            self.logger.error(error_message, exc_info=True)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "An unexpected error occurred while I was creating the data plan. Please review the error, and we can try again.")

        return update_state_timestamp(state)
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the data planning stage requirements are met.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            A tuple of (is_valid, list_of_missing_requirements).
        """
        missing_requirements = []
        
        if not state.get('data_collection_plan'):
            missing_requirements.append("A detailed data collection plan.")
        
        if not state.get('data_analysis_plan'):
            missing_requirements.append("A detailed data analysis plan.")
        
        if not state.get('expected_outcomes'):
            missing_requirements.append("A definition of expected outcomes.")
            
        if not state.get('potential_pitfalls') or len(state['potential_pitfalls']) < 3:
            missing_requirements.append("At least three potential pitfalls with mitigation strategies.")
            
        is_valid = not missing_requirements
        return is_valid, missing_requirements

    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions for the user based on current data planning needs.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of questions to ask the user
        """
        from ..prompts.data_prompts import (
            DATA_COLLECTION_QUESTIONS,
            STATISTICAL_ANALYSIS_QUESTIONS,
            PITFALL_IDENTIFICATION_QUESTIONS,
            SUCCESS_CRITERIA_QUESTIONS
        )
        
        # Get current data planning elements
        data_collection_plan = state.get('data_collection_plan', {})
        data_analysis_plan = state.get('data_analysis_plan', {})
        expected_outcomes = state.get('expected_outcomes', [])
        potential_pitfalls = state.get('potential_pitfalls', [])
        
        # Determine what questions to ask based on what's missing
        if not data_collection_plan:
            return DATA_COLLECTION_QUESTIONS[:3]
        elif not data_analysis_plan:
            return STATISTICAL_ANALYSIS_QUESTIONS[:3]
        elif not expected_outcomes:
            return SUCCESS_CRITERIA_QUESTIONS[:3]
        elif not potential_pitfalls or len(potential_pitfalls) < 3:
            return PITFALL_IDENTIFICATION_QUESTIONS[:3]
        else:
            # Data planning refinement questions
            return [
                "Would you like to refine your data collection or analysis approach?",
                "Are there any additional potential pitfalls we should consider?",
                "Do the expected outcomes align with your research objectives?"
            ]

    def _create_data_plan_summary(self, state: ExperimentPlanState) -> str:
        """Create a summary of the generated data plan."""
        collection_plan = state.get('data_collection_plan', {})
        analysis_plan = state.get('data_analysis_plan', {})
        pitfalls = state.get('potential_pitfalls', [])
        
        summary = ["I have drafted a comprehensive data collection and analysis plan for your review:"]
        
        if collection_plan:
            summary.append(f"\n**Data Collection:** {collection_plan.get('methods', 'N/A')}")
        
        if analysis_plan:
            summary.append(f"**Data Analysis:** {analysis_plan.get('statistical_tests', 'N/A')}")
        
        if pitfalls:
            summary.append(f"**Risk Assessment:** Identified {len(pitfalls)} potential pitfalls, including '{pitfalls[0].get('issue', 'N/A')}'.")

        summary.append("\nPlease review this plan. We can make adjustments or proceed to the final review.")
        
        return "\n".join(summary)

    def _summarize_list(self, item_list: List[Dict[str, Any]], title: str) -> str:
        """A helper to create a string summary of a list of dictionary items."""
        if not item_list:
            return f"{title}: None"
        
        # Use 'name' for groups/materials, 'description' for steps
        key = 'description' if title == "Methodology Steps" else 'name'
        
        summary_items = [f"- {item.get(key, 'Unnamed')}" for item in item_list[:2]]
        if len(item_list) > 2:
            summary_items.append(f"- ... and {len(item_list) - 2} more.")
            
        return f"{title}:\n" + "\n".join(summary_items)

    def __repr__(self) -> str:
        return f"DataAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 