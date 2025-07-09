"""
Methodology & Protocol Agent for the experiment planning system.

This agent specializes in generating detailed experimental protocols with step-by-step
procedures, creating comprehensive materials and equipment lists, and providing
domain-specific methodology guidance for robust experimental execution.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from pydantic import ValidationError

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.methodology_prompts import METHODOLOGY_SYSTEM_PROMPT
from ..models import MethodologyOutput


class MethodologyAgent(BaseAgent):
    """
    Agent responsible for developing a detailed experimental protocol and materials list.
    
    This agent leverages an LLM with structured output capabilities to:
    - Generate a complete, step-by-step experimental protocol.
    - Compile a comprehensive list of all necessary materials and equipment.
    - Ensure the methodology is detailed, reproducible, and aligned with the experimental design.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Methodology & Protocol Agent.
        
        Args:
            llm: Optional LangChain ChatOpenAI instance.
            debugger: Optional StateDebugger instance for logging.
            log_level: Logging level for this agent.
        """
        super().__init__(
            agent_name="methodology_agent",
            stage="methodology_protocol",
            debugger=debugger,
            log_level=log_level
        )
        from ..llm_config import get_llm
        self.llm = llm or get_llm()
        self.logger.info("MethodologyAgent initialized for methodology & protocol stage")

    def _create_context_for_llm(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Create a comprehensive context dictionary for the LLM prompt.

        Args:
            state: The current experiment plan state.

        Returns:
            A dictionary containing the necessary context for the methodology prompt.
        """
        # Convert complex objects to a string representation for the prompt
        experimental_groups = "\n".join([f"- {g.get('name')}: {g.get('description')}" for g in state.get('experimental_groups', [])])
        control_groups = "\n".join([f"- {g.get('name')} ({g.get('type')}): {g.get('purpose')}" for g in state.get('control_groups', [])])
        
        return {
            "objective": state.get('experiment_objective', 'Not defined'),
            "hypothesis": state.get('hypothesis', 'Not defined'),
            "experimental_design": f"Experimental Groups:\n{experimental_groups}\n\nControl Groups:\n{control_groups}",
            "chat_history": self._format_chat_history(state.get('chat_history', [])),
        }

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to generate a complete experimental protocol and materials list.
        
        This method invokes an LLM with a structured output model (`MethodologyOutput`)
        to generate the entire methodology in a single, validated step.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with the generated methodology and materials.
        """
        self.logger.info(f"Processing methodology for experiment: {state.get('experiment_id')}")

        context = self._create_context_for_llm(state)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", METHODOLOGY_SYSTEM_PROMPT),
            ("human", """
Based on the provided context, please generate a complete, step-by-step experimental protocol and a comprehensive list of required materials and equipment.

**Experiment Context:**
- **Objective:** {objective}
- **Hypothesis:** {hypothesis}
- **Experimental Design Summary:** 
{experimental_design}

**Conversation History:**
{chat_history}

Please generate a detailed, reproducible protocol with specific parameters and a full list of all necessary items.
Adhere strictly to the required output format.
            """),
        ])
        
        runnable = prompt | self.llm.with_structured_output(MethodologyOutput)
        
        try:
            self.logger.info("Invoking LLM with structured output for methodology.")
            methodology_output = runnable.invoke(context)
            
            # Update state with the structured output
            state['methodology_steps'] = [step.dict() for step in methodology_output.methodology_steps]
            state['materials_equipment'] = [item.dict() for item in methodology_output.materials_equipment]
            
            summary_message = self._create_methodology_summary(state)
            state = add_chat_message(state, "assistant", summary_message)
            self.logger.info("Successfully updated state with new methodology and materials list.")

        except ValidationError as e:
            error_message = f"LLM output failed validation for MethodologyOutput: {e}"
            self.logger.error(error_message)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "I had trouble structuring the experimental protocol. The output was not in the correct format. Let's try to regenerate it.")
        
        except Exception as e:
            error_message = f"An unexpected error occurred during methodology generation: {e}"
            self.logger.error(error_message, exc_info=True)
            state['errors'].append(error_message)
            state = add_chat_message(state, "assistant", "An unexpected error occurred while I was creating the experimental protocol. Please review the error, and we can try again.")

        return update_state_timestamp(state)
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the methodology and protocol stage requirements are met.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            A tuple of (is_valid, list_of_missing_requirements).
        """
        missing_requirements = []
        
        if not state.get('methodology_steps'):
            missing_requirements.append("A detailed, step-by-step experimental protocol.")
        
        if not state.get('materials_equipment'):
            missing_requirements.append("A comprehensive list of materials and equipment.")
            
        is_valid = not missing_requirements
        return is_valid, missing_requirements

    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions for the user based on current methodology development needs.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of questions to ask the user
        """
        from ..prompts.methodology_prompts import (
            METHODOLOGY_DEVELOPMENT_QUESTIONS,
            PROTOCOL_GENERATION_QUESTIONS,
            MATERIALS_EQUIPMENT_QUESTIONS,
            get_methodology_domain_guidance
        )
        
        # Get domain guidance
        research_query = state.get('research_query', '')
        experimental_design = {
            'experimental_groups': state.get('experimental_groups', []),
            'control_groups': state.get('control_groups', [])
        }
        
        domain_guidance = get_methodology_domain_guidance(research_query, experimental_design)
        
        # Get current methodology elements
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        # Determine what questions to ask based on what's missing
        if not methodology_steps:
            return PROTOCOL_GENERATION_QUESTIONS[:3]
        elif not materials_equipment:
            return MATERIALS_EQUIPMENT_QUESTIONS[:3]
        else:
            # Methodology refinement questions
            return [
                "Are there any specific parameters or conditions you'd like to adjust in your protocol?",
                "Do you need any additional materials or equipment for your experiment?",
                "Are there any safety considerations or quality control measures to add?"
            ]

    def _create_methodology_summary(self, state: ExperimentPlanState) -> str:
        """Create a summary of the generated methodology and materials list."""
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        summary = ["I have generated a detailed experimental protocol and a list of necessary materials for your review:"]
        
        if methodology_steps:
            summary.append(f"\n**Experimental Protocol ({len(methodology_steps)} steps):**")
            for step in methodology_steps[:3]:  # Show first 3 steps for brevity
                summary.append(f"- **Step {step.get('step_number', 'N/A')}**: {step.get('description', 'No description')}")
            if len(methodology_steps) > 3:
                summary.append(f"- ... and {len(methodology_steps) - 3} more steps.")

        if materials_equipment:
            summary.append(f"\n**Materials & Equipment ({len(materials_equipment)} items):**")
            for item in materials_equipment[:3]: # Show first 3 items
                summary.append(f"- **{item.get('name', 'Unnamed')}** ({item.get('type', 'N/A')})")
            if len(materials_equipment) > 3:
                summary.append(f"- ... and {len(materials_equipment) - 3} more items.")

        summary.append("\nPlease look over the generated protocol. We can refine it or proceed to the next stage.")
        
        return "\n".join(summary)

    def __repr__(self) -> str:
        return f"MethodologyAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 