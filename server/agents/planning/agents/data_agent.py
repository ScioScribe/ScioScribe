"""
Data Planning & QA Agent for the experiment planning system.

This agent specializes in developing comprehensive data collection plans,
recommending statistical analysis approaches, identifying potential pitfalls,
and creating troubleshooting guides for robust experimental execution.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import random

from .base_agent import BaseAgent
from ..state import ExperimentPlanState, PITFALL_REQUIRED_FIELDS
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.data_prompts import (
    DATA_SYSTEM_PROMPT,
    DATA_COLLECTION_QUESTIONS,
    STATISTICAL_ANALYSIS_QUESTIONS,
    VISUALIZATION_QUESTIONS,
    PITFALL_IDENTIFICATION_QUESTIONS,
    SUCCESS_CRITERIA_QUESTIONS,
    DATA_RESPONSE_TEMPLATES,
    STATISTICAL_TEST_RECOMMENDATIONS,
    VISUALIZATION_RECOMMENDATIONS,
    COMMON_PITFALLS,
    get_data_domain_guidance,
    format_data_response,
    validate_data_plan_completeness,
    generate_troubleshooting_guide
)


class DataAgent(BaseAgent):
    """
    Agent responsible for data collection planning and quality assurance.
    
    This agent guides users through:
    - Developing comprehensive data collection plans
    - Recommending appropriate statistical analysis approaches
    - Suggesting effective visualization strategies
    - Identifying potential experimental pitfalls and mitigation strategies
    - Defining success criteria and expected outcomes
    - Creating troubleshooting guides for common issues
    """
    
    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Data Planning & QA Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        super().__init__(
            agent_name="data_agent",
            stage="data_planning",
            debugger=debugger,
            log_level=log_level
        )
        
        self.logger.info("DataAgent initialized for data planning stage")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to develop data collection and analysis plans.
        
        Analyzes the experimental design and methodology to create comprehensive
        data collection plans, recommend statistical approaches, and identify pitfalls.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with data planning details
        """
        self.logger.info(f"Processing data planning for experiment: {state.get('experiment_id')}")
        
        # Get the latest user input from chat history
        user_input = self._get_latest_user_input(state)
        
        # Get current data planning elements
        data_collection_plan = state.get('data_collection_plan', {})
        data_analysis_plan = state.get('data_analysis_plan', {})
        potential_pitfalls = state.get('potential_pitfalls', [])
        expected_outcomes = state.get('expected_outcomes')
        
        # Get experimental context
        experimental_context = {
            'experimental_groups': state.get('experimental_groups', []),
            'control_groups': state.get('control_groups', []),
            'independent_variables': state.get('independent_variables', []),
            'dependent_variables': state.get('dependent_variables', []),
            'methodology_steps': state.get('methodology_steps', []),
            'materials_equipment': state.get('materials_equipment', [])
        }
        
        # Validate current data planning
        validation_results = validate_data_plan_completeness(
            data_collection_plan, 
            data_analysis_plan, 
            potential_pitfalls
        )
        
        # Get domain guidance
        research_query = state.get('research_query', '')
        domain_guidance = get_data_domain_guidance(research_query, experimental_context)
        
        # Determine what data planning elements are needed
        next_action = self._determine_next_data_action(state, validation_results, domain_guidance)
        
        # Process user input based on current needs
        if next_action == "data_collection":
            updated_state = self._process_data_collection(state, user_input, domain_guidance)
        elif next_action == "statistical_analysis":
            updated_state = self._process_statistical_analysis(state, user_input, domain_guidance)
        elif next_action == "visualization":
            updated_state = self._process_visualization_planning(state, user_input, domain_guidance)
        elif next_action == "pitfalls":
            updated_state = self._process_pitfall_identification(state, user_input, domain_guidance)
        elif next_action == "success_criteria":
            updated_state = self._process_success_criteria(state, user_input, domain_guidance)
        elif next_action == "troubleshooting":
            updated_state = self._process_troubleshooting_guide(state, user_input, domain_guidance)
        elif next_action == "refinement":
            updated_state = self._refine_data_plan(state, user_input, domain_guidance)
        else:
            updated_state = self._finalize_data_plan(state, user_input, domain_guidance)
        
        # Generate agent response
        response = self._generate_data_response(updated_state, next_action, domain_guidance)
        updated_state = add_chat_message(updated_state, "assistant", response)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        self.logger.info(f"Data planning processing complete for action: {next_action}")
        
        return updated_state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions for the user based on current data planning needs.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of questions to ask the user
        """
        # Get current data planning elements
        data_collection_plan = state.get('data_collection_plan', {})
        data_analysis_plan = state.get('data_analysis_plan', {})
        potential_pitfalls = state.get('potential_pitfalls', [])
        
        # Determine what's needed and generate appropriate questions
        questions = []
        
        # Data collection questions
        if not data_collection_plan.get('methods'):
            questions.extend(random.sample(DATA_COLLECTION_QUESTIONS, 3))
        
        # Statistical analysis questions
        elif not data_analysis_plan.get('statistical_tests'):
            questions.extend(random.sample(STATISTICAL_ANALYSIS_QUESTIONS, 3))
        
        # Visualization questions
        elif not data_analysis_plan.get('visualizations'):
            questions.extend(random.sample(VISUALIZATION_QUESTIONS, 2))
        
        # Pitfalls identification questions
        elif len(potential_pitfalls) < 3:
            questions.extend(random.sample(PITFALL_IDENTIFICATION_QUESTIONS, 3))
        
        # Success criteria questions
        elif not state.get('expected_outcomes'):
            questions.extend(random.sample(SUCCESS_CRITERIA_QUESTIONS, 2))
        
        # Default to refinement questions if most elements are present
        else:
            questions.extend([
                "Are there any specific data quality concerns for your experiment?",
                "What contingency plans do you have if data collection issues arise?",
                "How will you validate the reliability of your measurements?"
            ])
        
        # Limit to 5 questions maximum
        return questions[:5]
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the state meets the data planning stage requirements.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Check data collection plan
        data_collection_plan = state.get('data_collection_plan', {})
        if not data_collection_plan.get('methods'):
            missing_requirements.append("Data collection methods must be defined")
        
        if not data_collection_plan.get('timing'):
            missing_requirements.append("Data collection timing must be specified")
        
        if not data_collection_plan.get('formats'):
            missing_requirements.append("Data formats must be specified")
        
        # Check data analysis plan
        data_analysis_plan = state.get('data_analysis_plan', {})
        if not data_analysis_plan.get('statistical_tests'):
            missing_requirements.append("Statistical analysis approach must be defined")
        
        if not data_analysis_plan.get('visualizations'):
            missing_requirements.append("Visualization strategy must be planned")
        
        # Check pitfalls identification
        potential_pitfalls = state.get('potential_pitfalls', [])
        if len(potential_pitfalls) < 3:
            missing_requirements.append("At least 3 potential pitfalls must be identified")
        
        # Validate pitfall structure
        for pitfall in potential_pitfalls:
            if not self._validate_pitfall_fields(pitfall):
                missing_requirements.append("All pitfalls must have complete definitions")
                break
        
        # Check expected outcomes
        if not state.get('expected_outcomes'):
            missing_requirements.append("Expected outcomes must be defined")
        
        # Check for basic quality elements
        if not data_collection_plan.get('quality_control'):
            missing_requirements.append("Quality control measures must be specified")
        
        is_valid = len(missing_requirements) == 0
        
        return is_valid, missing_requirements
    
    def _get_latest_user_input(self, state: ExperimentPlanState) -> str:
        """Extract the latest user input from chat history."""
        chat_history = state.get('chat_history', [])
        
        # Find the most recent user message
        for message in reversed(chat_history):
            if message.get('role') == 'user':
                return message.get('content', '')
        
        return ""
    
    def _determine_next_data_action(self, state: ExperimentPlanState, 
                                   validation_results: Dict[str, Any],
                                   domain_guidance: Dict[str, Any]) -> str:
        """
        Determine the next action needed for data planning.
        
        Args:
            state: Current experiment plan state
            validation_results: Validation results from completeness check
            domain_guidance: Domain-specific guidance
            
        Returns:
            Next action to take
        """
        data_collection_plan = state.get('data_collection_plan', {})
        data_analysis_plan = state.get('data_analysis_plan', {})
        potential_pitfalls = state.get('potential_pitfalls', [])
        expected_outcomes = state.get('expected_outcomes')
        
        # Check in order of priority
        if not data_collection_plan.get('methods'):
            return "data_collection"
        
        if not data_analysis_plan.get('statistical_tests'):
            return "statistical_analysis"
        
        if not data_analysis_plan.get('visualizations'):
            return "visualization"
        
        if len(potential_pitfalls) < 3:
            return "pitfalls"
        
        if not expected_outcomes:
            return "success_criteria"
        
        # Check if troubleshooting guide is needed
        if not self._has_troubleshooting_guide(state):
            return "troubleshooting"
        
        # If validation score is low, focus on refinement
        if validation_results.get('score', 0) < 80:
            return "refinement"
        
        return "finalize"
    
    def _process_data_collection(self, state: ExperimentPlanState, 
                               user_input: str, 
                               domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input for data collection planning."""
        current_plan = state.get('data_collection_plan', {})
        
        # Extract data collection information from user input
        if user_input.strip():
            # Parse user input for data collection methods
            methods = self._extract_data_collection_methods(user_input)
            timing = self._extract_data_collection_timing(user_input)
            formats = self._extract_data_formats(user_input)
            storage = self._extract_storage_methods(user_input)
            quality_control = self._extract_quality_control(user_input)
            
            # Update data collection plan
            updated_plan = {
                'methods': methods or current_plan.get('methods', []),
                'timing': timing or current_plan.get('timing', 'single_timepoint'),
                'formats': formats or current_plan.get('formats', []),
                'storage': storage or current_plan.get('storage', 'digital'),
                'quality_control': quality_control or current_plan.get('quality_control', [])
            }
            
            state['data_collection_plan'] = updated_plan
        
        return state
    
    def _process_statistical_analysis(self, state: ExperimentPlanState, 
                                    user_input: str, 
                                    domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input for statistical analysis planning."""
        current_plan = state.get('data_analysis_plan', {})
        
        # Get experimental context for statistical recommendations
        experimental_groups = state.get('experimental_groups', [])
        dependent_variables = state.get('dependent_variables', [])
        
        # Extract or suggest statistical tests
        statistical_tests = self._extract_statistical_tests(user_input, experimental_groups, dependent_variables)
        
        # Update data analysis plan
        updated_plan = current_plan.copy()
        updated_plan['statistical_tests'] = statistical_tests or current_plan.get('statistical_tests', [])
        
        # Add software recommendations
        if not updated_plan.get('software'):
            updated_plan['software'] = ['R', 'Python', 'GraphPad Prism']
        
        state['data_analysis_plan'] = updated_plan
        
        return state
    
    def _process_visualization_planning(self, state: ExperimentPlanState, 
                                      user_input: str, 
                                      domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input for visualization planning."""
        current_plan = state.get('data_analysis_plan', {})
        
        # Get context for visualization recommendations
        experimental_groups = state.get('experimental_groups', [])
        dependent_variables = state.get('dependent_variables', [])
        
        # Extract or suggest visualizations
        visualizations = self._extract_visualizations(user_input, experimental_groups, dependent_variables)
        
        # Update data analysis plan
        updated_plan = current_plan.copy()
        updated_plan['visualizations'] = visualizations or current_plan.get('visualizations', [])
        
        state['data_analysis_plan'] = updated_plan
        
        return state
    
    def _process_pitfall_identification(self, state: ExperimentPlanState, 
                                      user_input: str, 
                                      domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input for pitfall identification."""
        current_pitfalls = state.get('potential_pitfalls', [])
        
        # Extract pitfalls from user input or use domain guidance
        if user_input.strip():
            new_pitfalls = self._extract_pitfalls(user_input)
        else:
            new_pitfalls = domain_guidance.get('pitfalls', [])
        
        # Combine with existing pitfalls
        all_pitfalls = current_pitfalls + new_pitfalls
        
        # Remove duplicates based on issue description
        unique_pitfalls = []
        seen_issues = set()
        for pitfall in all_pitfalls:
            issue = pitfall.get('issue', '')
            if issue not in seen_issues:
                unique_pitfalls.append(pitfall)
                seen_issues.add(issue)
        
        state['potential_pitfalls'] = unique_pitfalls
        
        return state
    
    def _process_success_criteria(self, state: ExperimentPlanState, 
                                user_input: str, 
                                domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input for success criteria definition."""
        if user_input.strip():
            expected_outcomes = user_input.strip()
        else:
            # Generate default success criteria
            success_criteria = domain_guidance.get('success_criteria', [])
            expected_outcomes = '\n'.join(success_criteria)
        
        state['expected_outcomes'] = expected_outcomes
        
        return state
    
    def _process_troubleshooting_guide(self, state: ExperimentPlanState, 
                                     user_input: str, 
                                     domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Process user input for troubleshooting guide creation."""
        methodology_steps = state.get('methodology_steps', [])
        potential_pitfalls = state.get('potential_pitfalls', [])
        
        # Generate troubleshooting guide
        troubleshooting_guide = generate_troubleshooting_guide(methodology_steps, potential_pitfalls)
        
        # Store in data analysis plan
        data_analysis_plan = state.get('data_analysis_plan', {})
        data_analysis_plan['troubleshooting_guide'] = troubleshooting_guide
        state['data_analysis_plan'] = data_analysis_plan
        
        return state
    
    def _refine_data_plan(self, state: ExperimentPlanState, 
                         user_input: str, 
                         domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Refine the data plan based on user feedback."""
        # This would involve updating specific elements based on user input
        # For now, just log the refinement request
        self.logger.info(f"Refining data plan based on user input: {user_input[:100]}...")
        
        return state
    
    def _finalize_data_plan(self, state: ExperimentPlanState, 
                          user_input: str, 
                          domain_guidance: Dict[str, Any]) -> ExperimentPlanState:
        """Finalize the data plan."""
        self.logger.info("Finalizing data plan")
        
        # Ensure all required elements are present
        if not state.get('data_collection_plan'):
            state['data_collection_plan'] = {
                'methods': ['Standardized measurement protocols'],
                'timing': 'single_timepoint',
                'formats': ['numerical'],
                'storage': 'digital',
                'quality_control': ['Calibration checks']
            }
        
        if not state.get('data_analysis_plan'):
            state['data_analysis_plan'] = {
                'statistical_tests': ['Descriptive statistics', 'Appropriate significance tests'],
                'visualizations': ['Bar charts', 'Scatter plots'],
                'software': ['R', 'Python', 'GraphPad Prism']
            }
        
        return state
    
    def _generate_data_response(self, state: ExperimentPlanState, 
                              next_action: str, 
                              domain_guidance: Dict[str, Any]) -> str:
        """Generate a conversational response based on the current action."""
        try:
            if next_action == "data_collection":
                context = {
                    'context': 'Based on your experimental design, let\'s plan your data collection approach.',
                    'specific_question': random.choice(DATA_COLLECTION_QUESTIONS)
                }
                return format_data_response("data_collection_needed", context)
            
            elif next_action == "statistical_analysis":
                experimental_groups = state.get('experimental_groups', [])
                context = {
                    'design_context': f'You have {len(experimental_groups)} experimental groups.',
                    'analysis_question': random.choice(STATISTICAL_ANALYSIS_QUESTIONS)
                }
                return format_data_response("statistical_analysis_needed", context)
            
            elif next_action == "visualization":
                dependent_vars = state.get('dependent_variables', [])
                context = {
                    'data_context': f'You\'ll be measuring {len(dependent_vars)} outcome variables.',
                    'visualization_question': random.choice(VISUALIZATION_QUESTIONS)
                }
                return format_data_response("visualization_planning", context)
            
            elif next_action == "pitfalls":
                context = {
                    'experimental_context': 'Based on your methodology, let\'s identify potential issues.',
                    'pitfall_question': random.choice(PITFALL_IDENTIFICATION_QUESTIONS)
                }
                return format_data_response("pitfall_identification", context)
            
            elif next_action == "success_criteria":
                objective = state.get('experiment_objective', '')
                context = {
                    'objective_context': f'Your objective: {objective}',
                    'success_question': random.choice(SUCCESS_CRITERIA_QUESTIONS)
                }
                return format_data_response("success_criteria", context)
            
            elif next_action == "troubleshooting":
                context = {
                    'protocol_context': 'Based on your methodology and identified pitfalls.',
                    'troubleshooting_question': 'What specific issues do you want to prepare for?'
                }
                return format_data_response("troubleshooting_guide", context)
            
            elif next_action == "finalize":
                # Generate completion summary
                data_collection_plan = state.get('data_collection_plan', {})
                data_analysis_plan = state.get('data_analysis_plan', {})
                potential_pitfalls = state.get('potential_pitfalls', [])
                
                context = {
                    'data_plan_summary': self._create_data_plan_summary(state),
                    'collection_methods_count': len(data_collection_plan.get('methods', [])),
                    'statistical_tests_count': len(data_analysis_plan.get('statistical_tests', [])),
                    'pitfalls_count': len(potential_pitfalls)
                }
                return format_data_response("data_planning_complete", context)
            
            else:
                return "Let's continue developing your data collection and analysis plan. What specific aspect would you like to focus on?"
        
        except Exception as e:
            self.logger.error(f"Error generating data response: {e}")
            return "I'm ready to help you plan your data collection and analysis approach. What would you like to discuss?"
    
    def _create_data_plan_summary(self, state: ExperimentPlanState) -> str:
        """Create a summary of the data plan."""
        summary_parts = []
        
        # Data collection summary
        data_collection_plan = state.get('data_collection_plan', {})
        if data_collection_plan.get('methods'):
            summary_parts.append(f"Data Collection: {', '.join(data_collection_plan['methods'])}")
        
        # Statistical analysis summary
        data_analysis_plan = state.get('data_analysis_plan', {})
        if data_analysis_plan.get('statistical_tests'):
            summary_parts.append(f"Statistical Tests: {', '.join(data_analysis_plan['statistical_tests'])}")
        
        # Visualization summary
        if data_analysis_plan.get('visualizations'):
            summary_parts.append(f"Visualizations: {', '.join(data_analysis_plan['visualizations'])}")
        
        # Pitfalls summary
        potential_pitfalls = state.get('potential_pitfalls', [])
        if potential_pitfalls:
            pitfall_issues = [p.get('issue', '') for p in potential_pitfalls[:3]]
            summary_parts.append(f"Key Pitfalls: {', '.join(pitfall_issues)}")
        
        return '\n'.join(summary_parts) if summary_parts else "Data plan in development"
    
    def _has_troubleshooting_guide(self, state: ExperimentPlanState) -> bool:
        """Check if a troubleshooting guide exists."""
        data_analysis_plan = state.get('data_analysis_plan', {})
        return 'troubleshooting_guide' in data_analysis_plan
    
    def _validate_pitfall_fields(self, pitfall: Dict[str, Any]) -> bool:
        """Validate that a pitfall has all required fields."""
        required_fields = ['issue', 'likelihood', 'mitigation']
        return all(field in pitfall and pitfall[field] for field in required_fields)
    
    def _extract_data_collection_methods(self, user_input: str) -> List[str]:
        """Extract data collection methods from user input."""
        methods = []
        
        # Simple keyword-based extraction
        if 'manual' in user_input.lower():
            methods.append('Manual data recording')
        if 'automated' in user_input.lower():
            methods.append('Automated data collection')
        if 'instrument' in user_input.lower() or 'equipment' in user_input.lower():
            methods.append('Instrument-based measurements')
        if 'observation' in user_input.lower():
            methods.append('Direct observation')
        
        return methods or ['Standardized measurement protocols']
    
    def _extract_data_collection_timing(self, user_input: str) -> str:
        """Extract data collection timing from user input."""
        if 'time' in user_input.lower() or 'multiple' in user_input.lower():
            return 'multiple_timepoints'
        return 'single_timepoint'
    
    def _extract_data_formats(self, user_input: str) -> List[str]:
        """Extract data formats from user input."""
        formats = []
        
        if 'number' in user_input.lower() or 'quantitative' in user_input.lower():
            formats.append('numerical')
        if 'category' in user_input.lower() or 'qualitative' in user_input.lower():
            formats.append('categorical')
        if 'binary' in user_input.lower() or 'yes/no' in user_input.lower():
            formats.append('binary')
        
        return formats or ['numerical']
    
    def _extract_storage_methods(self, user_input: str) -> str:
        """Extract storage methods from user input."""
        if 'cloud' in user_input.lower():
            return 'cloud'
        if 'local' in user_input.lower():
            return 'local'
        return 'digital'
    
    def _extract_quality_control(self, user_input: str) -> List[str]:
        """Extract quality control measures from user input."""
        qc_measures = []
        
        if 'calibration' in user_input.lower():
            qc_measures.append('Instrument calibration')
        if 'replicate' in user_input.lower():
            qc_measures.append('Technical replicates')
        if 'control' in user_input.lower():
            qc_measures.append('Quality control samples')
        
        return qc_measures or ['Standard quality control measures']
    
    def _extract_statistical_tests(self, user_input: str, 
                                 experimental_groups: List[Dict[str, Any]], 
                                 dependent_variables: List[Dict[str, Any]]) -> List[str]:
        """Extract or suggest statistical tests based on experimental design."""
        tests = []
        
        # Basic recommendations based on experimental design
        if len(experimental_groups) == 2:
            tests.append('Two-sample t-test')
        elif len(experimental_groups) > 2:
            tests.append('One-way ANOVA')
        
        if len(dependent_variables) > 1:
            tests.append('Correlation analysis')
        
        # Add common tests
        tests.extend(['Descriptive statistics', 'Normality tests'])
        
        return tests
    
    def _extract_visualizations(self, user_input: str, 
                              experimental_groups: List[Dict[str, Any]], 
                              dependent_variables: List[Dict[str, Any]]) -> List[str]:
        """Extract or suggest visualizations based on experimental design."""
        visualizations = []
        
        # Basic recommendations based on experimental design
        if len(experimental_groups) >= 2:
            visualizations.extend(['Box plots', 'Bar charts with error bars'])
        
        if len(dependent_variables) > 1:
            visualizations.append('Scatter plots')
        
        # Add common visualizations
        visualizations.extend(['Histograms', 'Summary statistics tables'])
        
        return visualizations
    
    def _extract_pitfalls(self, user_input: str) -> List[Dict[str, Any]]:
        """Extract pitfalls from user input."""
        pitfalls = []
        
        # Simple extraction - in practice, this would be more sophisticated
        if 'contamination' in user_input.lower():
            pitfalls.append(COMMON_PITFALLS['contamination'])
        
        if 'sample size' in user_input.lower():
            pitfalls.append(COMMON_PITFALLS['sample_size'])
        
        if 'equipment' in user_input.lower() or 'instrument' in user_input.lower():
            pitfalls.append(COMMON_PITFALLS['equipment_failure'])
        
        # Add batch effects as a common pitfall
        pitfalls.append(COMMON_PITFALLS['batch_effects'])
        
        return pitfalls 