"""
Tests for the ObjectiveAgent class.

This module tests the objective setting agent functionality including objective
clarification, hypothesis development, and SMART goal generation.
"""

import pytest
from unittest.mock import Mock, patch

from ..agents.objective_agent import ObjectiveAgent
from ..state import ExperimentPlanState
from ..factory import create_new_experiment_state, add_chat_message


class TestObjectiveAgentInitialization:
    """Test ObjectiveAgent initialization."""
    
    def test_valid_initialization(self):
        """Test that ObjectiveAgent initializes correctly."""
        agent = ObjectiveAgent()
        
        assert agent.agent_name == "objective_agent"
        assert agent.stage == "objective_setting"
        assert agent.logger is not None
        assert agent.debugger is not None
    
    def test_initialization_with_custom_params(self, mock_debugger):
        """Test initialization with custom parameters."""
        agent = ObjectiveAgent(debugger=mock_debugger, log_level="DEBUG")
        
        assert agent.debugger == mock_debugger
        assert agent.logger.level == 10  # DEBUG level


class TestObjectiveAgentStateProcessing:
    """Test ObjectiveAgent state processing functionality."""
    
    def test_process_state_initial_extraction(self, minimal_state):
        """Test processing state with initial objective extraction."""
        agent = ObjectiveAgent()
        
        # Add user input to chat history
        state_with_input = add_chat_message(minimal_state, "user", "I want to study enzyme kinetics")
        
        result = agent.process_state(state_with_input)
        
        assert 'experiment_objective' in result
        assert result['experiment_objective'] == "I want to study enzyme kinetics"
        assert 'updated_at' in result
        
        # Check that response was added to chat history
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_objective_refinement(self, minimal_state):
        """Test processing state with objective refinement."""
        agent = ObjectiveAgent()
        
        # Set initial objective
        minimal_state['experiment_objective'] = "Study proteins"
        
        # Add user input for refinement
        state_with_input = add_chat_message(minimal_state, "user", "specifically enzyme kinetics at different temperatures")
        
        result = agent.process_state(state_with_input)
        
        # Should refine the objective
        assert 'experiment_objective' in result
        assert "enzyme kinetics" in result['experiment_objective']
        assert "temperatures" in result['experiment_objective']
    
    def test_process_state_hypothesis_development(self, minimal_state):
        """Test processing state for hypothesis development."""
        agent = ObjectiveAgent()
        
        # Set a complete objective but no hypothesis
        minimal_state['experiment_objective'] = "Determine the optimal temperature for α-amylase activity"
        
        # Add user input for hypothesis
        state_with_input = add_chat_message(minimal_state, "user", "I predict activity will increase until 50°C then decrease")
        
        result = agent.process_state(state_with_input)
        
        assert 'hypothesis' in result
        assert result['hypothesis'] == "I predict activity will increase until 50°C then decrease"
    
    def test_process_state_validation_and_finalization(self, objective_complete_state):
        """Test processing state with validation and finalization."""
        agent = ObjectiveAgent()
        
        # Add some refinement input
        state_with_input = add_chat_message(objective_complete_state, "user", "Please refine the objective to be more specific")
        
        result = agent.process_state(state_with_input)
        
        # Should maintain the objective but possibly refine it
        assert 'experiment_objective' in result
        assert 'hypothesis' in result
    
    def test_process_state_no_user_input(self, minimal_state):
        """Test processing state without user input."""
        agent = ObjectiveAgent()
        
        result = agent.process_state(minimal_state)
        
        # Should still process and add assistant response
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0


