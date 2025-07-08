"""
Methodology & Protocol Agent for the experiment planning system.

This agent specializes in generating detailed experimental protocols with step-by-step
procedures, creating comprehensive materials and equipment lists, and providing
domain-specific methodology guidance for robust experimental execution.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json

from .base_agent import BaseAgent
from ..state import ExperimentPlanState, METHODOLOGY_REQUIRED_FIELDS, MATERIAL_REQUIRED_FIELDS
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.methodology_prompts import (
    METHODOLOGY_SYSTEM_PROMPT,
    METHODOLOGY_DEVELOPMENT_QUESTIONS,
    PROTOCOL_GENERATION_QUESTIONS,
    MATERIALS_EQUIPMENT_QUESTIONS,
    METHODOLOGY_RESPONSE_TEMPLATES,
    get_methodology_domain_guidance,
    format_methodology_response,
    validate_methodology_completeness,
    suggest_protocol_steps,
    generate_materials_list
)


class MethodologyAgent(BaseAgent):
    """
    Agent responsible for developing detailed experimental protocols and methodology.
    
    This agent guides users through:
    - Creating step-by-step experimental protocols with specific parameters
    - Generating comprehensive materials and equipment lists
    - Providing domain-specific methodology guidance
    - Ensuring protocols are reproducible and scientifically rigorous
    - Identifying safety considerations and quality control measures
    """
    
    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Methodology & Protocol Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        super().__init__(
            agent_name="methodology_agent",
            stage="methodology_protocol",
            debugger=debugger,
            log_level=log_level
        )
        
        self.logger.info("MethodologyAgent initialized for methodology & protocol stage")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to develop experimental methodology and protocols.
        
        Analyzes the experimental design to generate detailed protocols with
        specific parameters, materials lists, and methodology guidance.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with methodology and protocol details
        """
        self.logger.info(f"Processing methodology development for experiment: {state.get('experiment_id')}")
        
        # Get the latest user input from chat history
        user_input = self._get_latest_user_input(state)
        
        # Get current methodology elements
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        # Get experimental design context
        experimental_design = {
            'experimental_groups': state.get('experimental_groups', []),
            'control_groups': state.get('control_groups', []),
            'independent_variables': state.get('independent_variables', []),
            'dependent_variables': state.get('dependent_variables', [])
        }
        
        # Validate current methodology
        validation_results = validate_methodology_completeness(methodology_steps, materials_equipment)
        
        # Get domain guidance
        research_query = state.get('research_query', '')
        domain_guidance = get_methodology_domain_guidance(research_query, experimental_design)
        
        # Determine what methodology elements are needed
        next_action = self._determine_next_methodology_action(state, validation_results, domain_guidance)
        
        # Process user input based on current needs
        if next_action == "protocol_steps":
            updated_state = self._process_protocol_steps(state, user_input, domain_guidance)
        elif next_action == "materials_equipment":
            updated_state = self._process_materials_equipment(state, user_input, domain_guidance)
        elif next_action == "refinement":
            updated_state = self._refine_methodology(state, user_input, domain_guidance)
        else:
            updated_state = self._finalize_methodology(state, user_input)
        
        # Generate agent response
        response = self._generate_methodology_response(updated_state, next_action, domain_guidance)
        updated_state = add_chat_message(updated_state, "assistant", response)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        self.logger.info(f"Methodology processing complete. Next action: {next_action}")
        
        return updated_state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions based on current methodology development needs.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of relevant questions for the user
        """
        # Get experimental design context
        experimental_design = {
            'experimental_groups': state.get('experimental_groups', []),
            'control_groups': state.get('control_groups', []),
            'independent_variables': state.get('independent_variables', []),
            'dependent_variables': state.get('dependent_variables', [])
        }
        
        # Get domain guidance
        research_query = state.get('research_query', '')
        domain_guidance = get_methodology_domain_guidance(research_query, experimental_design)
        
        # Get current methodology elements
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        # Determine what questions to ask
        if not methodology_steps:
            # Focus on protocol development
            questions = PROTOCOL_GENERATION_QUESTIONS[:3]
            
            # Add domain-specific questions
            if domain_guidance['domain'] == 'cell_culture':
                questions.extend([
                    "What cell lines will you be working with?",
                    "What culture conditions (temperature, CO2, media) will you use?",
                    "How will you assess cell viability or function?"
                ])
            elif domain_guidance['domain'] == 'molecular_biology':
                questions.extend([
                    "What DNA/RNA extraction method will you use?",
                    "What are your PCR conditions and primer sequences?",
                    "How will you analyze your molecular results?"
                ])
            elif domain_guidance['domain'] == 'biochemistry':
                questions.extend([
                    "What buffer systems will you use?",
                    "What are your enzyme assay conditions?",
                    "How will you measure protein concentrations?"
                ])
        
        elif not materials_equipment:
            # Focus on materials and equipment
            questions = MATERIALS_EQUIPMENT_QUESTIONS[:3]
            
            # Add domain-specific material questions
            if domain_guidance['domain'] != 'general':
                questions.extend([
                    f"Do you have all the essential {domain_guidance['domain']} materials?",
                    "Are there any specialized instruments you'll need?",
                    "What safety equipment is required for your procedures?"
                ])
        
        else:
            # Methodology refinement questions
            questions = METHODOLOGY_DEVELOPMENT_QUESTIONS[:3]
            questions.extend([
                "Are there any critical timing considerations in your protocol?",
                "What quality control measures will you implement?",
                "Are there any troubleshooting steps you should prepare for?"
            ])
        
        return questions[:5]  # Return top 5 questions
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the methodology and protocol stage requirements are met.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Get current methodology elements
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        # Validate using the methodology validation function
        validation_results = validate_methodology_completeness(methodology_steps, materials_equipment)
        
        if not validation_results['is_complete']:
            missing_requirements.extend(validation_results['missing_elements'])
            missing_requirements.extend(validation_results['suggestions'])
        
        # Detailed validation of methodology steps
        if not methodology_steps:
            missing_requirements.append("At least 5 detailed protocol steps")
        else:
            for i, step in enumerate(methodology_steps):
                if not self._validate_methodology_step_fields(step):
                    missing_requirements.append(f"Complete definition for protocol step {i+1}")
        
        # Detailed validation of materials and equipment
        if not materials_equipment:
            missing_requirements.append("At least 10 materials and equipment items")
        else:
            for i, item in enumerate(materials_equipment):
                if not self._validate_material_fields(item):
                    missing_requirements.append(f"Complete specifications for material/equipment {i+1}")
        
        # Check for safety considerations
        if methodology_steps and not any("safety" in step.get('description', '').lower() for step in methodology_steps):
            missing_requirements.append("Safety considerations and precautions")
        
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
    
    def _determine_next_methodology_action(self, state: ExperimentPlanState, 
                                         validation_results: Dict[str, Any],
                                         domain_guidance: Dict[str, Any]) -> str:
        """Determine what methodology action to take next based on current state."""
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        if not methodology_steps:
            return "protocol_steps"
        elif not materials_equipment:
            return "materials_equipment"
        elif validation_results['score'] < 80:
            return "refinement"
        else:
            return "finalize"
    
    def _process_protocol_steps(self, state: ExperimentPlanState, user_input: str, 
                               domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input to define protocol steps."""
        methodology_steps = state.get('methodology_steps', [])
        
        if user_input:
            # Parse user input for protocol steps
            new_steps = self._extract_protocol_steps(user_input, domain_guidance)
            
            if new_steps:
                methodology_steps.extend(new_steps)
                state['methodology_steps'] = methodology_steps
                
                self.logger.info(f"Added {len(new_steps)} protocol steps")
            else:
                # If no specific steps provided, suggest based on domain
                if not methodology_steps:
                    experimental_design = {
                        'experimental_groups': state.get('experimental_groups', []),
                        'control_groups': state.get('control_groups', []),
                        'independent_variables': state.get('independent_variables', []),
                        'dependent_variables': state.get('dependent_variables', [])
                    }
                    
                    suggested_steps = suggest_protocol_steps(domain_guidance['domain'], experimental_design)
                    methodology_steps.extend(suggested_steps)
                    state['methodology_steps'] = methodology_steps
                    
                    self.logger.info(f"Added {len(suggested_steps)} suggested protocol steps")
        
        return state
    
    def _process_materials_equipment(self, state: ExperimentPlanState, user_input: str,
                                   domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input to define materials and equipment."""
        materials_equipment = state.get('materials_equipment', [])
        
        if user_input:
            # Parse user input for materials and equipment
            new_materials = self._extract_materials_equipment(user_input, domain_guidance)
            
            if new_materials:
                materials_equipment.extend(new_materials)
                state['materials_equipment'] = materials_equipment
                
                self.logger.info(f"Added {len(new_materials)} materials/equipment items")
            else:
                # If no specific materials provided, suggest based on domain
                if not materials_equipment:
                    experimental_design = {
                        'experimental_groups': state.get('experimental_groups', []),
                        'control_groups': state.get('control_groups', []),
                        'independent_variables': state.get('independent_variables', []),
                        'dependent_variables': state.get('dependent_variables', [])
                    }
                    
                    suggested_materials = generate_materials_list(domain_guidance['domain'], experimental_design)
                    materials_equipment.extend(suggested_materials)
                    state['materials_equipment'] = materials_equipment
                    
                    self.logger.info(f"Added {len(suggested_materials)} suggested materials/equipment items")
        
        return state
    
    def _refine_methodology(self, state: ExperimentPlanState, user_input: str,
                           domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Refine existing methodology based on user input."""
        if not user_input:
            return state
        
        input_lower = user_input.lower()
        
        # Determine what aspect to refine
        if "step" in input_lower or "protocol" in input_lower:
            # Refine protocol steps
            methodology_steps = state.get('methodology_steps', [])
            if methodology_steps:
                # Simple refinement - in practice, this would be more sophisticated
                for step in methodology_steps:
                    if not step.get('parameters'):
                        step['parameters'] = "See detailed protocol"
                    if not step.get('duration'):
                        step['duration'] = "Variable"
                
                state['methodology_steps'] = methodology_steps
                self.logger.info("Refined protocol steps")
        
        elif "material" in input_lower or "equipment" in input_lower:
            # Refine materials and equipment
            materials_equipment = state.get('materials_equipment', [])
            if materials_equipment:
                # Simple refinement - add specifications where missing
                for item in materials_equipment:
                    if not item.get('specifications'):
                        item['specifications'] = "Standard laboratory grade"
                    if not item.get('quantity'):
                        item['quantity'] = "As needed"
                
                state['materials_equipment'] = materials_equipment
                self.logger.info("Refined materials and equipment")
        
        return state
    
    def _finalize_methodology(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Finalize methodology and prepare for next stage."""
        # Any final processing or validation
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        # Ensure all steps are numbered correctly
        for i, step in enumerate(methodology_steps):
            step['step_number'] = i + 1
        
        state['methodology_steps'] = methodology_steps
        
        self.logger.info("Finalized methodology and protocol")
        
        return state
    
    def _extract_protocol_steps(self, user_input: str, domain_guidance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract protocol steps from user input."""
        if not user_input:
            return []
        
        # Basic extraction - in reality, this would use NLP
        steps = []
        lines = user_input.split('\n')
        step_number = 1
        
        for line in lines:
            line = line.strip()
            if line:
                # Remove leading numbers and dots if present
                clean_line = line
                if line and line[0].isdigit() and ('.' in line or ')' in line):
                    # Extract text after number and delimiter
                    for i, char in enumerate(line):
                        if char in '.):':
                            clean_line = line[i+1:].strip()
                            break
                
                step = {
                    "step_number": step_number,
                    "description": clean_line,
                    "parameters": "To be specified",
                    "duration": "Variable"
                }
                steps.append(step)
                step_number += 1
        
        return steps
    
    def _extract_materials_equipment(self, user_input: str, domain_guidance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract materials and equipment from user input."""
        if not user_input:
            return []
        
        # Basic extraction - in reality, this would use NLP
        materials = []
        lines = user_input.split('\n')
        
        for line in lines:
            if line.strip():
                # Determine if it's equipment or material
                item_type = "equipment" if any(term in line.lower() for term in ["microscope", "centrifuge", "incubator", "pipette"]) else "reagent"
                
                material = {
                    "name": line.strip(),
                    "type": item_type,
                    "quantity": "As needed",
                    "specifications": "Standard laboratory grade"
                }
                materials.append(material)
        
        return materials
    
    def _validate_methodology_step_fields(self, step: Dict[str, Any]) -> bool:
        """Validate that a protocol step has all required fields."""
        return all(field in step and step[field] for field in METHODOLOGY_REQUIRED_FIELDS)
    
    def _validate_material_fields(self, item: Dict[str, Any]) -> bool:
        """Validate that a material/equipment item has all required fields."""
        return all(field in item and item[field] for field in MATERIAL_REQUIRED_FIELDS)
    
    def _generate_methodology_response(self, state: ExperimentPlanState, next_action: str,
                                     domain_guidance: Dict[str, Any]) -> str:
        """Generate appropriate response based on current state and next action."""
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        if next_action == "protocol_steps":
            if not methodology_steps:
                context = {
                    "context": f"For {domain_guidance['domain']} research, I'll help you develop a detailed protocol."
                }
                return format_methodology_response("protocol_development", context)
            else:
                return "Great! Do you have any additional protocol steps to add?"
        
        elif next_action == "materials_equipment":
            if not materials_equipment:
                context = {
                    "current_materials": f"Based on your {domain_guidance['domain']} protocol, let's identify materials."
                }
                return format_methodology_response("materials_needed", context)
            else:
                return "Excellent! Are there any other materials or equipment you need?"
        
        elif next_action == "refinement":
            protocol_summary = self._create_protocol_summary(methodology_steps)
            context = {
                "protocol_summary": protocol_summary,
                "refinement_focus": "Let's add more specific parameters and timing information."
            }
            return format_methodology_response("protocol_refinement", context)
        
        else:
            # Finalization
            methodology_summary = self._create_methodology_summary(methodology_steps, materials_equipment)
            context = {
                "methodology_summary": methodology_summary,
                "step_count": len(methodology_steps),
                "material_count": len(materials_equipment)
            }
            return format_methodology_response("methodology_complete", context)
    
    def _create_protocol_summary(self, methodology_steps: List[Dict[str, Any]]) -> str:
        """Create a summary of the protocol steps."""
        if not methodology_steps:
            return "No protocol steps defined yet."
        
        summary = []
        for step in methodology_steps:
            summary.append(f"Step {step.get('step_number', 0)}: {step.get('description', 'No description')}")
        
        return "\n".join(summary)
    
    def _create_methodology_summary(self, methodology_steps: List[Dict[str, Any]],
                                   materials_equipment: List[Dict[str, Any]]) -> str:
        """Create a summary of the complete methodology."""
        summary = []
        
        if methodology_steps:
            summary.append(f"Protocol Steps ({len(methodology_steps)}):")
            for step in methodology_steps[:3]:  # Show first 3 steps
                summary.append(f"  {step.get('step_number', 0)}. {step.get('description', 'No description')}")
            if len(methodology_steps) > 3:
                summary.append(f"  ... and {len(methodology_steps) - 3} more steps")
        
        if materials_equipment:
            summary.append(f"\nMaterials & Equipment ({len(materials_equipment)} items):")
            for item in materials_equipment[:3]:  # Show first 3 items
                summary.append(f"  - {item.get('name', 'Unknown')}")
            if len(materials_equipment) > 3:
                summary.append(f"  ... and {len(materials_equipment) - 3} more items")
        
        return "\n".join(summary)
    
    def get_methodology_summary(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get a summary of the current methodology development progress.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Summary dictionary with methodology details
        """
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        validation_results = validate_methodology_completeness(methodology_steps, materials_equipment)
        
        # Get domain guidance
        research_query = state.get('research_query', '')
        experimental_design = {
            'experimental_groups': state.get('experimental_groups', []),
            'control_groups': state.get('control_groups', []),
            'independent_variables': state.get('independent_variables', []),
            'dependent_variables': state.get('dependent_variables', [])
        }
        domain_guidance = get_methodology_domain_guidance(research_query, experimental_design)
        
        return {
            "stage": "methodology_protocol",
            "methodology_steps": methodology_steps,
            "materials_equipment": materials_equipment,
            "completion_score": validation_results['score'],
            "is_complete": validation_results['is_complete'],
            "missing_elements": validation_results['missing_elements'],
            "suggestions": validation_results['suggestions'],
            "domain": domain_guidance['domain'],
            "step_count": len(methodology_steps),
            "material_count": len(materials_equipment)
        }
    
    def __repr__(self) -> str:
        return f"MethodologyAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 