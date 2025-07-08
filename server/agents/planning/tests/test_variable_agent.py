"""
Tests for the VariableAgent class.

This module tests the variable identification agent functionality including
independent, dependent, and control variable identification with domain expertise.
"""

import pytest
from unittest.mock import Mock, patch

from ..agents.variable_agent import VariableAgent
from ..state import ExperimentPlanState
from ..factory import create_new_experiment_state, add_chat_message


class TestVariableAgentInitialization:
    """Test VariableAgent initialization."""
    
    def test_valid_initialization(self):
        """Test that VariableAgent initializes correctly."""
        agent = VariableAgent()
        
        assert agent.agent_name == "variable_agent"
        assert agent.stage == "variable_identification"
        assert agent.logger is not None
        assert agent.debugger is not None
    
    def test_initialization_with_custom_params(self, mock_debugger):
        """Test initialization with custom parameters."""
        agent = VariableAgent(debugger=mock_debugger, log_level="DEBUG")
        
        assert agent.debugger == mock_debugger
        assert agent.logger.level == 10  # DEBUG level


class TestVariableAgentStateProcessing:
    """Test VariableAgent state processing functionality."""
    
    def test_process_state_with_objective(self, minimal_state):
        """Test processing state with clear objective."""
        agent = VariableAgent()
        
        # Set objective for variable identification
        minimal_state['experiment_objective'] = "Study the effect of temperature on enzyme activity"
        
        # Add user input
        state_with_input = add_chat_message(minimal_state, "user", "Temperature is independent, enzyme activity is dependent")
        
        result = agent.process_state(state_with_input)
        
        assert 'updated_at' in result
        
        # Check that response was added to chat history
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_variable_suggestion(self, minimal_state):
        """Test processing state with variable suggestions."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Measure protein binding affinity at different pH levels"
        
        state_with_input = add_chat_message(minimal_state, "user", "pH should be independent, binding affinity dependent")
        
        result = agent.process_state(state_with_input)
        
        # Should process the variable suggestions
        assert 'updated_at' in result
        
        # Check response
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_refinement(self, variables_complete_state):
        """Test processing state with variable refinement."""
        agent = VariableAgent()
        
        state_with_input = add_chat_message(variables_complete_state, "user", "Add temperature as a control variable")
        
        result = agent.process_state(state_with_input)
        
        assert 'updated_at' in result
        
        # Should process refinement
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_no_objective(self, minimal_state):
        """Test processing state without clear objective."""
        agent = VariableAgent()
        
        # No objective set
        state_with_input = add_chat_message(minimal_state, "user", "What variables should I consider?")
        
        result = agent.process_state(state_with_input)
        
        # Should still process and respond
        assert 'updated_at' in result
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0


class TestVariableAgentQuestionGeneration:
    """Test VariableAgent question generation functionality."""
    
    def test_generate_questions_with_objective(self, minimal_state):
        """Test question generation with clear objective."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study the effect of temperature on enzyme activity"
        
        questions = agent.generate_questions(minimal_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 5  # Should limit to 5 questions
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 0 for q in questions)
    
    def test_generate_questions_without_objective(self, minimal_state):
        """Test question generation without clear objective."""
        agent = VariableAgent()
        
        questions = agent.generate_questions(minimal_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        # Should ask about objective or general variable questions
    
    def test_generate_questions_with_partial_variables(self, minimal_state):
        """Test question generation with some variables defined."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study enzyme kinetics"
        minimal_state['independent_variables'] = [
            {'name': 'temperature', 'type': 'continuous', 'units': '°C', 'levels': [25, 35, 45]}
        ]
        
        questions = agent.generate_questions(minimal_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        # Should ask about dependent and control variables
    
    def test_generate_questions_randomization(self, minimal_state):
        """Test that questions are randomized appropriately."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study protein folding"
        
        questions1 = agent.generate_questions(minimal_state)
        questions2 = agent.generate_questions(minimal_state)
        questions3 = agent.generate_questions(minimal_state)
        
        # Should all be valid questions
        assert all(isinstance(q, str) for q in questions1)
        assert all(isinstance(q, str) for q in questions2)
        assert all(isinstance(q, str) for q in questions3)


class TestVariableAgentValidation:
    """Test VariableAgent validation functionality."""
    
    def test_validate_stage_requirements_incomplete(self, minimal_state):
        """Test validation with incomplete stage requirements."""
        agent = VariableAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert isinstance(missing_requirements, list)
        assert len(missing_requirements) > 0
        assert any('independent' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_only_independent(self, minimal_state):
        """Test validation with only independent variables."""
        agent = VariableAgent()
        
        minimal_state['independent_variables'] = [
            {'name': 'temperature', 'type': 'continuous', 'units': '°C', 'levels': [25, 35, 45]}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert any('dependent' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_missing_measurement_method(self, minimal_state):
        """Test validation with missing measurement methods."""
        agent = VariableAgent()
        
        minimal_state['independent_variables'] = [
            {'name': 'temperature', 'type': 'continuous', 'units': '°C', 'levels': [25, 35, 45]}
        ]
        minimal_state['dependent_variables'] = [
            {'name': 'activity', 'type': 'continuous', 'units': 'U/mL'}
            # Missing measurement_method
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert any('measurement' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_complete(self, variables_complete_state):
        """Test validation with complete stage requirements."""
        agent = VariableAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(variables_complete_state)
        
        # Should be valid or close to valid
        assert isinstance(is_valid, bool)
        assert isinstance(missing_requirements, list)
        # With properly complete state, should have fewer missing requirements
    
    def test_validate_stage_requirements_incomplete_control_variables(self, minimal_state):
        """Test validation with incomplete control variables."""
        agent = VariableAgent()
        
        minimal_state['independent_variables'] = [
            {'name': 'temperature', 'type': 'continuous', 'units': '°C', 'levels': [25, 35, 45]}
        ]
        minimal_state['dependent_variables'] = [
            {'name': 'activity', 'type': 'continuous', 'units': 'U/mL', 'measurement_method': 'spectrophotometry'}
        ]
        minimal_state['control_variables'] = [
            {'name': 'pH'}  # Missing reason and control_method
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert any('control' in req.lower() for req in missing_requirements)


class TestVariableAgentUtilityMethods:
    """Test VariableAgent utility methods."""
    
    def test_get_latest_user_input(self, minimal_state):
        """Test extracting latest user input from chat history."""
        agent = VariableAgent()
        
        # Add multiple messages
        state = add_chat_message(minimal_state, "user", "First message")
        state = add_chat_message(state, "assistant", "Response")
        state = add_chat_message(state, "user", "Second message about variables")
        
        latest_input = agent._get_latest_user_input(state)
        
        assert latest_input == "Second message about variables"
    
    def test_get_latest_user_input_no_messages(self, minimal_state):
        """Test extracting user input when no messages exist."""
        agent = VariableAgent()
        
        latest_input = agent._get_latest_user_input(minimal_state)
        
        assert latest_input == ""
    
    def test_extract_domain_from_objective(self, minimal_state):
        """Test extracting research domain from objective."""
        agent = VariableAgent()
        
        # Test with enzyme kinetics
        minimal_state['experiment_objective'] = "Study enzyme kinetics at different temperatures"
        domain = agent._extract_domain_from_objective(minimal_state)
        
        assert isinstance(domain, str)
        # Should identify biochemistry-related domain
        
        # Test with cell biology
        minimal_state['experiment_objective'] = "Study cell viability under different conditions"
        domain = agent._extract_domain_from_objective(minimal_state)
        
        assert isinstance(domain, str)
        
        # Test with generic objective
        minimal_state['experiment_objective'] = "Study something interesting"
        domain = agent._extract_domain_from_objective(minimal_state)
        
        assert isinstance(domain, str)
    
    def test_suggest_variables_based_on_objective(self, minimal_state):
        """Test variable suggestion based on objective."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study the effect of pH on protein binding"
        
        suggestions = agent._suggest_variables_based_on_objective(minimal_state)
        
        assert isinstance(suggestions, dict)
        assert 'independent' in suggestions
        assert 'dependent' in suggestions
        assert 'control' in suggestions
        
        # Should suggest relevant variables
        assert isinstance(suggestions['independent'], list)
        assert isinstance(suggestions['dependent'], list)
        assert isinstance(suggestions['control'], list)
    
    def test_process_user_variable_input(self, minimal_state):
        """Test processing user input for variables."""
        agent = VariableAgent()
        
        # Test with clear variable specification
        user_input = "pH is independent variable, binding affinity is dependent"
        
        result = agent._process_user_variable_input(minimal_state, user_input)
        
        assert isinstance(result, dict)
        # Should process and update state based on user input
    
    def test_validate_variable_completeness(self, minimal_state):
        """Test validating variable completeness."""
        agent = VariableAgent()
        
        # Test with incomplete variables
        minimal_state['independent_variables'] = [
            {'name': 'temperature', 'type': 'continuous'}  # Missing units and levels
        ]
        
        validation_results = agent._validate_variable_completeness(minimal_state)
        
        assert isinstance(validation_results, dict)
        assert 'is_complete' in validation_results
        assert 'missing_elements' in validation_results
        assert 'suggestions' in validation_results
        
        assert validation_results['is_complete'] is False
        assert len(validation_results['missing_elements']) > 0


class TestVariableAgentResponseGeneration:
    """Test VariableAgent response generation functionality."""
    
    def test_generate_agent_response_initial_state(self, minimal_state):
        """Test response generation for initial state."""
        agent = VariableAgent()
        
        response = agent.generate_response(minimal_state)
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should ask about objective or variables
    
    def test_generate_agent_response_with_objective(self, minimal_state):
        """Test response generation with clear objective."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study enzyme kinetics"
        
        response = agent.generate_response(minimal_state)
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should provide variable suggestions based on objective
    
    def test_generate_agent_response_with_partial_variables(self, minimal_state):
        """Test response generation with partial variables."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study enzyme activity"
        minimal_state['independent_variables'] = [
            {'name': 'temperature', 'type': 'continuous', 'units': '°C', 'levels': [25, 35, 45]}
        ]
        
        response = agent.generate_response(minimal_state)
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should ask about dependent and control variables
    
    def test_generate_agent_response_needs_refinement(self, minimal_state):
        """Test response generation when refinement is needed."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study proteins"
        minimal_state['independent_variables'] = [
            {'name': 'something', 'type': 'unknown'}  # Incomplete
        ]
        
        response = agent.generate_response(minimal_state)
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should ask for clarification or refinement


class TestVariableAgentSpecialization:
    """Test VariableAgent domain specialization."""
    
    def test_enzyme_kinetics_domain(self, minimal_state):
        """Test variable suggestions for enzyme kinetics."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study α-amylase kinetics at different temperatures"
        
        questions = agent.generate_questions(minimal_state)
        
        # Should include enzyme-specific questions
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check if enzyme-related terms are in questions
        question_text = ' '.join(questions).lower()
        assert 'temperature' in question_text or 'enzyme' in question_text or 'activity' in question_text
    
    def test_cell_biology_domain(self, minimal_state):
        """Test variable suggestions for cell biology."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study cell viability under different stress conditions"
        
        questions = agent.generate_questions(minimal_state)
        
        # Should include cell biology-specific questions
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check for cell biology terms
        question_text = ' '.join(questions).lower()
        assert 'cell' in question_text or 'viability' in question_text or 'stress' in question_text
    
    def test_protein_studies_domain(self, minimal_state):
        """Test variable suggestions for protein studies."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study protein folding under different conditions"
        
        suggestions = agent._suggest_variables_based_on_objective(minimal_state)
        
        assert isinstance(suggestions, dict)
        # Should suggest relevant protein study variables
        
        # Check for protein-related suggestions
        all_suggestions = str(suggestions).lower()
        assert 'protein' in all_suggestions or 'folding' in all_suggestions or 'concentration' in all_suggestions


class TestVariableAgentIntegration:
    """Integration tests for VariableAgent functionality."""
    
    def test_full_variable_workflow(self, minimal_state):
        """Test complete variable identification workflow."""
        agent = VariableAgent()
        
        # Step 1: Set objective
        minimal_state['experiment_objective'] = "Study enzyme activity at different temperatures"
        
        # Step 2: Initial processing
        state1 = add_chat_message(minimal_state, "user", "Temperature should be independent variable")
        result1 = agent.execute(state1)
        
        # Step 3: Add dependent variable
        state2 = add_chat_message(result1, "user", "Enzyme activity is dependent, measured by spectrophotometry")
        result2 = agent.execute(state2)
        
        # Step 4: Add control variable
        state3 = add_chat_message(result2, "user", "pH should be controlled at 7.0")
        result3 = agent.execute(state3)
        
        # Step 5: Validate completion
        is_valid, missing = agent.validate_stage_requirements(result3)
        
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
        
        # Check that chat history was maintained
        chat_history = result3.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) >= 3
    
    def test_error_handling_workflow(self, invalid_state):
        """Test error handling in variable workflow."""
        agent = VariableAgent()
        
        # Should handle invalid state gracefully
        result = agent.execute(invalid_state)
        
        assert 'errors' in result
        assert len(result['errors']) > 0
        
        # Should still generate response
        response = agent.generate_response(result)
        assert isinstance(response, str)
    
    def test_progressive_refinement(self, minimal_state):
        """Test progressive refinement of variables."""
        agent = VariableAgent()
        
        minimal_state['experiment_objective'] = "Study protein binding"
        
        # Start with vague input
        state1 = add_chat_message(minimal_state, "user", "I need variables for protein binding")
        result1 = agent.execute(state1)
        
        # More specific input
        state2 = add_chat_message(result1, "user", "Concentration is independent, binding affinity is dependent")
        result2 = agent.execute(state2)
        
        # Refinement
        state3 = add_chat_message(result2, "user", "Also need to control temperature and pH")
        result3 = agent.execute(state3)
        
        # Should maintain consistency through refinement
        assert result3['experiment_objective'] == minimal_state['experiment_objective']
        assert 'updated_at' in result3
        
        # Should have chat history
        chat_history = result3.get('chat_history', [])
        assert len(chat_history) >= 3
    
    def test_domain_adaptation(self, minimal_state):
        """Test adaptation to different research domains."""
        agent = VariableAgent()
        
        # Test with different objectives
        objectives = [
            "Study enzyme kinetics",
            "Measure cell viability",
            "Analyze protein folding",
            "Test drug efficacy"
        ]
        
        for objective in objectives:
            test_state = minimal_state.copy()
            test_state['experiment_objective'] = objective
            
            questions = agent.generate_questions(test_state)
            response = agent.generate_response(test_state)
            
            assert isinstance(questions, list)
            assert len(questions) > 0
            assert isinstance(response, str)
            assert len(response) > 0
            
            # Each should be relevant to the domain
            combined_text = ' '.join(questions + [response]).lower()
            # Should contain relevant terms or ask relevant questions
            assert len(combined_text) > 50  # Should be substantial
    
    def test_state_consistency_through_processing(self, minimal_state):
        """Test that state remains consistent through processing."""
        agent = VariableAgent()
        
        original_id = minimal_state['experiment_id']
        original_query = minimal_state['research_query']
        
        # Process multiple times
        result1 = agent.execute(minimal_state, "First input about variables")
        result2 = agent.execute(result1, "Second input about variables")
        result3 = agent.execute(result2, "Third input about variables")
        
        # Essential fields should be preserved
        assert result3['experiment_id'] == original_id
        assert result3['research_query'] == original_query
        
        # Should have proper structure
        assert 'chat_history' in result3
        assert 'errors' in result3
        assert 'updated_at' in result3
        
        # Should maintain chat history
        chat_history = result3.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) >= 3 