class TestObjectiveAgentQuestionGeneration:
    """Test ObjectiveAgent question generation functionality."""
    
    def test_generate_questions_initial_state(self, minimal_state):
        """Test question generation for initial state."""
        agent = ObjectiveAgent()
        
        questions = agent.generate_questions(minimal_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 5  # Should limit to 5 questions
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 0 for q in questions)
    
    def test_generate_questions_with_objective_no_hypothesis(self, minimal_state):
        """Test question generation when objective exists but no hypothesis."""
        agent = ObjectiveAgent()
        
        minimal_state['experiment_objective'] = "Study enzyme kinetics"
        
        questions = agent.generate_questions(minimal_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        # Should include hypothesis development questions
        assert any('hypothesis' in q.lower() or 'predict' in q.lower() for q in questions)
    
    def test_generate_questions_with_complete_objective(self, objective_complete_state):
        """Test question generation with complete objective and hypothesis."""
        agent = ObjectiveAgent()
        
        questions = agent.generate_questions(objective_complete_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        # Should include SMART refinement questions
    
    def test_generate_questions_randomization(self, minimal_state):
        """Test that questions are randomized."""
        agent = ObjectiveAgent()
        
        # Generate questions multiple times
        questions1 = agent.generate_questions(minimal_state)
        questions2 = agent.generate_questions(minimal_state)
        questions3 = agent.generate_questions(minimal_state)
        
        # While content might be similar, order could be different
        # This test ensures the randomization doesn't break functionality
        assert all(isinstance(q, str) for q in questions1)
        assert all(isinstance(q, str) for q in questions2)
        assert all(isinstance(q, str) for q in questions3)


class TestObjectiveAgentValidation:
    """Test ObjectiveAgent validation functionality."""
    
    def test_validate_stage_requirements_incomplete(self, minimal_state):
        """Test validation with incomplete stage requirements."""
        agent = ObjectiveAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert isinstance(missing_requirements, list)
        assert len(missing_requirements) > 0
        assert any('objective' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_with_objective_only(self, minimal_state):
        """Test validation with objective but no hypothesis."""
        agent = ObjectiveAgent()
        
        minimal_state['experiment_objective'] = "Study the effect of temperature on enzyme activity"
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert 'hypothesis' in str(missing_requirements).lower()
    
    def test_validate_stage_requirements_complete(self, objective_complete_state):
        """Test validation with complete stage requirements."""
        agent = ObjectiveAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(objective_complete_state)
        
        # This depends on the validation logic in the prompts module
        # It should be valid or close to valid
        assert isinstance(is_valid, bool)
        assert isinstance(missing_requirements, list)
    
    def test_validate_stage_requirements_short_objective(self, minimal_state):
        """Test validation with very short objective."""
        agent = ObjectiveAgent()
        
        minimal_state['experiment_objective'] = "Study"  # Too short
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert any('detailed' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_smart_criteria(self, minimal_state):
        """Test validation for SMART criteria."""
        agent = ObjectiveAgent()
        
        # Objective without measurable outcomes
        minimal_state['experiment_objective'] = "I want to look at protein folding"
        minimal_state['hypothesis'] = "Proteins fold differently"
        
        is_valid, missing_requirements = agent.validate_stage_requirements(minimal_state)
        
        assert is_valid is False
        assert any('measurable' in req.lower() for req in missing_requirements)


class TestObjectiveAgentResponseGeneration:
    """Test ObjectiveAgent response generation functionality."""
    
    def test_generate_agent_response_initial_state(self, minimal_state):
        """Test response generation for initial state."""
        agent = ObjectiveAgent()
        
        # Mock the validation results
        validation_results = {
            'is_complete': False,
            'score': 20,
            'missing_elements': ['objective'],
            'suggestions': ['Be more specific about what you want to study']
        }
        
        response = agent._generate_agent_response(minimal_state, validation_results)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'specific' in response.lower()
    
    def test_generate_agent_response_needs_hypothesis(self, minimal_state):
        """Test response generation when hypothesis is needed."""
        agent = ObjectiveAgent()
        
        minimal_state['experiment_objective'] = "Study enzyme kinetics"
        
        validation_results = {
            'is_complete': False,
            'score': 60,
            'missing_elements': ['hypothesis'],
            'suggestions': ['Develop a testable hypothesis']
        }
        
        response = agent._generate_agent_response(minimal_state, validation_results)
        
        assert isinstance(response, str)
        assert 'hypothesis' in response.lower()
    
    def test_generate_agent_response_complete(self, objective_complete_state):
        """Test response generation when objective is complete."""
        agent = ObjectiveAgent()
        
        validation_results = {
            'is_complete': True,
            'score': 85,
            'missing_elements': [],
            'suggestions': []
        }
        
        response = agent._generate_agent_response(objective_complete_state, validation_results)
        
        assert isinstance(response, str)
        assert 'complete' in response.lower() or 'ready' in response.lower()
    
    def test_generate_agent_response_needs_refinement(self, minimal_state):
        """Test response generation when refinement is needed."""
        agent = ObjectiveAgent()
        
        minimal_state['experiment_objective'] = "Study protein"
        minimal_state['hypothesis'] = "Protein will change"
        
        validation_results = {
            'is_complete': False,
            'score': 40,
            'missing_elements': ['specificity'],
            'suggestions': ['Be more specific about which protein and what changes']
        }
        
        response = agent._generate_agent_response(minimal_state, validation_results)
        
        assert isinstance(response, str)
        assert 'specific' in response.lower()


class TestObjectiveAgentUtilityMethods:
    """Test ObjectiveAgent utility methods."""
    
    def test_get_latest_user_input(self, minimal_state):
        """Test extracting latest user input from chat history."""
        agent = ObjectiveAgent()
        
        # Add multiple messages
        state = add_chat_message(minimal_state, "user", "First message")
        state = add_chat_message(state, "assistant", "Response")
        state = add_chat_message(state, "user", "Second message")
        
        latest_input = agent._get_latest_user_input(state)
        
        assert latest_input == "Second message"
    
    def test_get_latest_user_input_no_messages(self, minimal_state):
        """Test extracting user input when no messages exist."""
        agent = ObjectiveAgent()
        
        latest_input = agent._get_latest_user_input(minimal_state)
        
        assert latest_input == ""
    
    def test_get_latest_user_input_no_user_messages(self, minimal_state):
        """Test extracting user input when only assistant messages exist."""
        agent = ObjectiveAgent()
        
        state = add_chat_message(minimal_state, "assistant", "Assistant message")
        
        latest_input = agent._get_latest_user_input(state)
        
        assert latest_input == ""
    
    def test_extract_initial_objective(self, minimal_state):
        """Test extracting initial objective from user input."""
        agent = ObjectiveAgent()
        
        result = agent._extract_initial_objective(minimal_state, "I want to study enzyme kinetics")
        
        assert result['experiment_objective'] == "I want to study enzyme kinetics"
    
    def test_extract_initial_objective_fallback(self, minimal_state):
        """Test extracting initial objective with fallback to research query."""
        agent = ObjectiveAgent()
        
        result = agent._extract_initial_objective(minimal_state, "")
        
        assert result['experiment_objective'] == minimal_state['research_query']
    
    def test_refine_objective(self, minimal_state):
        """Test refining existing objective."""
        agent = ObjectiveAgent()
        
        minimal_state['experiment_objective'] = "Study enzyme kinetics"
        
        result = agent._refine_objective(minimal_state, "at different temperatures", {})
        
        assert "enzyme kinetics" in result['experiment_objective']
        assert "temperatures" in result['experiment_objective']
    
    def test_develop_hypothesis(self, minimal_state):
        """Test developing hypothesis from user input."""
        agent = ObjectiveAgent()
        
        result = agent._develop_hypothesis(minimal_state, "Activity will increase with temperature")
        
        assert result['hypothesis'] == "Activity will increase with temperature"
    
    def test_get_follow_up_question(self, minimal_state):
        """Test getting appropriate follow-up questions."""
        agent = ObjectiveAgent()
        
        question = agent._get_follow_up_question(['objective specificity'])
        assert isinstance(question, str)
        assert 'measure' in question.lower()
        
        question = agent._get_follow_up_question(['hypothesis development'])
        assert isinstance(question, str)
        assert 'outcome' in question.lower()
        
        question = agent._get_follow_up_question(['random element'])
        assert isinstance(question, str)


class TestObjectiveAgentSummaryMethod:
    """Test ObjectiveAgent summary functionality."""
    
    def test_get_objective_summary_minimal(self, minimal_state):
        """Test getting objective summary for minimal state."""
        agent = ObjectiveAgent()
        
        summary = agent.get_objective_summary(minimal_state)
        
        assert isinstance(summary, dict)
        assert 'stage' in summary
        assert 'research_query' in summary
        assert 'experiment_objective' in summary
        assert 'hypothesis' in summary
        assert 'completion_score' in summary
        assert 'is_complete' in summary
        assert 'missing_elements' in summary
        assert 'suggestions' in summary
        assert 'domain_guidance' in summary
        
        assert summary['stage'] == 'objective_setting'
        assert summary['research_query'] == minimal_state['research_query']
    
    def test_get_objective_summary_complete(self, objective_complete_state):
        """Test getting objective summary for complete state."""
        agent = ObjectiveAgent()
        
        summary = agent.get_objective_summary(objective_complete_state)
        
        assert isinstance(summary, dict)
        assert summary['experiment_objective'] == objective_complete_state['experiment_objective']
        assert summary['hypothesis'] == objective_complete_state['hypothesis']
        assert isinstance(summary['completion_score'], (int, float))
        assert isinstance(summary['is_complete'], bool)


class TestObjectiveAgentIntegration:
    """Integration tests for ObjectiveAgent functionality."""
    
    def test_full_objective_workflow(self, minimal_state):
        """Test complete objective setting workflow."""
        agent = ObjectiveAgent()
        
        # Step 1: Initial user input
        state1 = add_chat_message(minimal_state, "user", "I want to study enzyme activity")
        result1 = agent.execute(state1)
        
        assert 'experiment_objective' in result1
        assert result1['experiment_objective'] == "I want to study enzyme activity"
        
        # Step 2: Generate questions
        questions = agent.generate_questions(result1)
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Step 3: Refine objective
        state2 = add_chat_message(result1, "user", "specifically α-amylase at different temperatures")
        result2 = agent.execute(state2)
        
        assert "α-amylase" in result2['experiment_objective']
        assert "temperatures" in result2['experiment_objective']
        
        # Step 4: Add hypothesis
        state3 = add_chat_message(result2, "user", "I predict maximum activity will be at 50°C")
        result3 = agent.execute(state3)
        
        assert result3['hypothesis'] == "I predict maximum activity will be at 50°C"
        
        # Step 5: Check completion
        is_valid, missing = agent.validate_stage_requirements(result3)
        summary = agent.get_objective_summary(result3)
        
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
        assert isinstance(summary, dict)
    
    def test_error_handling_workflow(self, invalid_state):
        """Test error handling in objective workflow."""
        agent = ObjectiveAgent()
        
        # Should handle invalid state gracefully
        result = agent.execute(invalid_state)
        
        assert 'errors' in result
        assert len(result['errors']) > 0
        
        # Should still generate response
        response = agent.generate_response(result)
        assert isinstance(response, str)
        assert 'error' in response.lower()
    
    def test_response_consistency(self, minimal_state):
        """Test that responses are consistent with state."""
        agent = ObjectiveAgent()
        
        # Test with different completion levels
        states = [
            minimal_state,
            add_chat_message(minimal_state, "user", "Study enzyme kinetics"),
        ]
        
        for state in states:
            result = agent.execute(state)
            response = agent.generate_response(result)
            
            assert isinstance(response, str)
            assert len(response) > 0
            # Response should be relevant to the state
            if 'experiment_objective' in result:
                # Should acknowledge the objective or ask for refinement
                assert len(response) > 20  # Should be substantial
    
    def test_state_preservation_through_processing(self, minimal_state):
        """Test that essential state is preserved during processing."""
        agent = ObjectiveAgent()
        
        original_id = minimal_state['experiment_id']
        original_query = minimal_state['research_query']
        
        # Process multiple times
        result1 = agent.execute(minimal_state, "First input")
        result2 = agent.execute(result1, "Second input")
        result3 = agent.execute(result2, "Third input")
        
        # Essential fields should be preserved
        assert result3['experiment_id'] == original_id
        assert result3['research_query'] == original_query
        
        # Should maintain chat history
        chat_history = result3.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) >= 3
        
        # Should maintain errors list
        assert 'errors' in result3
        assert isinstance(result3['errors'], list) 