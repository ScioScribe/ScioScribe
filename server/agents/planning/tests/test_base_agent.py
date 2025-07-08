"""
Tests for the BaseAgent class.

This module tests the core functionality of the BaseAgent class that all
specific planning agents inherit from.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List, Tuple

from ..agents.base_agent import BaseAgent
from ..state import ExperimentPlanState, PLANNING_STAGES
from ..validation import StateValidationError
from ..factory import create_new_experiment_state


class TestableAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def __init__(self, stage: str = "objective_setting", **kwargs):
        super().__init__(
            agent_name="testable_agent",
            stage=stage,
            **kwargs
        )
        self.process_called = False
        self.questions_generated = False
        self.validation_called = False
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """Mock implementation of process_state."""
        self.process_called = True
        # Simple mock processing - just update the current stage
        state = state.copy()
        state['current_stage'] = self.stage
        return state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """Mock implementation of generate_questions."""
        self.questions_generated = True
        return ["Mock question 1?", "Mock question 2?"]
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """Mock implementation of validate_stage_requirements."""
        self.validation_called = True
        # Simple validation - check if experiment_objective exists
        objective = state.get('experiment_objective')
        if objective and len(objective.strip()) > 10:
            return True, []
        return False, ['Detailed experiment objective needed']


class TestBaseAgentInitialization:
    """Test BaseAgent initialization."""
    
    def test_valid_initialization(self):
        """Test that BaseAgent initializes correctly with valid parameters."""
        agent = TestableAgent(stage="objective_setting")
        
        assert agent.agent_name == "testable_agent"
        assert agent.stage == "objective_setting"
        assert agent.logger is not None
        assert agent.debugger is not None
    
    def test_invalid_stage_raises_error(self):
        """Test that invalid stage raises ValueError."""
        with pytest.raises(ValueError, match="Invalid stage"):
            TestableAgent(stage="invalid_stage")
    
    def test_valid_stages_accepted(self):
        """Test that all valid stages are accepted."""
        for stage in PLANNING_STAGES:
            agent = TestableAgent(stage=stage)
            assert agent.stage == stage
    
    def test_custom_debugger_and_log_level(self, mock_debugger):
        """Test initialization with custom debugger and log level."""
        agent = TestableAgent(
            stage="objective_setting",
            debugger=mock_debugger,
            log_level="DEBUG"
        )
        
        assert agent.debugger == mock_debugger
        assert agent.logger.level == 10  # DEBUG level


class TestBaseAgentStateProcessing:
    """Test BaseAgent state processing functionality."""
    
    def test_execute_with_valid_state(self, minimal_state):
        """Test execute method with valid state."""
        agent = TestableAgent()
        
        result = agent.execute(minimal_state)
        
        assert agent.process_called
        assert result['current_stage'] == 'objective_setting'
        assert 'errors' in result
        assert len(result['errors']) == 0
    
    def test_execute_with_user_input(self, minimal_state):
        """Test execute method with user input."""
        agent = TestableAgent()
        user_input = "I want to study enzyme kinetics"
        
        result = agent.execute(minimal_state, user_input)
        
        assert agent.process_called
        # Check that user input was added to chat history
        chat_history = result.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) > 0
        assert user_messages[-1]['content'] == user_input
    
    def test_execute_with_invalid_state(self, invalid_state):
        """Test execute method with invalid state."""
        agent = TestableAgent()
        
        result = agent.execute(invalid_state)
        
        # Should handle the error gracefully
        assert 'errors' in result
        assert len(result['errors']) > 0
        assert any('validation error' in error.lower() for error in result['errors'])
    
    def test_can_process_stage(self, minimal_state):
        """Test can_process_stage method."""
        agent = TestableAgent(stage="objective_setting")
        
        # Should return True when current_stage matches
        minimal_state['current_stage'] = 'objective_setting'
        assert agent.can_process_stage(minimal_state) is True
        
        # Should return False when current_stage doesn't match
        minimal_state['current_stage'] = 'variable_identification'
        assert agent.can_process_stage(minimal_state) is False


class TestBaseAgentProgressTracking:
    """Test BaseAgent progress tracking functionality."""
    
    def test_get_stage_progress_incomplete(self, minimal_state):
        """Test get_stage_progress with incomplete stage."""
        agent = TestableAgent()
        
        progress = agent.get_stage_progress(minimal_state)
        
        assert progress['stage'] == 'objective_setting'
        assert progress['agent'] == 'testable_agent'
        assert progress['is_complete'] is False
        assert len(progress['missing_requirements']) > 0
        assert progress['can_advance'] is False
        assert isinstance(progress['completion_percentage'], float)
    
    def test_get_stage_progress_complete(self, objective_complete_state):
        """Test get_stage_progress with complete stage."""
        agent = TestableAgent()
        
        progress = agent.get_stage_progress(objective_complete_state)
        
        assert progress['is_complete'] is True
        assert len(progress['missing_requirements']) == 0
        assert progress['can_advance'] is True
        assert progress['completion_percentage'] == 100.0
    
    def test_calculate_completion_percentage(self, minimal_state):
        """Test completion percentage calculation."""
        agent = TestableAgent()
        
        # With no objective
        percentage = agent._calculate_completion_percentage(minimal_state)
        assert 0 <= percentage <= 100
        
        # With objective
        minimal_state['experiment_objective'] = 'Study protein folding mechanisms'
        percentage = agent._calculate_completion_percentage(minimal_state)
        assert percentage == 100.0  # Since validation will pass


class TestBaseAgentResponseGeneration:
    """Test BaseAgent response generation functionality."""
    
    def test_generate_response_incomplete_stage(self, minimal_state):
        """Test generate_response with incomplete stage."""
        agent = TestableAgent()
        
        response = agent.generate_response(minimal_state)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert agent.questions_generated
        assert agent.validation_called
    
    def test_generate_response_complete_stage(self, objective_complete_state):
        """Test generate_response with complete stage."""
        agent = TestableAgent()
        
        response = agent.generate_response(objective_complete_state)
        
        assert isinstance(response, str)
        assert 'completed' in response.lower() or 'move to' in response.lower()
    
    def test_generate_response_with_user_input(self, minimal_state):
        """Test generate_response with user input."""
        agent = TestableAgent()
        user_input = "I want to study enzyme activity"
        
        response = agent.generate_response(minimal_state, user_input)
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_generate_questions_called(self, minimal_state):
        """Test that generate_questions is called during response generation."""
        agent = TestableAgent()
        
        agent.generate_response(minimal_state)
        
        assert agent.questions_generated
    
    def test_validate_stage_requirements_called(self, minimal_state):
        """Test that validate_stage_requirements is called during response generation."""
        agent = TestableAgent()
        
        agent.generate_response(minimal_state)
        
        assert agent.validation_called


class TestBaseAgentErrorHandling:
    """Test BaseAgent error handling functionality."""
    
    def test_state_validation_error_handling(self, minimal_state):
        """Test handling of StateValidationError."""
        agent = TestableAgent()
        
        # Mock process_state to raise StateValidationError
        with patch.object(agent, 'process_state', side_effect=StateValidationError("Test validation error")):
            result = agent.execute(minimal_state)
            
            assert 'errors' in result
            assert len(result['errors']) > 0
            assert any('validation error' in error for error in result['errors'])
    
    def test_general_exception_handling(self, minimal_state):
        """Test handling of general exceptions."""
        agent = TestableAgent()
        
        # Mock process_state to raise generic exception
        with patch.object(agent, 'process_state', side_effect=Exception("Test exception")):
            result = agent.execute(minimal_state)
            
            assert 'errors' in result
            assert len(result['errors']) > 0
            assert any('execution error' in error for error in result['errors'])
    
    def test_response_generation_error_handling(self, minimal_state):
        """Test error handling in response generation."""
        agent = TestableAgent()
        
        # Mock validate_stage_requirements to raise exception
        with patch.object(agent, 'validate_stage_requirements', side_effect=Exception("Test error")):
            response = agent.generate_response(minimal_state)
            
            assert 'error' in response.lower()
            assert 'try again' in response.lower()


class TestBaseAgentDebugFunctionality:
    """Test BaseAgent debug functionality."""
    
    def test_get_debug_info(self, minimal_state):
        """Test get_debug_info method."""
        agent = TestableAgent()
        
        debug_info = agent.get_debug_info(minimal_state)
        
        assert 'agent_name' in debug_info
        assert 'stage' in debug_info
        assert 'can_process' in debug_info
        assert 'progress' in debug_info
        assert 'state_summary' in debug_info
        
        assert debug_info['agent_name'] == 'testable_agent'
        assert debug_info['stage'] == 'objective_setting'
    
    def test_repr_method(self):
        """Test __repr__ method."""
        agent = TestableAgent()
        
        repr_str = repr(agent)
        
        assert 'TestableAgent' in repr_str
        assert 'testable_agent' in repr_str
        assert 'objective_setting' in repr_str


class TestBaseAgentValidationMethods:
    """Test BaseAgent validation methods."""
    
    def test_validate_input_state_valid(self, minimal_state):
        """Test _validate_input_state with valid state."""
        agent = TestableAgent()
        
        # Should not raise any exceptions
        try:
            agent._validate_input_state(minimal_state)
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")
    
    def test_validate_input_state_invalid_type(self):
        """Test _validate_input_state with invalid type."""
        agent = TestableAgent()
        
        with pytest.raises(StateValidationError):
            agent._validate_input_state("not_a_dict")
    
    def test_validate_output_state_valid(self, minimal_state):
        """Test _validate_output_state with valid state."""
        agent = TestableAgent()
        
        # Should not raise any exceptions
        try:
            agent._validate_output_state(minimal_state)
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")
    
    def test_get_stage_fields(self):
        """Test _get_stage_fields method."""
        agent = TestableAgent(stage="objective_setting")
        
        fields = agent._get_stage_fields()
        
        assert isinstance(fields, list)
        assert 'experiment_objective' in fields
        assert 'hypothesis' in fields
    
    def test_different_stage_fields(self):
        """Test _get_stage_fields for different stages."""
        # Test variable identification stage
        agent = TestableAgent(stage="variable_identification")
        fields = agent._get_stage_fields()
        
        assert 'independent_variables' in fields
        assert 'dependent_variables' in fields
        assert 'control_variables' in fields
        
        # Test unknown stage
        agent = TestableAgent(stage="unknown_stage")
        fields = agent._get_stage_fields()
        
        assert fields == []


# Integration tests
class TestBaseAgentIntegration:
    """Integration tests for BaseAgent functionality."""
    
    def test_full_workflow_simulation(self, minimal_state):
        """Test a complete workflow simulation."""
        agent = TestableAgent()
        
        # Step 1: Process initial state
        result1 = agent.execute(minimal_state, "I want to study enzyme kinetics")
        assert 'errors' not in result1 or len(result1['errors']) == 0
        
        # Step 2: Generate response
        response = agent.generate_response(result1)
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Step 3: Check progress
        progress = agent.get_stage_progress(result1)
        assert isinstance(progress, dict)
        assert 'completion_percentage' in progress
        
        # Step 4: Get debug info
        debug_info = agent.get_debug_info(result1)
        assert isinstance(debug_info, dict)
    
    def test_state_consistency_through_processing(self, minimal_state):
        """Test that state remains consistent through processing."""
        agent = TestableAgent()
        
        original_id = minimal_state['experiment_id']
        original_query = minimal_state['research_query']
        
        result = agent.execute(minimal_state)
        
        # Basic fields should remain unchanged
        assert result['experiment_id'] == original_id
        assert result['research_query'] == original_query
        
        # Should have timestamps
        assert 'created_at' in result
        assert 'updated_at' in result
        
        # Should have proper structure
        assert isinstance(result.get('chat_history', []), list)
        assert isinstance(result.get('errors', []), list) 