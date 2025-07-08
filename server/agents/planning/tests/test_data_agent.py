"""
Tests for the DataAgent class.

This module tests the data planning and QA agent functionality including
data collection planning, statistical analysis recommendations, visualization
strategies, and pitfall identification.
"""

import pytest
from unittest.mock import Mock, patch

from ..agents.data_agent import DataAgent
from ..state import ExperimentPlanState
from ..factory import create_new_experiment_state, add_chat_message


class TestDataAgentInitialization:
    """Test DataAgent initialization."""
    
    def test_valid_initialization(self):
        """Test that DataAgent initializes correctly."""
        agent = DataAgent()
        
        assert agent.agent_name == "data_agent"
        assert agent.stage == "data_planning"
        assert agent.logger is not None
        assert agent.debugger is not None
    
    def test_initialization_with_custom_params(self, mock_debugger):
        """Test initialization with custom parameters."""
        agent = DataAgent(debugger=mock_debugger, log_level="DEBUG")
        
        assert agent.debugger == mock_debugger
        assert agent.logger.level == 10  # DEBUG level


class TestDataAgentStateProcessing:
    """Test DataAgent state processing functionality."""
    
    def test_process_state_data_collection(self, data_ready_state):
        """Test processing state for data collection planning."""
        agent = DataAgent()
        
        # Add user input for data collection
        user_input = """
        I need to collect numerical data using automated instruments.
        I'll be taking measurements at multiple time points.
        Data will be stored digitally with quality control checks.
        """
        
        state_with_input = add_chat_message(data_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'data_collection_plan' in result
        assert 'updated_at' in result
        
        # Check that response was added to chat history
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_statistical_analysis(self, data_ready_state):
        """Test processing state for statistical analysis planning."""
        agent = DataAgent()
        
        # Add data collection plan first
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        
        # Add user input for statistical analysis
        user_input = """
        I want to compare means between my experimental groups.
        I'll check normality first and use appropriate tests.
        I'm planning to use R for the analysis.
        """
        
        state_with_input = add_chat_message(data_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'data_analysis_plan' in result
        assert 'updated_at' in result
        
        # Check response
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_visualization_planning(self, data_ready_state):
        """Test processing state for visualization planning."""
        agent = DataAgent()
        
        # Add prerequisite data plans
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test', 'ANOVA'],
            'software': ['R', 'Python']
        }
        
        # Add user input for visualization
        user_input = """
        I want to show the differences between groups clearly.
        Box plots and bar charts would be good.
        I need publication-ready figures.
        """
        
        state_with_input = add_chat_message(data_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'data_analysis_plan' in result
        assert 'visualizations' in result['data_analysis_plan']
        assert 'updated_at' in result
    
    def test_process_state_pitfall_identification(self, data_ready_state):
        """Test processing state for pitfall identification."""
        agent = DataAgent()
        
        # Add prerequisite plans
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        
        # Add user input for pitfalls
        user_input = """
        I'm worried about contamination between samples.
        Equipment might fail during the experiment.
        Sample size might be too small for reliable results.
        """
        
        state_with_input = add_chat_message(data_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'potential_pitfalls' in result
        assert len(result['potential_pitfalls']) > 0
        assert 'updated_at' in result
    
    def test_process_state_success_criteria(self, data_ready_state):
        """Test processing state for success criteria definition."""
        agent = DataAgent()
        
        # Add all prerequisite plans
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'Contamination', 'likelihood': 'medium', 'mitigation': 'Use sterile technique'},
            {'issue': 'Equipment failure', 'likelihood': 'low', 'mitigation': 'Have backup equipment'},
            {'issue': 'Small sample size', 'likelihood': 'high', 'mitigation': 'Increase n'}
        ]
        
        # Add user input for success criteria
        user_input = """
        Success means detecting a 20% difference between groups.
        All quality controls should pass.
        Results should be reproducible.
        """
        
        state_with_input = add_chat_message(data_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'expected_outcomes' in result
        assert result['expected_outcomes'].strip() != ""
        assert 'updated_at' in result
    
    def test_process_state_troubleshooting(self, data_complete_state):
        """Test processing state for troubleshooting guide creation."""
        agent = DataAgent()
        
        state_with_input = add_chat_message(
            data_complete_state, 
            "user", 
            "I want to create a troubleshooting guide for common issues"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'data_analysis_plan' in result
        assert 'troubleshooting_guide' in result['data_analysis_plan']
        assert 'updated_at' in result
    
    def test_process_state_no_methodology(self, minimal_state):
        """Test processing state without experimental design."""
        agent = DataAgent()
        
        state_with_input = add_chat_message(
            minimal_state, 
            "user", 
            "How do I plan my data collection?"
        )
        
        result = agent.process_state(state_with_input)
        
        # Should still process and respond
        assert 'updated_at' in result
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0


class TestDataAgentQuestionGeneration:
    """Test DataAgent question generation functionality."""
    
    def test_generate_questions_data_collection(self, data_ready_state):
        """Test question generation for data collection planning."""
        agent = DataAgent()
        
        questions = agent.generate_questions(data_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 5  # Should limit to 5 questions
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 0 for q in questions)
    
    def test_generate_questions_statistical_analysis_focus(self, data_ready_state):
        """Test question generation when statistical analysis is needed."""
        agent = DataAgent()
        
        # Add data collection plan but no statistical analysis
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        
        questions = agent.generate_questions(data_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about statistical analysis
        question_text = ' '.join(questions).lower()
        assert 'statistical' in question_text or 'analysis' in question_text or 'test' in question_text
    
    def test_generate_questions_visualization_focus(self, data_ready_state):
        """Test question generation when visualization is needed."""
        agent = DataAgent()
        
        # Add data collection and statistical analysis but no visualization
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'software': ['R']
        }
        
        questions = agent.generate_questions(data_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about visualization
        question_text = ' '.join(questions).lower()
        assert 'visualization' in question_text or 'chart' in question_text or 'graph' in question_text
    
    def test_generate_questions_pitfalls_focus(self, data_ready_state):
        """Test question generation when pitfalls identification is needed."""
        agent = DataAgent()
        
        # Add most elements but few pitfalls
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'One pitfall', 'likelihood': 'medium', 'mitigation': 'Some solution'}
        ]
        
        questions = agent.generate_questions(data_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about pitfalls
        question_text = ' '.join(questions).lower()
        assert 'pitfall' in question_text or 'issue' in question_text or 'problem' in question_text
    
    def test_generate_questions_success_criteria_focus(self, data_ready_state):
        """Test question generation when success criteria are needed."""
        agent = DataAgent()
        
        # Add all elements except success criteria
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'Pitfall 1', 'likelihood': 'medium', 'mitigation': 'Solution 1'},
            {'issue': 'Pitfall 2', 'likelihood': 'low', 'mitigation': 'Solution 2'},
            {'issue': 'Pitfall 3', 'likelihood': 'high', 'mitigation': 'Solution 3'}
        ]
        
        questions = agent.generate_questions(data_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about success criteria
        question_text = ' '.join(questions).lower()
        assert 'success' in question_text or 'outcome' in question_text or 'result' in question_text
    
    def test_generate_questions_refinement_stage(self, data_complete_state):
        """Test question generation for refinement stage."""
        agent = DataAgent()
        
        questions = agent.generate_questions(data_complete_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about refinement topics
        question_text = ' '.join(questions).lower()
        assert 'quality' in question_text or 'contingency' in question_text or 'validate' in question_text


class TestDataAgentValidation:
    """Test DataAgent validation functionality."""
    
    def test_validate_stage_requirements_incomplete(self, data_ready_state):
        """Test validation with incomplete stage requirements."""
        agent = DataAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_ready_state)
        
        assert is_valid is False
        assert isinstance(missing_requirements, list)
        assert len(missing_requirements) > 0
        assert any('data collection' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_only_data_collection(self, data_ready_state):
        """Test validation with only data collection plan."""
        agent = DataAgent()
        
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_ready_state)
        
        assert is_valid is False
        assert any('statistical analysis' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_incomplete_data_collection(self, data_ready_state):
        """Test validation with incomplete data collection plan."""
        agent = DataAgent()
        
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement']
            # Missing timing, formats, storage, quality_control
        }
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_ready_state)
        
        assert is_valid is False
        assert any('timing' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_incomplete_pitfalls(self, data_ready_state):
        """Test validation with insufficient pitfalls."""
        agent = DataAgent()
        
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'Only one pitfall', 'likelihood': 'medium', 'mitigation': 'Some solution'}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_ready_state)
        
        assert is_valid is False
        assert any('3 potential pitfalls' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_incomplete_pitfall_fields(self, data_ready_state):
        """Test validation with incomplete pitfall fields."""
        agent = DataAgent()
        
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'Pitfall 1'},  # Missing likelihood and mitigation
            {'issue': 'Pitfall 2', 'likelihood': 'medium'},  # Missing mitigation
            {'issue': 'Pitfall 3', 'likelihood': 'high', 'mitigation': 'Solution 3'}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_ready_state)
        
        assert is_valid is False
        assert any('complete definitions' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_missing_expected_outcomes(self, data_ready_state):
        """Test validation with missing expected outcomes."""
        agent = DataAgent()
        
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'visualizations': ['box plots'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'Pitfall 1', 'likelihood': 'medium', 'mitigation': 'Solution 1'},
            {'issue': 'Pitfall 2', 'likelihood': 'low', 'mitigation': 'Solution 2'},
            {'issue': 'Pitfall 3', 'likelihood': 'high', 'mitigation': 'Solution 3'}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_ready_state)
        
        assert any('expected outcomes' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_complete(self, data_complete_state):
        """Test validation with complete stage requirements."""
        agent = DataAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(data_complete_state)
        
        # Should be valid or close to valid
        assert isinstance(is_valid, bool)
        assert isinstance(missing_requirements, list)
        
        # With properly complete state, should have fewer missing requirements
        if not is_valid:
            assert len(missing_requirements) < 3  # Should be mostly complete


class TestDataAgentUtilityMethods:
    """Test DataAgent utility methods."""
    
    def test_get_latest_user_input(self, data_ready_state):
        """Test extracting latest user input from chat history."""
        agent = DataAgent()
        
        # Add multiple messages
        state = add_chat_message(data_ready_state, "user", "First message")
        state = add_chat_message(state, "assistant", "Response")
        state = add_chat_message(state, "user", "Second message about data collection")
        
        latest_input = agent._get_latest_user_input(state)
        
        assert latest_input == "Second message about data collection"
    
    def test_get_latest_user_input_no_messages(self, data_ready_state):
        """Test extracting user input when no messages exist."""
        agent = DataAgent()
        
        latest_input = agent._get_latest_user_input(data_ready_state)
        
        assert latest_input == ""
    
    def test_determine_next_data_action(self, data_ready_state):
        """Test determining next data planning action."""
        agent = DataAgent()
        
        # Mock validation results
        validation_results = {'score': 30, 'is_complete': False}
        domain_guidance = {'domain': 'general'}
        
        # Test with no data collection plan
        action = agent._determine_next_data_action(data_ready_state, validation_results, domain_guidance)
        assert action == "data_collection"
        
        # Test with data collection but no statistical analysis
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        action = agent._determine_next_data_action(data_ready_state, validation_results, domain_guidance)
        assert action == "statistical_analysis"
        
        # Test with both but no visualization
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'software': ['R']
        }
        action = agent._determine_next_data_action(data_ready_state, validation_results, domain_guidance)
        assert action == "visualization"
    
    def test_extract_data_collection_methods(self, data_ready_state):
        """Test extracting data collection methods from user input."""
        agent = DataAgent()
        
        user_input = "I will use automated instruments for manual recording of observations"
        methods = agent._extract_data_collection_methods(user_input)
        
        assert isinstance(methods, list)
        assert len(methods) > 0
        assert any('automated' in method.lower() for method in methods)
        assert any('manual' in method.lower() for method in methods)
    
    def test_extract_statistical_tests(self, data_ready_state):
        """Test extracting statistical tests based on experimental design."""
        agent = DataAgent()
        
        experimental_groups = [
            {'name': 'Control', 'description': 'Control group'},
            {'name': 'Treatment', 'description': 'Treatment group'}
        ]
        dependent_variables = [
            {'name': 'Response', 'type': 'continuous', 'units': 'units'}
        ]
        
        tests = agent._extract_statistical_tests("", experimental_groups, dependent_variables)
        
        assert isinstance(tests, list)
        assert len(tests) > 0
        assert any('t-test' in test.lower() for test in tests)
    
    def test_extract_visualizations(self, data_ready_state):
        """Test extracting visualizations based on experimental design."""
        agent = DataAgent()
        
        experimental_groups = [
            {'name': 'Control', 'description': 'Control group'},
            {'name': 'Treatment', 'description': 'Treatment group'}
        ]
        dependent_variables = [
            {'name': 'Response', 'type': 'continuous', 'units': 'units'}
        ]
        
        visualizations = agent._extract_visualizations("", experimental_groups, dependent_variables)
        
        assert isinstance(visualizations, list)
        assert len(visualizations) > 0
        assert any('box' in viz.lower() or 'bar' in viz.lower() for viz in visualizations)
    
    def test_extract_pitfalls(self, data_ready_state):
        """Test extracting pitfalls from user input."""
        agent = DataAgent()
        
        user_input = "I'm worried about contamination and equipment failure"
        pitfalls = agent._extract_pitfalls(user_input)
        
        assert isinstance(pitfalls, list)
        assert len(pitfalls) > 0
        
        # Check that pitfalls have required fields
        for pitfall in pitfalls:
            assert 'issue' in pitfall
            assert 'likelihood' in pitfall
            assert 'mitigation' in pitfall
    
    def test_validate_pitfall_fields(self, data_ready_state):
        """Test validating pitfall field completeness."""
        agent = DataAgent()
        
        # Complete pitfall
        complete_pitfall = {
            'issue': 'Contamination risk',
            'likelihood': 'medium',
            'mitigation': 'Use sterile technique'
        }
        assert agent._validate_pitfall_fields(complete_pitfall) is True
        
        # Incomplete pitfall
        incomplete_pitfall = {
            'issue': 'Contamination risk'
            # Missing likelihood and mitigation
        }
        assert agent._validate_pitfall_fields(incomplete_pitfall) is False
    
    def test_create_data_plan_summary(self, data_ready_state):
        """Test creating data plan summary."""
        agent = DataAgent()
        
        # Add complete data plans
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test', 'ANOVA'],
            'visualizations': ['box plots', 'bar charts'],
            'software': ['R']
        }
        data_ready_state['potential_pitfalls'] = [
            {'issue': 'Contamination', 'likelihood': 'medium', 'mitigation': 'Sterile technique'},
            {'issue': 'Equipment failure', 'likelihood': 'low', 'mitigation': 'Backup equipment'}
        ]
        
        summary = agent._create_data_plan_summary(data_ready_state)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert 'Data Collection' in summary
        assert 'Statistical Tests' in summary
        assert 'Visualizations' in summary
    
    def test_has_troubleshooting_guide(self, data_ready_state):
        """Test checking for troubleshooting guide existence."""
        agent = DataAgent()
        
        # Without troubleshooting guide
        assert agent._has_troubleshooting_guide(data_ready_state) is False
        
        # With troubleshooting guide
        data_ready_state['data_analysis_plan'] = {
            'troubleshooting_guide': [{'issue': 'Problem', 'solution': 'Fix it'}]
        }
        assert agent._has_troubleshooting_guide(data_ready_state) is True


