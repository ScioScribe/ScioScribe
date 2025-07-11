"""
Methodology & Protocol Agent for the experiment planning system.

This agent specializes in generating detailed experimental protocols with step-by-step
procedures, creating comprehensive materials and equipment lists, and providing
domain-specific methodology guidance for robust experimental execution.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
from pydantic import ValidationError

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message
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
        # Use higher token limit for methodology agent to handle complex protocols
        self.llm = llm or get_llm(agent_type="methodology", max_tokens=4000)
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

    def _create_simplified_prompt(self) -> ChatPromptTemplate:
        """Create a simplified prompt that focuses on essential information to reduce token usage."""
        return ChatPromptTemplate.from_messages([
            ("system", METHODOLOGY_SYSTEM_PROMPT),
            ("human", """
Based on the provided context, generate a concise but complete experimental protocol and materials list.

**Experiment Context:**
- **Objective:** {objective}
- **Hypothesis:** {hypothesis}
- **Experimental Design:** {experimental_design}

**CRITICAL REQUIREMENTS:**
1. Keep descriptions concise but complete
2. Focus on essential steps and materials only
3. Use standard abbreviations where appropriate
4. Limit protocol to 6-8 key steps maximum
5. Include only essential materials and equipment

**Output Format Requirements:**
- Each step must have: step_number, description, parameters, duration
- Each material must have: name, type, quantity, specifications
- Use simple ASCII characters only (avoid µ, °, etc.)

Generate a practical, implementable protocol that covers all essential aspects.
            """),
        ])

    def _retry_with_fallback(self, state: ExperimentPlanState, max_retries: int = 2) -> ExperimentPlanState:
        """
        Retry methodology generation with progressively simpler approaches.
        
        Args:
            state: Current experiment plan state
            max_retries: Maximum number of retry attempts
            
        Returns:
            Updated state with methodology or error messages
        """
        context = self._create_context_for_llm(state)
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Methodology generation attempt {attempt + 1}/{max_retries + 1}")
                
                if attempt == 0:
                    # First attempt: Full detailed prompt
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

**IMPORTANT REQUIREMENTS:**
1. Each methodology step MUST include:
   - step_number: Sequential number (1, 2, 3, etc.)
   - description: Detailed description of the action
   - parameters: Dictionary of critical parameters (volumes, concentrations, temperatures, etc.)
   - duration: Estimated time to complete (optional)

2. Each material/equipment item MUST include:
   - name: Specific name of the item
   - type: Category (reagent, consumable, equipment)
   - quantity: Amount needed (optional)
   - specifications: Grade, model, supplier info (optional)

Please generate a detailed, reproducible protocol with specific parameters and a full list of all necessary items.
Adhere strictly to the required output format with all required fields.
                        """),
                    ])
                    
                elif attempt == 1:
                    # Second attempt: Simplified prompt with lower token target
                    prompt = self._create_simplified_prompt()
                    # Use a more conservative token limit
                    self.llm = self.llm.__class__(
                        **{**self.llm.__dict__, 'max_tokens': 3000}
                    )
                    
                else:
                    # Final attempt: Minimal prompt
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "You are a scientific methodology expert. Generate a concise experimental protocol."),
                        ("human", "Create a step-by-step protocol for: {objective}. Include essential materials. Keep it concise but complete."),
                    ])
                    self.llm = self.llm.__class__(
                        **{**self.llm.__dict__, 'max_tokens': 2000}
                    )
                
                runnable = prompt | self.llm.with_structured_output(MethodologyOutput)
                methodology_output = runnable.invoke(context)
                
                # Success! Update state and return
                state['methodology_steps'] = [step.dict() for step in methodology_output.methodology_steps]
                state['materials_equipment'] = [item.dict() for item in methodology_output.materials_equipment]
                
                summary_message = self._create_methodology_summary(state)
                self.logger.info(f"Methodology summary created: {summary_message}")
                self.logger.info(f"Successfully generated methodology on attempt {attempt + 1}")
                return state
                
            except OutputParserException as e:
                self.logger.warning(f"JSON parsing error on attempt {attempt + 1}: {str(e)[:200]}...")
                if attempt == max_retries:
                    # Final attempt failed, create manual fallback
                    return self._create_fallback_methodology(state, str(e))
                continue
                
            except ValidationError as e:
                self.logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    return self._create_fallback_methodology(state, str(e))
                continue
                
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    return self._create_fallback_methodology(state, str(e))
                continue
        
        # This should not be reached, but just in case
        return self._create_fallback_methodology(state, "All retry attempts failed")

    def _create_fallback_methodology(self, state: ExperimentPlanState, error_details: str) -> ExperimentPlanState:
        """
        Create a basic methodology structure when LLM generation fails.
        
        Args:
            state: Current experiment plan state
            error_details: Details about the error that occurred
            
        Returns:
            Updated state with fallback methodology
        """
        self.logger.info("Creating fallback methodology due to LLM generation failure")
        
        # Create basic methodology steps based on experimental design
        experimental_groups = state.get('experimental_groups', [])
        objective = state.get('experiment_objective', 'experiment')
        
        fallback_steps = [
            {
                "step_number": 1,
                "description": "Prepare experimental setup and materials according to the experimental design",
                "parameters": {"setup_time": "30 minutes", "temperature": "room temperature"},
                "duration": "30 minutes"
            },
            {
                "step_number": 2,
                "description": "Set up experimental groups as defined in the design",
                "parameters": {"groups": len(experimental_groups), "replicates": "as specified"},
                "duration": "1 hour"
            },
            {
                "step_number": 3,
                "description": "Execute the experimental protocol for each group",
                "parameters": {"monitoring": "continuous", "documentation": "detailed"},
                "duration": "varies"
            },
            {
                "step_number": 4,
                "description": "Collect and record data according to the measurement plan",
                "parameters": {"data_format": "structured", "quality_control": "standard"},
                "duration": "varies"
            }
        ]
        
        fallback_materials = [
            {
                "name": "Standard laboratory equipment",
                "type": "equipment",
                "quantity": "as needed",
                "specifications": "laboratory grade"
            },
            {
                "name": "Experimental reagents",
                "type": "reagent",
                "quantity": "as calculated",
                "specifications": "research grade"
            },
            {
                "name": "Data recording materials",
                "type": "consumable",
                "quantity": "sufficient",
                "specifications": "standard"
            }
        ]
        
        state['methodology_steps'] = fallback_steps
        state['materials_equipment'] = fallback_materials
        
        # Add error message and guidance
        error_message = (
            f"I encountered an issue generating the detailed methodology ({error_details[:100]}...). "
            "I've created a basic protocol structure for you to review and expand upon. "
            "Please provide more specific details about your experimental procedures, "
            "and I'll help you develop a more detailed protocol."
        )
        
        state = add_chat_message(state, "assistant", error_message)
        self.logger.info("Fallback methodology created successfully")
        return state

    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to generate a complete experimental protocol and materials list.
        
        This method uses retry logic with progressively simpler approaches to handle
        token limits and JSON parsing errors.
        
        Args:
            state: Current experiment plan state.
            
        Returns:
            Updated ExperimentPlanState with the generated methodology and materials.
        """
        self.logger.info(f"Processing methodology for experiment: {state.get('experiment_id')}")
        
        try:
            return self._retry_with_fallback(state)
        except Exception as e:
            self.logger.error(f"Critical error in methodology processing: {e}", exc_info=True)
            return self._create_fallback_methodology(state, str(e))

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