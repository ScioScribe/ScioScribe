"""
Experimental Design Agent for the experiment planning system.

This agent specializes in designing the experimental structure, determining
appropriate control groups, calculating statistical power, and optimizing
sample sizes for robust experimental design.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import math
from scipy import stats
import numpy as np

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


class DesignAgent(BaseAgent):
    """
    Agent responsible for experimental design and statistical power calculations.
    
    This agent guides users through:
    - Designing experimental groups and conditions
    - Recommending appropriate control groups
    - Calculating statistical power and sample sizes
    - Providing randomization and blinding recommendations
    """
    
    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Experimental Design Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        super().__init__(
            agent_name="design_agent",
            stage="experimental_design",
            debugger=debugger,
            log_level=log_level
        )
        
        self.logger.info("DesignAgent initialized for experimental design stage")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to design experimental structure.
        
        Analyzes variables and objectives to design appropriate experimental
        groups, control groups, and determine statistically valid sample sizes.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with experimental design
        """
        self.logger.info(f"Processing experimental design for experiment: {state.get('experiment_id')}")
        
        # Get the latest user input from chat history
        user_input = self._get_latest_user_input(state)
        
        # Get current design elements
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        # Validate current design
        validation_results = validate_experimental_design(
            experimental_groups, 
            control_groups, 
            sample_size,
            state.get('independent_variables', []),
            state.get('dependent_variables', [])
        )
        
        # Determine what design elements are needed
        next_action = self._determine_next_design_action(state, validation_results)
        
        # Process user input based on current needs
        if next_action == "experimental_groups":
            updated_state = self._process_experimental_groups(state, user_input)
        elif next_action == "control_groups":
            updated_state = self._process_control_groups(state, user_input)
        elif next_action == "sample_size":
            updated_state = self._process_sample_size(state, user_input)
        elif next_action == "refinement":
            updated_state = self._refine_design(state, user_input)
        else:
            updated_state = self._finalize_design(state, user_input)
        
        # Generate agent response
        response = self._generate_design_response(updated_state, next_action)
        updated_state = add_chat_message(updated_state, "assistant", response)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        self.logger.info(f"Experimental design processing complete. Next action: {next_action}")
        
        return updated_state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions based on current design needs.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of relevant questions for the user
        """
        # Get domain guidance
        research_query = state.get('research_query', '')
        objective = state.get('experiment_objective', '')
        variables = state.get('independent_variables', [])
        
        domain_guidance = get_design_domain_guidance(research_query, objective, variables)
        
        # Get current design elements
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        # Determine what questions to ask
        if not experimental_groups:
            return domain_guidance['suggested_questions'].get('experimental', EXPERIMENTAL_GROUP_QUESTIONS[:3])
        elif not control_groups:
            return domain_guidance['suggested_questions'].get('control', CONTROL_GROUP_QUESTIONS[:3])
        elif not sample_size:
            return domain_guidance['suggested_questions'].get('sample_size', SAMPLE_SIZE_QUESTIONS[:3])
        else:
            # Design refinement questions
            return [
                "Does your experimental design adequately test your hypothesis?",
                "Are there any additional control conditions needed?",
                "Is the sample size sufficient for your expected effect size?"
            ]
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the experimental design stage requirements are met.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Get current design elements
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        
        # Validate using the design validation function
        validation_results = validate_experimental_design(
            experimental_groups, 
            control_groups, 
            sample_size,
            independent_vars,
            dependent_vars
        )
        
        if not validation_results['is_complete']:
            missing_requirements.extend(validation_results['missing_elements'])
            missing_requirements.extend(validation_results['suggestions'])
        
        # Detailed validation of design elements
        if not experimental_groups:
            missing_requirements.append("At least one experimental group")
        else:
            for i, group in enumerate(experimental_groups):
                if not self._validate_group_fields(group):
                    missing_requirements.append(f"Complete definition for experimental group {i+1}")
        
        if not control_groups:
            missing_requirements.append("At least one control group")
        else:
            for i, group in enumerate(control_groups):
                if not self._validate_control_group_fields(group):
                    missing_requirements.append(f"Complete definition for control group {i+1}")
        
        if not sample_size:
            missing_requirements.append("Sample size calculation with power analysis")
        else:
            required_sample_fields = ['biological_replicates', 'technical_replicates', 'power_analysis']
            for field in required_sample_fields:
                if field not in sample_size:
                    missing_requirements.append(f"Sample size {field.replace('_', ' ')}")
        
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
    
    def _determine_next_design_action(self, state: ExperimentPlanState, validation_results: Dict[str, Any]) -> str:
        """Determine what design action to take next based on current state."""
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        if not experimental_groups:
            return "experimental_groups"
        elif not control_groups:
            return "control_groups"
        elif not sample_size:
            return "sample_size"
        elif validation_results['score'] < 80:
            return "refinement"
        else:
            return "finalize"
    
    def _process_experimental_groups(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Process user input to define experimental groups."""
        if not user_input:
            return state
        
        # Extract group information from user input
        group_info = self._extract_group_info(user_input, "experimental")
        
        if group_info:
            # Add to existing experimental groups
            experimental_groups = state.get('experimental_groups', [])
            experimental_groups.append(group_info)
            state['experimental_groups'] = experimental_groups
            
            self.logger.info(f"Added experimental group: {group_info.get('name', 'unnamed')}")
        
        return state
    
    def _process_control_groups(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Process user input to define control groups."""
        if not user_input:
            return state
        
        # Extract control group information from user input
        control_info = self._extract_control_info(user_input)
        
        if control_info:
            # Add to existing control groups
            control_groups = state.get('control_groups', [])
            control_groups.append(control_info)
            state['control_groups'] = control_groups
            
            self.logger.info(f"Added control group: {control_info.get('type', 'unnamed')}")
        
        return state
    
    def _process_sample_size(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Process user input to determine sample size and perform power analysis."""
        if not user_input:
            return state
        
        # Extract sample size information
        sample_info = self._extract_sample_size_info(user_input)
        
        if sample_info:
            # Perform power analysis
            power_analysis = self._perform_power_analysis(state, sample_info)
            
            # Update sample size with power analysis
            sample_size = {
                'biological_replicates': sample_info.get('biological_replicates', 3),
                'technical_replicates': sample_info.get('technical_replicates', 3),
                'power_analysis': power_analysis
            }
            
            state['sample_size'] = sample_size
            
            self.logger.info(f"Calculated sample size with power analysis")
        
        return state
    
    def _refine_design(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Refine existing experimental design based on user input."""
        if not user_input:
            return state
        
        # Simple refinement logic - in practice, this would be more sophisticated
        input_lower = user_input.lower()
        
        if "experimental" in input_lower and "group" in input_lower:
            # User wants to modify experimental groups
            pass
        elif "control" in input_lower:
            # User wants to modify control groups
            pass
        elif "sample" in input_lower or "size" in input_lower:
            # User wants to modify sample size
            pass
        
        return state
    
    def _finalize_design(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Finalize experimental design and prepare for next stage."""
        # Any final processing or validation
        return state
    
    def _extract_group_info(self, user_input: str, group_type: str) -> Optional[Dict[str, Any]]:
        """Extract experimental group information from user input."""
        if not user_input:
            return None
        
        # Basic extraction - in reality, this would use NLP
        group_info = {
            "name": user_input.strip(),
            "description": user_input.strip(),
            "conditions": []  # Would be extracted from input
        }
        
        return group_info
    
    def _extract_control_info(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Extract control group information from user input."""
        if not user_input:
            return None
        
        # Basic extraction
        control_info = {
            "type": self._infer_control_type(user_input),
            "purpose": user_input.strip(),
            "description": user_input.strip()
        }
        
        return control_info
    
    def _extract_sample_size_info(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Extract sample size information from user input."""
        if not user_input:
            return None
        
        # Basic extraction - would use NLP to extract numbers
        sample_info = {
            "biological_replicates": 3,  # Default
            "technical_replicates": 3,   # Default
            "effect_size": 0.5,         # Default medium effect
            "alpha": 0.05,              # Default significance level
            "power": 0.8                # Default statistical power
        }
        
        return sample_info
    
    def _infer_control_type(self, user_input: str) -> str:
        """Infer control group type from user input."""
        input_lower = user_input.lower()
        
        if "negative" in input_lower:
            return "negative"
        elif "positive" in input_lower:
            return "positive"
        elif "vehicle" in input_lower or "placebo" in input_lower:
            return "vehicle"
        elif "technical" in input_lower:
            return "technical"
        else:
            return "negative"  # Default
    
    def _perform_power_analysis(self, state: ExperimentPlanState, sample_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform statistical power analysis."""
        try:
            effect_size = sample_info.get('effect_size', 0.5)
            alpha = sample_info.get('alpha', 0.05)
            power = sample_info.get('power', 0.8)
            
            # Calculate required sample size using t-test power analysis
            # This is a simplified calculation - in practice, would depend on experimental design
            required_n = self._calculate_sample_size_ttest(effect_size, alpha, power)
            
            power_analysis = {
                "effect_size": effect_size,
                "alpha": alpha,
                "power": power,
                "required_sample_size": required_n,
                "statistical_test": "two_sample_ttest",
                "assumptions": [
                    "Normal distribution",
                    "Equal variances",
                    "Independent samples"
                ]
            }
            
            return power_analysis
            
        except Exception as e:
            self.logger.error(f"Power analysis failed: {e}")
            return {
                "error": str(e),
                "required_sample_size": 10,  # Conservative default
                "statistical_test": "unknown"
            }
    
    def _calculate_sample_size_ttest(self, effect_size: float, alpha: float, power: float) -> int:
        """Calculate sample size for two-sample t-test."""
        # Using standard power analysis formula
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_beta = stats.norm.ppf(power)
        
        # Cohen's d effect size
        n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
        
        return max(int(math.ceil(n)), 3)  # Minimum of 3 per group
    
    def _validate_group_fields(self, group: Dict[str, Any]) -> bool:
        """Validate that an experimental group has all required fields."""
        return all(field in group and group[field] for field in GROUP_REQUIRED_FIELDS)
    
    def _validate_control_group_fields(self, group: Dict[str, Any]) -> bool:
        """Validate that a control group has all required fields."""
        required_fields = ['type', 'purpose', 'description']
        return all(field in group and group[field] for field in required_fields)
    
    def _generate_design_response(self, state: ExperimentPlanState, next_action: str) -> str:
        """Generate appropriate response based on current state and next action."""
        research_query = state.get('research_query', '')
        objective = state.get('experiment_objective', '')
        variables = state.get('independent_variables', [])
        
        domain_guidance = get_design_domain_guidance(research_query, objective, variables)
        
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        if next_action == "experimental_groups":
            if not experimental_groups:
                return format_design_response(
                    "experimental_groups_needed",
                    {"variables": [v.get('name', '') for v in variables[:3]]}
                )
            else:
                return "Great! Do you have any other experimental conditions to test?"
        
        elif next_action == "control_groups":
            if not control_groups:
                control_suggestions = suggest_control_groups(domain_guidance['domain'], variables)
                return format_design_response(
                    "control_groups_needed",
                    {"suggested_controls": control_suggestions}
                )
            else:
                return "Excellent! Are there any other control conditions needed?"
        
        elif next_action == "sample_size":
            if not sample_size:
                return format_design_response(
                    "sample_size_needed",
                    {"design_complexity": len(experimental_groups) + len(control_groups)}
                )
            else:
                return "Good! Let's refine the sample size calculation."
        
        elif next_action == "refinement":
            validation_results = validate_experimental_design(
                experimental_groups, control_groups, sample_size,
                state.get('independent_variables', []),
                state.get('dependent_variables', [])
            )
            if validation_results['suggestions']:
                return f"Let's refine your experimental design. {validation_results['suggestions'][0]}"
            else:
                return "Let's review and refine your experimental design."
        
        else:
            # Finalization
            design_summary = self._create_design_summary(experimental_groups, control_groups, sample_size)
            return format_design_response(
                "design_complete",
                {"design_summary": design_summary}
            )
    
    def _create_design_summary(self, experimental_groups: List[Dict[str, Any]], 
                              control_groups: List[Dict[str, Any]], 
                              sample_size: Dict[str, Any]) -> str:
        """Create a summary of the experimental design."""
        summary = []
        
        if experimental_groups:
            summary.append(f"Experimental Groups ({len(experimental_groups)}):")
            for group in experimental_groups:
                summary.append(f"  - {group.get('name', 'Unnamed')}")
        
        if control_groups:
            summary.append(f"Control Groups ({len(control_groups)}):")
            for group in control_groups:
                summary.append(f"  - {group.get('type', 'Unknown')} control")
        
        if sample_size:
            power_analysis = sample_size.get('power_analysis', {})
            required_n = power_analysis.get('required_sample_size', 'Unknown')
            summary.append(f"Sample Size: {required_n} per group")
        
        return "\n".join(summary)
    
    def get_design_summary(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get a summary of the current experimental design progress.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Summary dictionary with design details
        """
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        
        validation_results = validate_experimental_design(
            experimental_groups, control_groups, sample_size,
            independent_vars, dependent_vars
        )
        
        return {
            "stage": "experimental_design",
            "experimental_groups": experimental_groups,
            "control_groups": control_groups,
            "sample_size": sample_size,
            "completion_score": validation_results['score'],
            "is_complete": validation_results['is_complete'],
            "missing_elements": validation_results['missing_elements'],
            "suggestions": validation_results['suggestions'],
            "statistical_power": sample_size.get('power_analysis', {}).get('power', 0.8),
            "required_sample_size": sample_size.get('power_analysis', {}).get('required_sample_size', 'Unknown')
        }
    
    def __repr__(self) -> str:
        return f"DesignAgent(stage='{self.stage}', agent_name='{self.agent_name}')" 