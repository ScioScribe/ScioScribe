"""
Tests for the DesignAgent class.

This module tests the experimental design agent functionality including
experimental group design, control group recommendations, statistical
power calculations, and sample size optimization.
"""

import pytest
from unittest.mock import Mock, patch
import math

from ..agents.design_agent import DesignAgent
from ..state import ExperimentPlanState
from ..factory import create_new_experiment_state, add_chat_message


class TestDesignAgentInitialization:
    """Test DesignAgent initialization."""
    
    def test_valid_initialization(self):
        """Test that DesignAgent initializes correctly."""
        agent = DesignAgent()
        
        assert agent.agent_name == "design_agent"
        assert agent.stage == "experimental_design"
        assert agent.logger is not None
        assert agent.debugger is not None
    
    def test_initialization_with_custom_params(self, mock_debugger):
        """Test initialization with custom parameters."""
        agent = DesignAgent(debugger=mock_debugger, log_level="DEBUG")
        
        assert agent.debugger == mock_debugger
        assert agent.logger.level == 10  # DEBUG level


class TestDesignAgentStateProcessing:
    """Test DesignAgent state processing functionality."""
    
    def test_process_state_experimental_groups(self, design_ready_state):
        """Test processing state for experimental group design."""
        agent = DesignAgent()
        
        # Add user input for experimental groups
        state_with_input = add_chat_message(
            design_ready_state, 
            "user", 
            "I want to test temperature at 25°C, 35°C, and 45°C"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'experimental_groups' in result
        assert len(result['experimental_groups']) > 0
        assert 'updated_at' in result
        
        # Check that response was added to chat history
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_control_groups(self, design_ready_state):
        """Test processing state for control group design."""
        agent = DesignAgent()
        
        # Add experimental groups first
        design_ready_state['experimental_groups'] = [
            {'name': 'High temp', 'description': 'Temperature at 45°C', 'conditions': ['temp=45']}
        ]
        
        # Add user input for control groups
        state_with_input = add_chat_message(
            design_ready_state, 
            "user", 
            "I need a negative control with no treatment"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'control_groups' in result
        assert 'updated_at' in result
        
        # Check response
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_sample_size(self, design_ready_state):
        """Test processing state for sample size calculation."""
        agent = DesignAgent()
        
        # Add experimental and control groups
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ]
        design_ready_state['control_groups'] = [
            {'type': 'negative', 'purpose': 'Baseline', 'description': 'No treatment'}
        ]
        
        # Add user input for sample size
        state_with_input = add_chat_message(
            design_ready_state, 
            "user", 
            "I expect a medium effect size and want 80% power"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'updated_at' in result
        
        # Check response
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_refinement(self, design_complete_state):
        """Test processing state for design refinement."""
        agent = DesignAgent()
        
        state_with_input = add_chat_message(
            design_complete_state, 
            "user", 
            "I want to add another experimental group"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'updated_at' in result
        
        # Should process refinement
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_no_variables(self, minimal_state):
        """Test processing state without defined variables."""
        agent = DesignAgent()
        
        state_with_input = add_chat_message(
            minimal_state, 
            "user", 
            "How should I design my experiment?"
        )
        
        result = agent.process_state(state_with_input)
        
        # Should still process and respond
        assert 'updated_at' in result
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0


class TestDesignAgentQuestionGeneration:
    """Test DesignAgent question generation functionality."""
    
    def test_generate_questions_with_variables(self, design_ready_state):
        """Test question generation with defined variables."""
        agent = DesignAgent()
        
        questions = agent.generate_questions(design_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 5  # Should limit to 5 questions
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 0 for q in questions)
    
    def test_generate_questions_without_variables(self, minimal_state):
        """Test question generation without defined variables."""
        agent = DesignAgent()
        
        questions = agent.generate_questions(minimal_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        # Should ask about experimental design generally
    
    def test_generate_questions_with_partial_design(self, design_ready_state):
        """Test question generation with partial design."""
        agent = DesignAgent()
        
        # Add experimental groups but no controls
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ]
        
        questions = agent.generate_questions(design_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        # Should ask about control groups
        question_text = ' '.join(questions).lower()
        assert 'control' in question_text
    
    def test_generate_questions_domain_specific(self, design_ready_state):
        """Test domain-specific question generation."""
        agent = DesignAgent()
        
        # Set cell biology context
        design_ready_state['research_query'] = "cell viability under different conditions"
        design_ready_state['experiment_objective'] = "Study cell viability"
        
        questions = agent.generate_questions(design_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check for domain-appropriate questions
        question_text = ' '.join(questions).lower()
        # Should include terms relevant to cell biology


class TestDesignAgentValidation:
    """Test DesignAgent validation functionality."""
    
    def test_validate_stage_requirements_incomplete(self, design_ready_state):
        """Test validation with incomplete stage requirements."""
        agent = DesignAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(design_ready_state)
        
        assert is_valid is False
        assert isinstance(missing_requirements, list)
        assert len(missing_requirements) > 0
        assert any('experimental' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_only_experimental_groups(self, design_ready_state):
        """Test validation with only experimental groups."""
        agent = DesignAgent()
        
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(design_ready_state)
        
        assert is_valid is False
        assert any('control' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_missing_sample_size(self, design_ready_state):
        """Test validation with missing sample size."""
        agent = DesignAgent()
        
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ]
        design_ready_state['control_groups'] = [
            {'type': 'negative', 'purpose': 'Baseline', 'description': 'No treatment'}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(design_ready_state)
        
        assert is_valid is False
        assert any('sample size' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_complete(self, design_complete_state):
        """Test validation with complete stage requirements."""
        agent = DesignAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(design_complete_state)
        
        # Should be valid or close to valid
        assert isinstance(is_valid, bool)
        assert isinstance(missing_requirements, list)
        
        # With properly complete state, should have fewer missing requirements
        if not is_valid:
            assert len(missing_requirements) < 3  # Should be mostly complete
    
    def test_validate_stage_requirements_incomplete_groups(self, design_ready_state):
        """Test validation with incomplete group definitions."""
        agent = DesignAgent()
        
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment'}  # Missing description and conditions
        ]
        design_ready_state['control_groups'] = [
            {'type': 'negative'}  # Missing purpose and description
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(design_ready_state)
        
        assert is_valid is False
        assert any('complete definition' in req.lower() for req in missing_requirements)


class TestDesignAgentStatisticalCalculations:
    """Test DesignAgent statistical power calculations."""
    
    def test_calculate_sample_size_ttest(self):
        """Test sample size calculation for t-test."""
        agent = DesignAgent()
        
        # Test with medium effect size
        result = agent._calculate_sample_size_ttest(0.5, 0.05, 0.8)
        
        assert isinstance(result, int)
        assert result >= 3  # Minimum sample size
        assert result < 100  # Reasonable upper bound
    
    def test_calculate_sample_size_different_effect_sizes(self):
        """Test sample size calculation with different effect sizes."""
        agent = DesignAgent()
        
        # Small effect size should require larger sample
        small_n = agent._calculate_sample_size_ttest(0.2, 0.05, 0.8)
        # Large effect size should require smaller sample  
        large_n = agent._calculate_sample_size_ttest(0.8, 0.05, 0.8)
        
        assert small_n > large_n
        assert both_samples_reasonable(small_n, large_n)
    
    def test_calculate_sample_size_different_power(self):
        """Test sample size calculation with different power levels."""
        agent = DesignAgent()
        
        # Higher power should require larger sample
        high_power_n = agent._calculate_sample_size_ttest(0.5, 0.05, 0.9)
        low_power_n = agent._calculate_sample_size_ttest(0.5, 0.05, 0.7)
        
        assert high_power_n > low_power_n
        assert both_samples_reasonable(high_power_n, low_power_n)
    
    def test_perform_power_analysis(self, design_ready_state):
        """Test comprehensive power analysis."""
        agent = DesignAgent()
        
        sample_info = {
            'effect_size': 0.5,
            'alpha': 0.05,
            'power': 0.8,
            'biological_replicates': 5,
            'technical_replicates': 3
        }
        
        result = agent._perform_power_analysis(design_ready_state, sample_info)
        
        assert isinstance(result, dict)
        assert 'effect_size' in result
        assert 'alpha' in result
        assert 'power' in result
        assert 'required_sample_size' in result
        assert 'statistical_test' in result
        assert 'assumptions' in result
        
        assert result['effect_size'] == 0.5
        assert result['alpha'] == 0.05
        assert result['power'] == 0.8
        assert isinstance(result['required_sample_size'], int)
        assert result['required_sample_size'] >= 3
    
    def test_perform_power_analysis_error_handling(self, design_ready_state):
        """Test power analysis error handling."""
        agent = DesignAgent()
        
        # Test with invalid effect size
        sample_info = {
            'effect_size': 0.0,  # Invalid
            'alpha': 0.05,
            'power': 0.8
        }
        
        result = agent._perform_power_analysis(design_ready_state, sample_info)
        
        assert isinstance(result, dict)
        assert 'error' in result or 'required_sample_size' in result
        # Should provide fallback sample size
        assert result['required_sample_size'] >= 3


class TestDesignAgentUtilityMethods:
    """Test DesignAgent utility methods."""
    
    def test_get_latest_user_input(self, design_ready_state):
        """Test extracting latest user input from chat history."""
        agent = DesignAgent()
        
        # Add multiple messages
        state = add_chat_message(design_ready_state, "user", "First message")
        state = add_chat_message(state, "assistant", "Response")
        state = add_chat_message(state, "user", "Second message about design")
        
        latest_input = agent._get_latest_user_input(state)
        
        assert latest_input == "Second message about design"
    
    def test_get_latest_user_input_no_messages(self, design_ready_state):
        """Test extracting user input when no messages exist."""
        agent = DesignAgent()
        
        latest_input = agent._get_latest_user_input(design_ready_state)
        
        assert latest_input == ""
    
    def test_determine_next_design_action(self, design_ready_state):
        """Test determining next design action."""
        agent = DesignAgent()
        
        # Mock validation results
        validation_results = {'score': 30, 'is_complete': False}
        
        # Test with no experimental groups
        action = agent._determine_next_design_action(design_ready_state, validation_results)
        assert action == "experimental_groups"
        
        # Test with experimental groups but no controls
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ]
        action = agent._determine_next_design_action(design_ready_state, validation_results)
        assert action == "control_groups"
        
        # Test with groups but no sample size
        design_ready_state['control_groups'] = [
            {'type': 'negative', 'purpose': 'Baseline', 'description': 'No treatment'}
        ]
        action = agent._determine_next_design_action(design_ready_state, validation_results)
        assert action == "sample_size"
    
    def test_extract_group_info(self, design_ready_state):
        """Test extracting group information from user input."""
        agent = DesignAgent()
        
        user_input = "I want to test high temperature conditions"
        
        result = agent._extract_group_info(user_input, "experimental")
        
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'description' in result
        assert 'conditions' in result
        assert result['name'] == user_input.strip()
    
    def test_extract_control_info(self, design_ready_state):
        """Test extracting control group information."""
        agent = DesignAgent()
        
        user_input = "I need a negative control with no treatment"
        
        result = agent._extract_control_info(user_input)
        
        assert isinstance(result, dict)
        assert 'type' in result
        assert 'purpose' in result
        assert 'description' in result
        assert result['type'] == "negative"
    
    def test_extract_sample_size_info(self, design_ready_state):
        """Test extracting sample size information."""
        agent = DesignAgent()
        
        user_input = "I want medium effect size with 80% power"
        
        result = agent._extract_sample_size_info(user_input)
        
        assert isinstance(result, dict)
        assert 'biological_replicates' in result
        assert 'technical_replicates' in result
        assert 'effect_size' in result
        assert 'alpha' in result
        assert 'power' in result
        
        # Should use reasonable defaults
        assert result['biological_replicates'] >= 3
        assert result['technical_replicates'] >= 3
        assert 0.1 <= result['effect_size'] <= 1.0
        assert 0.01 <= result['alpha'] <= 0.1
        assert 0.7 <= result['power'] <= 0.95
    
    def test_infer_control_type(self, design_ready_state):
        """Test inferring control type from user input."""
        agent = DesignAgent()
        
        assert agent._infer_control_type("negative control") == "negative"
        assert agent._infer_control_type("positive control") == "positive"
        assert agent._infer_control_type("vehicle control") == "vehicle"
        assert agent._infer_control_type("technical control") == "technical"
        assert agent._infer_control_type("some random input") == "negative"  # Default
    
    def test_validate_group_fields(self, design_ready_state):
        """Test validating group field completeness."""
        agent = DesignAgent()
        
        # Complete group
        complete_group = {
            'name': 'Treatment',
            'description': 'Active treatment',
            'conditions': ['active']
        }
        assert agent._validate_group_fields(complete_group) is True
        
        # Incomplete group
        incomplete_group = {
            'name': 'Treatment'
            # Missing description and conditions
        }
        assert agent._validate_group_fields(incomplete_group) is False
    
    def test_validate_control_group_fields(self, design_ready_state):
        """Test validating control group field completeness."""
        agent = DesignAgent()
        
        # Complete control group
        complete_control = {
            'type': 'negative',
            'purpose': 'Baseline',
            'description': 'No treatment'
        }
        assert agent._validate_control_group_fields(complete_control) is True
        
        # Incomplete control group
        incomplete_control = {
            'type': 'negative'
            # Missing purpose and description
        }
        assert agent._validate_control_group_fields(incomplete_control) is False


class TestDesignAgentResponseGeneration:
    """Test DesignAgent response generation functionality."""
    
    def test_generate_design_response_experimental_groups(self, design_ready_state):
        """Test response generation for experimental groups."""
        agent = DesignAgent()
        
        response = agent._generate_design_response(design_ready_state, "experimental_groups")
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should ask about experimental conditions
    
    def test_generate_design_response_control_groups(self, design_ready_state):
        """Test response generation for control groups."""
        agent = DesignAgent()
        
        response = agent._generate_design_response(design_ready_state, "control_groups")
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should suggest control types
        assert 'control' in response.lower()
    
    def test_generate_design_response_sample_size(self, design_ready_state):
        """Test response generation for sample size."""
        agent = DesignAgent()
        
        # Add some groups for context
        design_ready_state['experimental_groups'] = [{'name': 'Treatment'}]
        design_ready_state['control_groups'] = [{'type': 'negative'}]
        
        response = agent._generate_design_response(design_ready_state, "sample_size")
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should ask about effect size and power
    
    def test_generate_design_response_refinement(self, design_ready_state):
        """Test response generation for refinement."""
        agent = DesignAgent()
        
        response = agent._generate_design_response(design_ready_state, "refinement")
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should ask for refinement
        assert 'refine' in response.lower()
    
    def test_generate_design_response_completion(self, design_complete_state):
        """Test response generation for completion."""
        agent = DesignAgent()
        
        response = agent._generate_design_response(design_complete_state, "finalize")
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should indicate completion
        assert 'complete' in response.lower() or 'ready' in response.lower()
    
    def test_create_design_summary(self, design_complete_state):
        """Test creating design summary."""
        agent = DesignAgent()
        
        experimental_groups = [{'name': 'Treatment 1'}, {'name': 'Treatment 2'}]
        control_groups = [{'type': 'negative'}, {'type': 'positive'}]
        sample_size = {'power_analysis': {'required_sample_size': 15}}
        
        summary = agent._create_design_summary(experimental_groups, control_groups, sample_size)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert 'Treatment 1' in summary
        assert 'Treatment 2' in summary
        assert 'negative' in summary
        assert 'positive' in summary
        assert '15' in summary


class TestDesignAgentSummaryMethod:
    """Test DesignAgent summary functionality."""
    
    def test_get_design_summary_minimal(self, design_ready_state):
        """Test getting design summary for minimal state."""
        agent = DesignAgent()
        
        summary = agent.get_design_summary(design_ready_state)
        
        assert isinstance(summary, dict)
        assert 'stage' in summary
        assert 'experimental_groups' in summary
        assert 'control_groups' in summary
        assert 'sample_size' in summary
        assert 'completion_score' in summary
        assert 'is_complete' in summary
        assert 'missing_elements' in summary
        assert 'suggestions' in summary
        assert 'statistical_power' in summary
        assert 'required_sample_size' in summary
        
        assert summary['stage'] == 'experimental_design'
        assert isinstance(summary['experimental_groups'], list)
        assert isinstance(summary['control_groups'], list)
        assert isinstance(summary['sample_size'], dict)
    
    def test_get_design_summary_complete(self, design_complete_state):
        """Test getting design summary for complete state."""
        agent = DesignAgent()
        
        summary = agent.get_design_summary(design_complete_state)
        
        assert isinstance(summary, dict)
        assert len(summary['experimental_groups']) > 0
        assert len(summary['control_groups']) > 0
        assert 'power_analysis' in summary['sample_size']
        assert isinstance(summary['completion_score'], (int, float))
        assert isinstance(summary['is_complete'], bool)
        assert isinstance(summary['statistical_power'], (int, float))


class TestDesignAgentIntegration:
    """Integration tests for DesignAgent functionality."""
    
    def test_full_design_workflow(self, design_ready_state):
        """Test complete experimental design workflow."""
        agent = DesignAgent()
        
        # Step 1: Add experimental groups
        state1 = add_chat_message(design_ready_state, "user", "Test at 25°C, 35°C, and 45°C")
        result1 = agent.execute(state1)
        
        assert 'experimental_groups' in result1
        
        # Step 2: Add control groups
        state2 = add_chat_message(result1, "user", "Add negative control with no treatment")
        result2 = agent.execute(state2)
        
        assert 'control_groups' in result2
        
        # Step 3: Calculate sample size
        state3 = add_chat_message(result2, "user", "Medium effect size, 80% power")
        result3 = agent.execute(state3)
        
        # Step 4: Validate completion
        is_valid, missing = agent.validate_stage_requirements(result3)
        
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
        
        # Check that chat history was maintained
        chat_history = result3.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) >= 3
        
        # Step 5: Get summary
        summary = agent.get_design_summary(result3)
        assert isinstance(summary, dict)
        assert summary['stage'] == 'experimental_design'
    
    def test_error_handling_workflow(self, invalid_state):
        """Test error handling in design workflow."""
        agent = DesignAgent()
        
        # Should handle invalid state gracefully
        result = agent.execute(invalid_state)
        
        assert 'errors' in result
        assert len(result['errors']) > 0
        
        # Should still generate response
        response = agent.generate_response(result)
        assert isinstance(response, str)
    
    def test_statistical_power_integration(self, design_ready_state):
        """Test statistical power calculation integration."""
        agent = DesignAgent()
        
        # Set up state with experimental and control groups
        design_ready_state['experimental_groups'] = [
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ]
        design_ready_state['control_groups'] = [
            {'type': 'negative', 'purpose': 'Baseline', 'description': 'No treatment'}
        ]
        
        # Process sample size with power analysis
        state = add_chat_message(design_ready_state, "user", "Calculate for medium effect")
        result = agent.execute(state)
        
        # Should integrate power analysis
        if 'sample_size' in result:
            sample_size = result['sample_size']
            if 'power_analysis' in sample_size:
                power_analysis = sample_size['power_analysis']
                assert 'required_sample_size' in power_analysis
                assert 'power' in power_analysis
                assert 'effect_size' in power_analysis
    
    def test_domain_specific_integration(self, design_ready_state):
        """Test domain-specific design integration."""
        agent = DesignAgent()
        
        # Set cell biology context
        design_ready_state['research_query'] = "cell viability study"
        design_ready_state['experiment_objective'] = "Study cell viability under stress"
        
        # Generate questions should be domain-specific
        questions = agent.generate_questions(design_ready_state)
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Process with domain context
        state = add_chat_message(design_ready_state, "user", "Test different stress conditions")
        result = agent.execute(state)
        
        # Should maintain domain context
        assert 'updated_at' in result
        
        # Generate response should be contextually appropriate
        response = agent.generate_response(result)
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_progressive_design_refinement(self, design_ready_state):
        """Test progressive design refinement."""
        agent = DesignAgent()
        
        # Start with basic design
        state1 = add_chat_message(design_ready_state, "user", "Test two conditions")
        result1 = agent.execute(state1)
        
        # Refine with more detail
        state2 = add_chat_message(result1, "user", "Actually, test three temperature conditions")
        result2 = agent.execute(state2)
        
        # Add controls
        state3 = add_chat_message(result2, "user", "Add negative and positive controls")
        result3 = agent.execute(state3)
        
        # Refine sample size
        state4 = add_chat_message(result3, "user", "Increase power to 90%")
        result4 = agent.execute(state4)
        
        # Should maintain progression
        assert 'updated_at' in result4
        
        # Validate final state
        is_valid, missing = agent.validate_stage_requirements(result4)
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
        
        # Should have comprehensive chat history
        chat_history = result4.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) >= 4


# Helper functions for tests
def both_samples_reasonable(n1: int, n2: int) -> bool:
    """Check if both sample sizes are reasonable."""
    return (3 <= n1 <= 1000) and (3 <= n2 <= 1000)


# Additional fixtures specific to design agent tests
@pytest.fixture
def design_ready_state(variables_complete_state):
    """Create a state ready for experimental design."""
    state = variables_complete_state.copy()
    state['current_stage'] = 'experimental_design'
    state['completed_stages'] = ['objective_setting', 'variable_identification']
    return state


@pytest.fixture
def design_complete_state(design_ready_state):
    """Create a state with complete experimental design."""
    state = design_ready_state.copy()
    state.update({
        'experimental_groups': [
            {'name': 'Low pH', 'description': 'pH 6.0 condition', 'conditions': ['pH=6.0']},
            {'name': 'High pH', 'description': 'pH 8.0 condition', 'conditions': ['pH=8.0']}
        ],
        'control_groups': [
            {'type': 'negative', 'purpose': 'Baseline', 'description': 'No treatment'},
            {'type': 'positive', 'purpose': 'Validation', 'description': 'Known active compound'}
        ],
        'sample_size': {
            'biological_replicates': 6,
            'technical_replicates': 3,
            'power_analysis': {
                'effect_size': 0.5,
                'alpha': 0.05,
                'power': 0.8,
                'required_sample_size': 16,
                'statistical_test': 'two_sample_ttest',
                'assumptions': ['Normal distribution', 'Equal variances', 'Independent samples']
            }
        }
    })
    return state 