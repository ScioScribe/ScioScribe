"""
Pytest configuration and fixtures for planning agent tests.

This module provides shared fixtures and configuration for testing the experiment
planning agents in isolation.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from ..state import ExperimentPlanState
from ..factory import create_new_experiment_state
from ..debug import StateDebugger


@pytest.fixture
def minimal_state() -> ExperimentPlanState:
    """Create a minimal valid experiment plan state for testing."""
    return create_new_experiment_state(
        research_query="Test research query about protein folding"
    )


@pytest.fixture
def objective_complete_state() -> ExperimentPlanState:
    """Create a state with complete objective information."""
    state = create_new_experiment_state(
        research_query="Effect of temperature on enzyme activity"
    )
    state.update({
        'experiment_objective': 'Determine the optimal temperature for α-amylase enzyme activity using colorimetric assay',
        'hypothesis': 'Enzyme activity will increase with temperature up to 50°C, then decrease due to denaturation',
        'current_stage': 'objective_setting',
        'completed_stages': []
    })
    return state


@pytest.fixture
def variables_complete_state() -> ExperimentPlanState:
    """Create a state with complete variable information."""
    state = create_new_experiment_state(
        research_query="Effect of pH on protein binding"
    )
    state.update({
        'experiment_objective': 'Measure protein-ligand binding affinity across different pH conditions',
        'hypothesis': 'Binding affinity will be highest at physiological pH (7.4)',
        'independent_variables': [
            {
                'name': 'pH',
                'type': 'continuous',
                'units': 'pH units',
                'levels': [6.0, 6.5, 7.0, 7.5, 8.0]
            }
        ],
        'dependent_variables': [
            {
                'name': 'Binding affinity',
                'type': 'continuous',
                'units': 'µM',
                'measurement_method': 'Fluorescence polarization assay'
            }
        ],
        'control_variables': [
            {
                'name': 'Temperature',
                'reason': 'Temperature affects binding kinetics',
                'control_method': 'Maintain at 25°C using water bath'
            }
        ],
        'current_stage': 'variable_identification',
        'completed_stages': ['objective_setting']
    })
    return state


@pytest.fixture
def sample_chat_history() -> list:
    """Create sample chat history for testing."""
    return [
        {
            'timestamp': '2024-01-01T10:00:00Z',
            'role': 'user',
            'content': 'I want to study enzyme kinetics'
        },
        {
            'timestamp': '2024-01-01T10:01:00Z',
            'role': 'assistant',
            'content': 'Great! Let me help you design an enzyme kinetics study. What specific enzyme are you interested in?'
        },
        {
            'timestamp': '2024-01-01T10:02:00Z',
            'role': 'user',
            'content': 'I want to study α-amylase activity at different temperatures'
        }
    ]


@pytest.fixture
def mock_debugger() -> StateDebugger:
    """Create a mock debugger for testing."""
    return StateDebugger(log_level="DEBUG")


@pytest.fixture
def invalid_state() -> Dict[str, Any]:
    """Create an invalid state for testing error handling."""
    return {
        'experiment_id': 'test_invalid',
        # Missing required fields like research_query, created_at, etc.
        'some_invalid_field': 'invalid_value'
    }


@pytest.fixture
def user_inputs() -> Dict[str, str]:
    """Sample user inputs for testing agent interactions."""
    return {
        'vague_objective': 'I want to study proteins',
        'specific_objective': 'I want to measure the binding affinity of protein X to ligand Y under various pH conditions',
        'hypothesis_input': 'I think the binding will be strongest at pH 7.4 because that is physiological pH',
        'variable_suggestion': 'pH should be the independent variable, binding affinity should be measured as the dependent variable',
        'refinement_input': 'Actually, let me also consider temperature as a control variable'
    }


@pytest.fixture
def expected_validation_errors() -> Dict[str, list]:
    """Expected validation errors for testing."""
    return {
        'missing_objective': ['Detailed experiment objective'],
        'missing_hypothesis': ['Testable hypothesis'],
        'missing_variables': ['Independent variables must be defined'],
        'incomplete_variables': ['Variable measurement methods must be specified']
    }


# Mock external dependencies
@pytest.fixture
def mock_llm_response():
    """Mock LLM responses for testing without external API calls."""
    return {
        'objective_clarification': 'Could you be more specific about which aspect of protein folding you want to study?',
        'variable_suggestion': 'Based on your objective, I suggest measuring protein concentration as the dependent variable.',
        'hypothesis_refinement': 'Your hypothesis could be more specific about the expected quantitative relationship.'
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for each test."""
    # This fixture runs before each test
    yield
    # Cleanup after each test if needed
    pass 