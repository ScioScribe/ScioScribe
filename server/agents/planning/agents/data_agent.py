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
from langchain_core.exceptions import OutputParserException

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message
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
        # Use higher token limit for data agent to handle comprehensive plans
        self.llm = llm or get_llm(agent_type="data", max_tokens=3000)
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

    def _retry_with_fallback(self, state: ExperimentPlanState, max_retries: int = 2) -> ExperimentPlanState:
        """
        Retry data plan generation with progressively simpler approaches.
        
        Args:
            state: Current experiment plan state
            max_retries: Maximum number of retry attempts
            
        Returns:
            Updated state with data plan or error messages
        """
        context = self._create_context_for_llm(state)
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Data plan generation attempt {attempt + 1}/{max_retries + 1}")
                
                if attempt == 0:
                    # First attempt: Full detailed prompt
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
                    
                elif attempt == 1:
                    # Second attempt: Simplified prompt
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", DATA_SYSTEM_PROMPT),
                        ("human", """
Generate a concise data collection and analysis plan for: {objective}

**Key Requirements:**
- Data collection methods and timing
- Statistical analysis approach
- Expected outcomes
- 3 potential pitfalls with mitigation

Keep descriptions concise but complete.
                        """),
                    ])
                    # Use more conservative token limit
                    self.llm = self.llm.__class__(
                        **{**self.llm.__dict__, 'max_tokens': 2000}
                    )
                    
                else:
                    # Final attempt: Minimal prompt
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "You are a data analysis expert. Generate a concise data plan."),
                        ("human", "Create a data collection and analysis plan for: {objective}. Include methods, analysis, and 3 potential issues."),
                    ])
                    self.llm = self.llm.__class__(
                        **{**self.llm.__dict__, 'max_tokens': 1500}
                    )
                
                runnable = prompt | self.llm.with_structured_output(DataOutput)
                data_output = runnable.invoke(context)
                
                # Success! Update state and return
                state['data_collection_plan'] = data_output.data_collection_plan.dict()
                state['data_analysis_plan'] = data_output.data_analysis_plan.dict()
                state['expected_outcomes'] = data_output.expected_outcomes
                state['potential_pitfalls'] = [pitfall.dict() for pitfall in data_output.potential_pitfalls]
                
                summary_message = self._create_data_plan_summary(state)
                self.logger.info(f"Data plan summary created: {summary_message}")
                self.logger.info(f"Successfully generated data plan on attempt {attempt + 1}")
                return state
                
            except OutputParserException as e:
                self.logger.warning(f"JSON parsing error on attempt {attempt + 1}: {str(e)[:200]}...")
                if attempt == max_retries:
                    return self._create_fallback_data_plan(state, str(e))
                continue
                
            except ValidationError as e:
                self.logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    return self._create_fallback_data_plan(state, str(e))
                continue
                
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    return self._create_fallback_data_plan(state, str(e))
                continue
        
        # This should not be reached, but just in case
        return self._create_fallback_data_plan(state, "All retry attempts failed")

    def _create_fallback_data_plan(self, state: ExperimentPlanState, error_details: str) -> ExperimentPlanState:
        """
        Create a basic data plan structure when LLM generation fails.
        
        Args:
            state: Current experiment plan state
            error_details: Details about the error that occurred
            
        Returns:
            Updated state with fallback data plan
        """
        self.logger.info("Creating fallback data plan due to LLM generation failure")
        
        # Create basic data plan based on experimental design
        objective = state.get('experiment_objective', 'experiment')
        methodology_steps = state.get('methodology_steps', [])
        
        fallback_collection_plan = {
            "methods": "Data will be collected using appropriate measurement techniques as defined in the methodology",
            "timing": "Data collection will occur at specified timepoints during the experiment",
            "formats": "Data will be stored in structured formats suitable for analysis",
            "quality_control": "Standard quality control measures will be implemented"
        }
        
        fallback_analysis_plan = {
            "statistical_tests": "Appropriate statistical tests will be selected based on data distribution and experimental design",
            "visualizations": "Results will be visualized using standard scientific plots and graphs",
            "software": "Statistical analysis will be performed using appropriate software packages"
        }
        
        fallback_pitfalls = [
            {
                "issue": "Data quality issues or measurement errors",
                "likelihood": "Medium",
                "mitigation": "Implement proper calibration and quality control procedures"
            },
            {
                "issue": "Insufficient sample size or statistical power",
                "likelihood": "Low",
                "mitigation": "Verify sample size calculations and consider power analysis"
            },
            {
                "issue": "Unexpected experimental conditions or confounding variables",
                "likelihood": "Medium",
                "mitigation": "Monitor experimental conditions and document any deviations"
            }
        ]
        
        state['data_collection_plan'] = fallback_collection_plan
        state['data_analysis_plan'] = fallback_analysis_plan
        state['expected_outcomes'] = f"The experiment is expected to provide data that addresses the research objective: {objective}"
        state['potential_pitfalls'] = fallback_pitfalls
        
        # Add error message and guidance
        error_message = (
            f"I encountered an issue generating the detailed data plan ({error_details[:100]}...). "
            "I've created a basic data plan structure for you to review and expand upon. "
            "Please provide more specific details about your data collection and analysis needs, "
            "and I'll help you develop a more comprehensive plan."
        )
        
        state = add_chat_message(state, "assistant", error_message)
        self.logger.info("Fallback data plan created successfully")
        return state

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to generate a complete data collection and analysis plan.
        
        This method uses retry logic with progressively simpler approaches to handle
        token limits and JSON parsing errors.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with the generated data plan.
        """
        self.logger.info(f"Processing data plan for experiment: {state.get('experiment_id')}")

        try:
            return self._retry_with_fallback(state)
        except Exception as e:
            self.logger.error(f"Critical error in data plan processing: {e}", exc_info=True)
            return self._create_fallback_data_plan(state, str(e))
    
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