class TestDataAgentResponseGeneration:
    """Test DataAgent response generation functionality."""
    
    def test_generate_data_response_data_collection(self, data_ready_state):
        """Test generating response for data collection stage."""
        agent = DataAgent()
        
        response = agent._generate_data_response(data_ready_state, "data_collection", {})
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'data collection' in response.lower()
    
    def test_generate_data_response_statistical_analysis(self, data_ready_state):
        """Test generating response for statistical analysis stage."""
        agent = DataAgent()
        
        data_ready_state['experimental_groups'] = [
            {'name': 'Control', 'description': 'Control group'},
            {'name': 'Treatment', 'description': 'Treatment group'}
        ]
        
        response = agent._generate_data_response(data_ready_state, "statistical_analysis", {})
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'statistical' in response.lower()
    
    def test_generate_data_response_visualization(self, data_ready_state):
        """Test generating response for visualization stage."""
        agent = DataAgent()
        
        data_ready_state['dependent_variables'] = [
            {'name': 'Response', 'type': 'continuous', 'units': 'units'}
        ]
        
        response = agent._generate_data_response(data_ready_state, "visualization", {})
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'visualiz' in response.lower()
    
    def test_generate_data_response_completion(self, data_complete_state):
        """Test generating response for completion stage."""
        agent = DataAgent()
        
        response = agent._generate_data_response(data_complete_state, "finalize", {})
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'complete' in response.lower()


