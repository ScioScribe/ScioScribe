"""
Experimental Design Agent for the experiment planning system.

This agent specializes in designing the experimental structure, determining
appropriate control groups, calculating statistical power, and optimizing
sample sizes for robust experimental design.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from pydantic import ValidationError

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import PydanticOutputFunctionsParser
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from ..state import ExperimentPlanState, GROUP_REQUIRED_FIELDS
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.design_prompts import (
    DESIGN_SYSTEM_PROMPT,
    EXPERIMENTAL_GROUP_QUESTIONS,
    CONTROL_GROUP_QUESTIONS,
    SAMPLE_SIZE_QUESTIONS,
    DESIGN_RESPONSE_TEMPLATES,
    STATISTICAL_CONSIDERATIONS,
    get_design_domain_guidance,
    format_design_response,
    validate_experimental_design,
    suggest_control_groups,
    calculate_power_analysis
)
from ..models import DesignOutput
from ..llm_config import get_llm


class DesignAgent(BaseAgent):
    """
    Agent responsible for generating a complete experimental design using a structured output model.
    
    This agent leverages an LLM with structured output capabilities to:
    - Design experimental and control groups based on defined variables.
    - Propose a statistically valid sample size with power analysis.
    - Consolidate all design elements into a single, validated `DesignOutput` model.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Experimental Design Agent.
        
        Args:
            llm: Optional LangChain ChatOpenAI instance.
            debugger: Optional StateDebugger instance for logging.
            log_level: Logging level for this agent.
        """
        super().__init__(
            agent_name="design_agent",
            stage="experimental_design",
            debugger=debugger,
            log_level=log_level
        )
        self.llm = llm or get_llm()
        self.logger.info("DesignAgent initialized for experimental design stage")
    
    def _create_context_for_llm(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Create a comprehensive context dictionary for the LLM prompt.

        Args:
            state: The current experiment plan state.

        Returns:
            A dictionary containing the necessary context for the design prompt.
        """
        # Serialize variables to a simpler format for the prompt
        independent_vars = ", ".join([v.get('name', '') for v in state.get('independent_variables', [])])
        dependent_vars = ", ".join([v.get('name', '') for v in state.get('dependent_variables', [])])

        return {
            "objective": state.get('experiment_objective', 'Not defined'),
            "hypothesis": state.get('hypothesis', 'Not defined'),
            "independent_variables": independent_vars,
            "dependent_variables": dependent_vars,
            "chat_history": self._format_chat_history(state.get('chat_history', [])),
        }

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to generate a complete experimental design.
        
        This method invokes an LLM with a structured output model (`DesignOutput`)
        to generate the entire experimental design in a single step.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with the generated experimental design.
        """
        self.logger.info(f"Processing experimental design for experiment: {state.get('experiment_id')}")

        context = self._create_context_for_llm(state)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", DESIGN_SYSTEM_PROMPT),
            ("human", """
Based on the provided context, please generate a complete experimental design.

**Experiment Context:**
- **Objective:** {objective}
- **Hypothesis:** {hypothesis}
- **Independent Variables:** {independent_variables}
- **Dependent Variables:** {dependent_variables}

**Conversation History:**
{chat_history}

Please generate the experimental groups, control groups, and sample size calculations needed to test the hypothesis.
Ensure the design is logical, complete, and statistically sound.
Adhere strictly to the required output format.
            """),
        ])
        
        # Create the runnable chain with structured output
        runnable = prompt | self.llm.with_structured_output(DesignOutput)
        
        try:
            self.logger.info("Invoking LLM with structured output for experimental design.")
            design_output = runnable.invoke(context)
            
            # Update state with the structured output, converting Pydantic models to dicts
            state['experimental_groups'] = [group.dict() for group in design_output.experimental_groups]
            state['control_groups'] = [group.dict() for group in design_output.control_groups]
            state['sample_size'] = design_output.sample_size.dict()
            
            # Add a summary message to the chat history
            summary_message = self._create_design_summary(state)
            state = add_chat_message(state, "assistant", summary_message)
            self.logger.info("Successfully updated state with new experimental design.")

        except ValidationError as e:
            error_message = f"LLM output failed validation for DesignOutput: {e}"
            self.logger.error(error_message)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "I encountered an issue generating the experimental design. The output didn't have the correct structure. Let's try again.")
        
        except Exception as e:
            error_message = f"An unexpected error occurred during design generation: {e}"
            self.logger.error(error_message, exc_info=True)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "I ran into an unexpected error while creating the experimental design. Please review the details and we can try again.")

        return update_state_timestamp(state)
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the experimental design stage requirements are met.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements).
        """
        missing_requirements = []
        
        if not state.get('experimental_groups'):
            missing_requirements.append("Definition of experimental groups.")
        
        if not state.get('control_groups'):
            missing_requirements.append("Definition of control groups.")
            
        if not state.get('sample_size'):
            missing_requirements.append("Sample size calculation and power analysis.")
        
        is_valid = not missing_requirements
        return is_valid, missing_requirements

    def _create_design_summary(self, state: ExperimentPlanState) -> str:
        """Create a summary of the generated experimental design."""
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        summary = ["I have drafted a complete experimental design for your review:"]
        
        if experimental_groups:
            summary.append(f"\n**Experimental Groups ({len(experimental_groups)}):**")
            for group in experimental_groups:
                summary.append(f"- **{group.get('name', 'Unnamed')}**: {group.get('description', 'No description')}")
        
        if control_groups:
            summary.append(f"\n**Control Groups ({len(control_groups)}):**")
            for group in control_groups:
                summary.append(f"- **{group.get('name', 'Unnamed')} ({group.get('type', 'N/A')})**: {group.get('purpose', 'No purpose')}")
        
        if sample_size:
            power_analysis = sample_size.get('power_analysis', {})
            required_n = power_analysis.get('required_sample_size', 'N/A')
            bio_reps = sample_size.get('biological_replicates', 'N/A')
            summary.append("\n**Sample Size:**")
            summary.append(f"- Based on a power analysis, the recommended sample size is **{required_n}** per group.")
            summary.append(f"- This includes **{bio_reps}** biological replicates.")

        summary.append("\nPlease review the design. We can make adjustments if needed, or proceed to the next stage.")
        
        return "\n".join(summary)

    def __repr__(self) -> str:
        return f"DesignAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 