class TestDataAgentIntegration:
    """Test DataAgent integration workflows."""
    
    def test_full_data_planning_workflow(self, data_ready_state):
        """Test complete data planning workflow from start to finish."""
        agent = DataAgent()
        
        # Stage 1: Data collection planning
        user_input_1 = "I need automated data collection with quality controls"
        state_1 = add_chat_message(data_ready_state, "user", user_input_1)
        result_1 = agent.process_state(state_1)
        
        assert 'data_collection_plan' in result_1
        
        # Stage 2: Statistical analysis planning
        user_input_2 = "I want to compare groups using t-tests"
        state_2 = add_chat_message(result_1, "user", user_input_2)
        result_2 = agent.process_state(state_2)
        
        assert 'data_analysis_plan' in result_2
        assert 'statistical_tests' in result_2['data_analysis_plan']
        
        # Stage 3: Visualization planning
        user_input_3 = "I need box plots and bar charts"
        state_3 = add_chat_message(result_2, "user", user_input_3)
        result_3 = agent.process_state(state_3)
        
        assert 'visualizations' in result_3['data_analysis_plan']
        
        # Stage 4: Pitfall identification
        user_input_4 = "I'm worried about contamination, equipment failure, and small sample size"
        state_4 = add_chat_message(result_3, "user", user_input_4)
        result_4 = agent.process_state(state_4)
        
        assert 'potential_pitfalls' in result_4
        assert len(result_4['potential_pitfalls']) >= 3
        
        # Stage 5: Success criteria
        user_input_5 = "Success means detecting significant differences with good quality control"
        state_5 = add_chat_message(result_4, "user", user_input_5)
        result_5 = agent.process_state(state_5)
        
        assert 'expected_outcomes' in result_5
        
        # Final validation
        is_valid, missing = agent.validate_stage_requirements(result_5)
        assert len(missing) <= 2  # Should be mostly complete
    
    def test_error_handling_workflow(self, invalid_state):
        """Test error handling in data planning workflow."""
        agent = DataAgent()
        
        # Test with invalid state
        result = agent.process_state(invalid_state)
        
        # Should not crash and should return a state
        assert isinstance(result, dict)
        assert 'updated_at' in result
    
    def test_progressive_data_development(self, data_ready_state):
        """Test progressive development of data plan."""
        agent = DataAgent()
        
        # Initial state - should focus on data collection
        questions_1 = agent.generate_questions(data_ready_state)
        assert any('data' in q.lower() for q in questions_1)
        
        # Add data collection plan
        data_ready_state['data_collection_plan'] = {
            'methods': ['Automated measurement'],
            'timing': 'single_timepoint',
            'formats': ['numerical'],
            'storage': 'digital',
            'quality_control': ['Calibration checks']
        }
        
        # Should now focus on statistical analysis
        questions_2 = agent.generate_questions(data_ready_state)
        assert any('statistical' in q.lower() or 'analysis' in q.lower() for q in questions_2)
        
        # Add statistical analysis plan
        data_ready_state['data_analysis_plan'] = {
            'statistical_tests': ['t-test'],
            'software': ['R']
        }
        
        # Should now focus on visualization
        questions_3 = agent.generate_questions(data_ready_state)
        assert any('visualiz' in q.lower() or 'chart' in q.lower() for q in questions_3)
    
    def test_state_consistency_through_processing(self, data_ready_state):
        """Test that state remains consistent through processing."""
        agent = DataAgent()
        
        original_experiment_id = data_ready_state['experiment_id']
        original_research_query = data_ready_state['research_query']
        
        # Process through multiple stages
        user_input = "I need comprehensive data planning"
        state = add_chat_message(data_ready_state, "user", user_input)
        
        result = agent.process_state(state)
        
        # Core state should remain consistent
        assert result['experiment_id'] == original_experiment_id
        assert result['research_query'] == original_research_query
        assert 'updated_at' in result
        assert result['updated_at'] is not None
        
        # Chat history should be preserved and extended
        assert len(result['chat_history']) > len(data_ready_state.get('chat_history', []))


# Test fixtures
@pytest.fixture
def data_ready_state(variables_complete_state):
    """Create a state ready for data planning."""
    state = variables_complete_state.copy()
    
    # Add experimental design elements
    state.update({
        'experimental_groups': [
            {'name': 'Control', 'description': 'Buffer only', 'conditions': 'pH 7.0'},
            {'name': 'Treatment', 'description': 'With protein', 'conditions': 'pH 7.0 + protein'}
        ],
        'control_groups': [
            {'type': 'negative', 'purpose': 'Baseline measurement', 'description': 'Buffer only'},
            {'type': 'positive', 'purpose': 'Known response', 'description': 'Standard protein'}
        ],
        'sample_size': {
            'biological_replicates': 3,
            'technical_replicates': 3,
            'power_analysis': {'effect_size': 0.5, 'power': 0.8, 'alpha': 0.05}
        }
    })
    
    # Add methodology elements
    state['methodology_steps'] = [
        {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'},
        {'step_number': 2, 'description': 'Add reagent', 'parameters': '1 mL', 'duration': '5 min'},
        {'step_number': 3, 'description': 'Incubate', 'parameters': '37°C', 'duration': '30 min'},
        {'step_number': 4, 'description': 'Measure', 'parameters': '405 nm', 'duration': '5 min'}
    ]
    
    state['materials_equipment'] = [
        {'name': 'Reagent A', 'type': 'chemical', 'quantity': '100 mL', 'specifications': 'High purity'},
        {'name': 'Spectrophotometer', 'type': 'equipment', 'quantity': '1', 'specifications': 'UV-Vis'}
    ]
    
    # Set current stage to data planning
    state['current_stage'] = 'data_planning'
    state['completed_stages'] = ['objective_setting', 'variable_identification', 'experimental_design', 'methodology_protocol']
    
    return state


@pytest.fixture
def data_complete_state(data_ready_state):
    """Create a state with complete data planning."""
    state = data_ready_state.copy()
    
    # Add complete data collection plan
    state['data_collection_plan'] = {
        'methods': ['Automated measurement', 'Quality control checks'],
        'timing': 'single_timepoint',
        'formats': ['numerical', 'categorical'],
        'storage': 'digital',
        'quality_control': ['Instrument calibration', 'Technical replicates']
    }
    
    # Add complete data analysis plan
    state['data_analysis_plan'] = {
        'statistical_tests': ['Two-sample t-test', 'Normality tests', 'Descriptive statistics'],
        'visualizations': ['Box plots', 'Bar charts with error bars', 'Scatter plots'],
        'software': ['R', 'Python', 'GraphPad Prism'],
        'expected_outcomes': 'Significant difference between groups'
    }
    
    # Add potential pitfalls
    state['potential_pitfalls'] = [
        {'issue': 'Insufficient sample size', 'likelihood': 'high', 'mitigation': 'Perform power analysis'},
        {'issue': 'Measurement error', 'likelihood': 'medium', 'mitigation': 'Calibrate instruments'},
        {'issue': 'Batch effects', 'likelihood': 'high', 'mitigation': 'Randomize samples across batches'},
        {'issue': 'Environmental variation', 'likelihood': 'medium', 'mitigation': 'Control temperature and humidity'}
    ]
    
    # Add expected outcomes
    state['expected_outcomes'] = """
    Data collection completed according to protocol
    All planned measurements obtained successfully
    Quality control checks passed
    Statistical power achieved for primary endpoint
    Meaningful change detected in outcome variables
    Results are reproducible and consistent
    """
    
    return state 