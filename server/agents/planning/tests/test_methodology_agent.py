"""
Tests for the MethodologyAgent class.

This module tests the methodology and protocol agent functionality including
protocol step generation, materials list creation, domain-specific guidance,
and safety considerations.
"""

import pytest
from unittest.mock import Mock, patch

from ..agents.methodology_agent import MethodologyAgent
from ..state import ExperimentPlanState
from ..factory import create_new_experiment_state, add_chat_message


class TestMethodologyAgentInitialization:
    """Test MethodologyAgent initialization."""
    
    def test_valid_initialization(self):
        """Test that MethodologyAgent initializes correctly."""
        agent = MethodologyAgent()
        
        assert agent.agent_name == "methodology_agent"
        assert agent.stage == "methodology_protocol"
        assert agent.logger is not None
        assert agent.debugger is not None
    
    def test_initialization_with_custom_params(self, mock_debugger):
        """Test initialization with custom parameters."""
        agent = MethodologyAgent(debugger=mock_debugger, log_level="DEBUG")
        
        assert agent.debugger == mock_debugger
        assert agent.logger.level == 10  # DEBUG level


class TestMethodologyAgentStateProcessing:
    """Test MethodologyAgent state processing functionality."""
    
    def test_process_state_protocol_steps(self, methodology_ready_state):
        """Test processing state for protocol step development."""
        agent = MethodologyAgent()
        
        # Add user input for protocol steps
        user_input = """
        1. Prepare samples at room temperature
        2. Add enzyme solution and mix gently
        3. Incubate at 37°C for 30 minutes
        4. Stop reaction with stop solution
        5. Measure absorbance at 405 nm
        """
        
        state_with_input = add_chat_message(methodology_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'methodology_steps' in result
        assert len(result['methodology_steps']) > 0
        assert 'updated_at' in result
        
        # Check that response was added to chat history
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_materials_equipment(self, methodology_ready_state):
        """Test processing state for materials and equipment."""
        agent = MethodologyAgent()
        
        # Add some protocol steps first
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'}
        ]
        
        # Add user input for materials
        user_input = """
        Enzyme solution (α-amylase)
        Buffer (pH 7.0)
        Substrate (starch)
        Stop solution (HCl)
        Spectrophotometer
        Pipettes
        """
        
        state_with_input = add_chat_message(methodology_ready_state, "user", user_input)
        
        result = agent.process_state(state_with_input)
        
        assert 'materials_equipment' in result
        assert len(result['materials_equipment']) > 0
        assert 'updated_at' in result
        
        # Check response
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_refinement(self, methodology_complete_state):
        """Test processing state for methodology refinement."""
        agent = MethodologyAgent()
        
        state_with_input = add_chat_message(
            methodology_complete_state, 
            "user", 
            "I need to add more specific timing parameters to the protocol"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'updated_at' in result
        
        # Should process refinement
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_domain_guidance(self, methodology_ready_state):
        """Test processing state with domain-specific guidance."""
        agent = MethodologyAgent()
        
        # Set cell culture context
        methodology_ready_state['research_query'] = "cell viability under different conditions"
        
        state_with_input = add_chat_message(
            methodology_ready_state, 
            "user", 
            "I need to develop a cell culture protocol"
        )
        
        result = agent.process_state(state_with_input)
        
        assert 'updated_at' in result
        
        # Should provide domain-specific guidance
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0
    
    def test_process_state_no_design(self, minimal_state):
        """Test processing state without experimental design."""
        agent = MethodologyAgent()
        
        state_with_input = add_chat_message(
            minimal_state, 
            "user", 
            "How do I develop a protocol?"
        )
        
        result = agent.process_state(state_with_input)
        
        # Should still process and respond
        assert 'updated_at' in result
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0


class TestMethodologyAgentQuestionGeneration:
    """Test MethodologyAgent question generation functionality."""
    
    def test_generate_questions_protocol_development(self, methodology_ready_state):
        """Test question generation for protocol development."""
        agent = MethodologyAgent()
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 5  # Should limit to 5 questions
        assert all(isinstance(q, str) for q in questions)
        assert all(len(q) > 0 for q in questions)
    
    def test_generate_questions_materials_focus(self, methodology_ready_state):
        """Test question generation when materials are needed."""
        agent = MethodologyAgent()
        
        # Add protocol steps but no materials
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'}
        ]
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about materials and equipment
        question_text = ' '.join(questions).lower()
        assert 'material' in question_text or 'equipment' in question_text or 'reagent' in question_text
    
    def test_generate_questions_cell_culture_domain(self, methodology_ready_state):
        """Test domain-specific question generation for cell culture."""
        agent = MethodologyAgent()
        
        # Set cell culture context
        methodology_ready_state['research_query'] = "cell viability under stress conditions"
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check for cell culture specific questions
        question_text = ' '.join(questions).lower()
        assert 'cell' in question_text or 'culture' in question_text or 'viability' in question_text
    
    def test_generate_questions_molecular_biology_domain(self, methodology_ready_state):
        """Test domain-specific question generation for molecular biology."""
        agent = MethodologyAgent()
        
        # Set molecular biology context
        methodology_ready_state['research_query'] = "DNA extraction and PCR amplification"
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check for molecular biology specific questions
        question_text = ' '.join(questions).lower()
        assert 'dna' in question_text or 'pcr' in question_text or 'extraction' in question_text
    
    def test_generate_questions_biochemistry_domain(self, methodology_ready_state):
        """Test domain-specific question generation for biochemistry."""
        agent = MethodologyAgent()
        
        # Set biochemistry context
        methodology_ready_state['research_query'] = "protein purification and enzyme assays"
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Check for biochemistry specific questions
        question_text = ' '.join(questions).lower()
        assert 'protein' in question_text or 'enzyme' in question_text or 'buffer' in question_text
    
    def test_generate_questions_refinement_stage(self, methodology_complete_state):
        """Test question generation for refinement stage."""
        agent = MethodologyAgent()
        
        questions = agent.generate_questions(methodology_complete_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should ask about refinement topics
        question_text = ' '.join(questions).lower()
        assert 'timing' in question_text or 'quality' in question_text or 'troubleshooting' in question_text


class TestMethodologyAgentValidation:
    """Test MethodologyAgent validation functionality."""
    
    def test_validate_stage_requirements_incomplete(self, methodology_ready_state):
        """Test validation with incomplete stage requirements."""
        agent = MethodologyAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(methodology_ready_state)
        
        assert is_valid is False
        assert isinstance(missing_requirements, list)
        assert len(missing_requirements) > 0
        assert any('protocol' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_only_protocol_steps(self, methodology_ready_state):
        """Test validation with only protocol steps."""
        agent = MethodologyAgent()
        
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'},
            {'step_number': 2, 'description': 'Add enzyme', 'parameters': '1 mL', 'duration': '5 min'},
            {'step_number': 3, 'description': 'Incubate', 'parameters': '37°C', 'duration': '30 min'},
            {'step_number': 4, 'description': 'Stop reaction', 'parameters': 'HCl', 'duration': '1 min'},
            {'step_number': 5, 'description': 'Measure', 'parameters': '405 nm', 'duration': '5 min'}
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(methodology_ready_state)
        
        assert is_valid is False
        assert any('materials' in req.lower() or 'equipment' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_incomplete_protocol_steps(self, methodology_ready_state):
        """Test validation with incomplete protocol steps."""
        agent = MethodologyAgent()
        
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples'},  # Missing parameters and duration
            {'step_number': 2, 'description': 'Add enzyme', 'parameters': '1 mL'},  # Missing duration
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(methodology_ready_state)
        
        assert is_valid is False
        assert any('complete definition' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_incomplete_materials(self, methodology_ready_state):
        """Test validation with incomplete materials."""
        agent = MethodologyAgent()
        
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'},
            {'step_number': 2, 'description': 'Add enzyme', 'parameters': '1 mL', 'duration': '5 min'},
            {'step_number': 3, 'description': 'Incubate', 'parameters': '37°C', 'duration': '30 min'},
            {'step_number': 4, 'description': 'Stop reaction', 'parameters': 'HCl', 'duration': '1 min'},
            {'step_number': 5, 'description': 'Measure', 'parameters': '405 nm', 'duration': '5 min'}
        ]
        methodology_ready_state['materials_equipment'] = [
            {'name': 'Enzyme'},  # Missing type, quantity, specifications
            {'name': 'Buffer', 'type': 'reagent'},  # Missing quantity, specifications
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(methodology_ready_state)
        
        assert is_valid is False
        assert any('specifications' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_missing_safety(self, methodology_ready_state):
        """Test validation with missing safety considerations."""
        agent = MethodologyAgent()
        
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'},
            {'step_number': 2, 'description': 'Add enzyme', 'parameters': '1 mL', 'duration': '5 min'},
            {'step_number': 3, 'description': 'Incubate', 'parameters': '37°C', 'duration': '30 min'},
            {'step_number': 4, 'description': 'Stop reaction', 'parameters': 'HCl', 'duration': '1 min'},
            {'step_number': 5, 'description': 'Measure', 'parameters': '405 nm', 'duration': '5 min'}
        ]
        methodology_ready_state['materials_equipment'] = [
            {'name': 'Enzyme', 'type': 'reagent', 'quantity': '1 mL', 'specifications': 'α-amylase'},
            {'name': 'Buffer', 'type': 'reagent', 'quantity': '100 mL', 'specifications': 'pH 7.0'},
            {'name': 'Spectrophotometer', 'type': 'equipment', 'quantity': '1', 'specifications': 'UV-Vis'},
        ]
        
        is_valid, missing_requirements = agent.validate_stage_requirements(methodology_ready_state)
        
        # Should identify missing safety considerations
        assert any('safety' in req.lower() for req in missing_requirements)
    
    def test_validate_stage_requirements_complete(self, methodology_complete_state):
        """Test validation with complete stage requirements."""
        agent = MethodologyAgent()
        
        is_valid, missing_requirements = agent.validate_stage_requirements(methodology_complete_state)
        
        # Should be valid or close to valid
        assert isinstance(is_valid, bool)
        assert isinstance(missing_requirements, list)
        
        # With properly complete state, should have fewer missing requirements
        if not is_valid:
            assert len(missing_requirements) < 3  # Should be mostly complete


class TestMethodologyAgentUtilityMethods:
    """Test MethodologyAgent utility methods."""
    
    def test_get_latest_user_input(self, methodology_ready_state):
        """Test extracting latest user input from chat history."""
        agent = MethodologyAgent()
        
        # Add multiple messages
        state = add_chat_message(methodology_ready_state, "user", "First message")
        state = add_chat_message(state, "assistant", "Response")
        state = add_chat_message(state, "user", "Second message about protocol")
        
        latest_input = agent._get_latest_user_input(state)
        
        assert latest_input == "Second message about protocol"
    
    def test_get_latest_user_input_no_messages(self, methodology_ready_state):
        """Test extracting user input when no messages exist."""
        agent = MethodologyAgent()
        
        latest_input = agent._get_latest_user_input(methodology_ready_state)
        
        assert latest_input == ""
    
    def test_determine_next_methodology_action(self, methodology_ready_state):
        """Test determining next methodology action."""
        agent = MethodologyAgent()
        
        # Mock validation results
        validation_results = {'score': 30, 'is_complete': False}
        domain_guidance = {'domain': 'biochemistry'}
        
        # Test with no protocol steps
        action = agent._determine_next_methodology_action(methodology_ready_state, validation_results, domain_guidance)
        assert action == "protocol_steps"
        
        # Test with protocol steps but no materials
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'}
        ]
        action = agent._determine_next_methodology_action(methodology_ready_state, validation_results, domain_guidance)
        assert action == "materials_equipment"
        
        # Test with both but low score
        methodology_ready_state['materials_equipment'] = [
            {'name': 'Enzyme', 'type': 'reagent', 'quantity': '1 mL', 'specifications': 'α-amylase'}
        ]
        action = agent._determine_next_methodology_action(methodology_ready_state, validation_results, domain_guidance)
        assert action == "refinement"
        
        # Test with high score
        validation_results['score'] = 85
        action = agent._determine_next_methodology_action(methodology_ready_state, validation_results, domain_guidance)
        assert action == "finalize"
    
    def test_extract_protocol_steps(self, methodology_ready_state):
        """Test extracting protocol steps from user input."""
        agent = MethodologyAgent()
        
        domain_guidance = {'domain': 'biochemistry'}
        user_input = """
        1. Prepare samples at room temperature
        2. Add enzyme solution
        3. Incubate at 37°C for 30 minutes
        """
        
        result = agent._extract_protocol_steps(user_input, domain_guidance)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check that steps have required fields
        for step in result:
            assert 'step_number' in step
            assert 'description' in step
            assert 'parameters' in step
            assert 'duration' in step
    
    def test_extract_materials_equipment(self, methodology_ready_state):
        """Test extracting materials and equipment from user input."""
        agent = MethodologyAgent()
        
        domain_guidance = {'domain': 'biochemistry'}
        user_input = """
        α-amylase enzyme
        Buffer solution
        Spectrophotometer
        Pipettes
        """
        
        result = agent._extract_materials_equipment(user_input, domain_guidance)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check that materials have required fields
        for item in result:
            assert 'name' in item
            assert 'type' in item
            assert 'quantity' in item
            assert 'specifications' in item
    
    def test_validate_methodology_step_fields(self, methodology_ready_state):
        """Test validating methodology step field completeness."""
        agent = MethodologyAgent()
        
        # Complete step
        complete_step = {
            'step_number': 1,
            'description': 'Prepare samples',
            'parameters': '25°C',
            'duration': '10 min'
        }
        assert agent._validate_methodology_step_fields(complete_step) is True
        
        # Incomplete step
        incomplete_step = {
            'step_number': 1,
            'description': 'Prepare samples'
            # Missing parameters and duration
        }
        assert agent._validate_methodology_step_fields(incomplete_step) is False
    
    def test_validate_material_fields(self, methodology_ready_state):
        """Test validating material field completeness."""
        agent = MethodologyAgent()
        
        # Complete material
        complete_material = {
            'name': 'α-amylase',
            'type': 'reagent',
            'quantity': '1 mL',
            'specifications': 'Enzyme solution'
        }
        assert agent._validate_material_fields(complete_material) is True
        
        # Incomplete material
        incomplete_material = {
            'name': 'α-amylase',
            'type': 'reagent'
            # Missing quantity and specifications
        }
        assert agent._validate_material_fields(incomplete_material) is False
    
    def test_create_protocol_summary(self, methodology_ready_state):
        """Test creating protocol summary."""
        agent = MethodologyAgent()
        
        methodology_steps = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'},
            {'step_number': 2, 'description': 'Add enzyme', 'parameters': '1 mL', 'duration': '5 min'},
            {'step_number': 3, 'description': 'Incubate', 'parameters': '37°C', 'duration': '30 min'}
        ]
        
        summary = agent._create_protocol_summary(methodology_steps)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert 'Step 1' in summary
        assert 'Prepare samples' in summary
        assert 'Step 2' in summary
        assert 'Add enzyme' in summary
    
    def test_create_methodology_summary(self, methodology_ready_state):
        """Test creating comprehensive methodology summary."""
        agent = MethodologyAgent()
        
        methodology_steps = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'},
            {'step_number': 2, 'description': 'Add enzyme', 'parameters': '1 mL', 'duration': '5 min'}
        ]
        
        materials_equipment = [
            {'name': 'α-amylase', 'type': 'reagent', 'quantity': '1 mL', 'specifications': 'Enzyme'},
            {'name': 'Buffer', 'type': 'reagent', 'quantity': '100 mL', 'specifications': 'pH 7.0'}
        ]
        
        summary = agent._create_methodology_summary(methodology_steps, materials_equipment)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert 'Protocol Steps' in summary
        assert 'Materials & Equipment' in summary
        assert str(len(methodology_steps)) in summary
        assert str(len(materials_equipment)) in summary


class TestMethodologyAgentResponseGeneration:
    """Test MethodologyAgent response generation functionality."""
    
    def test_generate_methodology_response_protocol_steps(self, methodology_ready_state):
        """Test response generation for protocol steps."""
        agent = MethodologyAgent()
        
        domain_guidance = {'domain': 'biochemistry'}
        
        response = agent._generate_methodology_response(methodology_ready_state, "protocol_steps", domain_guidance)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'protocol' in response.lower()
    
    def test_generate_methodology_response_materials_equipment(self, methodology_ready_state):
        """Test response generation for materials and equipment."""
        agent = MethodologyAgent()
        
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'}
        ]
        
        domain_guidance = {'domain': 'biochemistry'}
        
        response = agent._generate_methodology_response(methodology_ready_state, "materials_equipment", domain_guidance)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'materials' in response.lower() or 'equipment' in response.lower()
    
    def test_generate_methodology_response_refinement(self, methodology_ready_state):
        """Test response generation for refinement."""
        agent = MethodologyAgent()
        
        methodology_ready_state['methodology_steps'] = [
            {'step_number': 1, 'description': 'Prepare samples', 'parameters': '25°C', 'duration': '10 min'}
        ]
        
        domain_guidance = {'domain': 'biochemistry'}
        
        response = agent._generate_methodology_response(methodology_ready_state, "refinement", domain_guidance)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'refine' in response.lower() or 'parameters' in response.lower()
    
    def test_generate_methodology_response_completion(self, methodology_complete_state):
        """Test response generation for completion."""
        agent = MethodologyAgent()
        
        domain_guidance = {'domain': 'biochemistry'}
        
        response = agent._generate_methodology_response(methodology_complete_state, "finalize", domain_guidance)
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert 'complete' in response.lower() or 'ready' in response.lower()


class TestMethodologyAgentSpecialization:
    """Test MethodologyAgent domain specialization."""
    
    def test_cell_culture_specialization(self, methodology_ready_state):
        """Test specialization for cell culture domain."""
        agent = MethodologyAgent()
        
        methodology_ready_state['research_query'] = "cell viability under different conditions"
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should include cell culture specific questions
        question_text = ' '.join(questions).lower()
        assert 'cell' in question_text or 'culture' in question_text or 'viability' in question_text
    
    def test_molecular_biology_specialization(self, methodology_ready_state):
        """Test specialization for molecular biology domain."""
        agent = MethodologyAgent()
        
        methodology_ready_state['research_query'] = "DNA extraction and PCR amplification"
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should include molecular biology specific questions
        question_text = ' '.join(questions).lower()
        assert 'dna' in question_text or 'pcr' in question_text or 'extraction' in question_text
    
    def test_biochemistry_specialization(self, methodology_ready_state):
        """Test specialization for biochemistry domain."""
        agent = MethodologyAgent()
        
        methodology_ready_state['research_query'] = "enzyme kinetics and protein purification"
        
        questions = agent.generate_questions(methodology_ready_state)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        
        # Should include biochemistry specific questions
        question_text = ' '.join(questions).lower()
        assert 'enzyme' in question_text or 'protein' in question_text or 'buffer' in question_text
    
    def test_domain_guidance_integration(self, methodology_ready_state):
        """Test integration of domain guidance."""
        agent = MethodologyAgent()
        
        # Test with cell culture
        methodology_ready_state['research_query'] = "cell culture proliferation assay"
        
        state_with_input = add_chat_message(methodology_ready_state, "user", "I need a cell culture protocol")
        result = agent.process_state(state_with_input)
        
        # Should process with cell culture context
        assert 'updated_at' in result
        
        # Check response includes domain context
        chat_history = result.get('chat_history', [])
        assistant_messages = [msg for msg in chat_history if msg['role'] == 'assistant']
        assert len(assistant_messages) > 0


class TestMethodologyAgentSummaryMethod:
    """Test MethodologyAgent summary method."""
    
    def test_get_methodology_summary_minimal(self, methodology_ready_state):
        """Test getting methodology summary with minimal data."""
        agent = MethodologyAgent()
        
        summary = agent.get_methodology_summary(methodology_ready_state)
        
        assert isinstance(summary, dict)
        assert 'stage' in summary
        assert 'methodology_steps' in summary
        assert 'materials_equipment' in summary
        assert 'completion_score' in summary
        assert 'is_complete' in summary
        assert 'missing_elements' in summary
        assert 'suggestions' in summary
        assert 'domain' in summary
        assert 'step_count' in summary
        assert 'material_count' in summary
        
        assert summary['stage'] == 'methodology_protocol'
        assert summary['step_count'] == 0
        assert summary['material_count'] == 0
        assert summary['is_complete'] is False
    
    def test_get_methodology_summary_complete(self, methodology_complete_state):
        """Test getting methodology summary with complete data."""
        agent = MethodologyAgent()
        
        summary = agent.get_methodology_summary(methodology_complete_state)
        
        assert isinstance(summary, dict)
        assert summary['stage'] == 'methodology_protocol'
        assert summary['step_count'] > 0
        assert summary['material_count'] > 0
        assert isinstance(summary['completion_score'], (int, float))
        assert summary['completion_score'] >= 0
        assert summary['completion_score'] <= 100


class TestMethodologyAgentIntegration:
    """Integration tests for MethodologyAgent functionality."""
    
    def test_full_methodology_workflow(self, methodology_ready_state):
        """Test complete methodology development workflow."""
        agent = MethodologyAgent()
        
        # Step 1: Add protocol steps
        protocol_input = """
        1. Prepare samples at room temperature
        2. Add enzyme solution and mix gently
        3. Incubate at 37°C for 30 minutes
        4. Stop reaction with stop solution
        5. Measure absorbance at 405 nm
        """
        
        state1 = add_chat_message(methodology_ready_state, "user", protocol_input)
        result1 = agent.execute(state1)
        
        # Step 2: Add materials and equipment
        materials_input = """
        α-amylase enzyme solution
        Buffer (pH 7.0)
        Substrate (starch)
        Stop solution (HCl)
        Spectrophotometer
        Pipettes (1-1000 µL)
        Microcentrifuge tubes
        """
        
        state2 = add_chat_message(result1, "user", materials_input)
        result2 = agent.execute(state2)
        
        # Step 3: Refinement
        state3 = add_chat_message(result2, "user", "Add safety considerations for HCl handling")
        result3 = agent.execute(state3)
        
        # Step 4: Validate completion
        is_valid, missing = agent.validate_stage_requirements(result3)
        
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)
        
        # Check that methodology elements were added
        assert len(result3.get('methodology_steps', [])) > 0
        assert len(result3.get('materials_equipment', [])) > 0
        
        # Check that chat history was maintained
        chat_history = result3.get('chat_history', [])
        user_messages = [msg for msg in chat_history if msg['role'] == 'user']
        assert len(user_messages) >= 3
    
    def test_error_handling_workflow(self, invalid_state):
        """Test error handling in methodology workflow."""
        agent = MethodologyAgent()
        
        # Should handle invalid state gracefully
        result = agent.execute(invalid_state)
        
        assert 'errors' in result
        assert len(result['errors']) > 0
        
        # Should still generate response
        response = agent.generate_response(result)
        assert isinstance(response, str)
    
    def test_progressive_methodology_development(self, methodology_ready_state):
        """Test progressive methodology development."""
        agent = MethodologyAgent()
        
        # Start with basic protocol request
        state1 = add_chat_message(methodology_ready_state, "user", "I need help developing a protocol")
        result1 = agent.execute(state1)
        
        # Add more specific input
        state2 = add_chat_message(result1, "user", "It's for enzyme activity measurement")
        result2 = agent.execute(state2)
        
        # Add detailed protocol steps
        state3 = add_chat_message(result2, "user", "1. Prepare enzyme solution\n2. Add substrate\n3. Measure activity")
        result3 = agent.execute(state3)
        
        # Should progressively build methodology
        assert len(result3.get('methodology_steps', [])) > 0
        
        # Chat history should show progression
        chat_history = result3.get('chat_history', [])
        assert len(chat_history) >= 6  # 3 user messages + 3 assistant responses
    
    def test_domain_adaptation_workflow(self, methodology_ready_state):
        """Test domain adaptation in methodology workflow."""
        agent = MethodologyAgent()
        
        # Test with different domains
        domains = [
            ("cell culture viability assay", ["cell", "culture", "viability"]),
            ("DNA extraction protocol", ["dna", "extraction", "molecular"]),
            ("protein purification procedure", ["protein", "purification", "enzyme", "buffer"])
        ]
        
        for query, expected_terms in domains:
            methodology_ready_state['research_query'] = query
            
            questions = agent.generate_questions(methodology_ready_state)
            question_text = ' '.join(questions).lower()
            
            # Should adapt to domain - at least one expected term should appear
            assert any(term in question_text for term in expected_terms), f"None of {expected_terms} found in: {question_text}"
    
    def test_state_consistency_through_processing(self, methodology_ready_state):
        """Test state consistency through processing."""
        agent = MethodologyAgent()
        
        # Process multiple inputs
        inputs = [
            "I need to develop a protocol for enzyme assays",
            "The protocol should include sample preparation",
            "I need materials list for spectrophotometry"
        ]
        
        current_state = methodology_ready_state
        for user_input in inputs:
            state_with_input = add_chat_message(current_state, "user", user_input)
            current_state = agent.process_state(state_with_input)
            
            # Validate state consistency
            assert 'experiment_id' in current_state
            assert 'updated_at' in current_state
            assert 'chat_history' in current_state
            assert current_state['current_stage'] == 'methodology_protocol'
        
        # Final state should be valid
        assert len(current_state.get('chat_history', [])) >= len(inputs) * 2  # User + assistant messages


# Additional fixtures for methodology testing
@pytest.fixture
def methodology_ready_state(variables_complete_state):
    """Create a state ready for methodology development."""
    state = variables_complete_state.copy()
    state.update({
        'experimental_groups': [
            {'name': 'Control', 'description': 'No treatment', 'conditions': []},
            {'name': 'Treatment', 'description': 'Active treatment', 'conditions': ['active']}
        ],
        'control_groups': [
            {'name': 'Negative Control', 'type': 'negative', 'purpose': 'Baseline', 'description': 'No treatment control', 'conditions': []}
        ],
        'sample_size': {
            'biological_replicates': 3,
            'technical_replicates': 3,
            'power_analysis': {'required_sample_size': 15, 'power': 0.8}
        },
        'current_stage': 'methodology_protocol',
        'completed_stages': ['objective_setting', 'variable_identification', 'experimental_design']
    })
    return state


@pytest.fixture
def methodology_complete_state(methodology_ready_state):
    """Create a state with complete methodology information."""
    state = methodology_ready_state.copy()
    state.update({
        'methodology_steps': [
            {'step_number': 1, 'description': 'Prepare samples at room temperature', 'parameters': '25°C', 'duration': '10 min'},
            {'step_number': 2, 'description': 'Add enzyme solution and mix gently', 'parameters': '1 mL', 'duration': '5 min'},
            {'step_number': 3, 'description': 'Incubate at 37°C for 30 minutes', 'parameters': '37°C', 'duration': '30 min'},
            {'step_number': 4, 'description': 'Stop reaction with HCl solution', 'parameters': '0.1 M HCl', 'duration': '1 min'},
            {'step_number': 5, 'description': 'Measure absorbance at 405 nm', 'parameters': '405 nm', 'duration': '5 min'},
            {'step_number': 6, 'description': 'Safety: Handle HCl with proper PPE', 'parameters': 'Gloves, goggles', 'duration': 'Always'}
        ],
        'materials_equipment': [
            {'name': 'α-amylase enzyme', 'type': 'reagent', 'quantity': '1 mL', 'specifications': 'Activity: 100 U/mL'},
            {'name': 'Buffer solution', 'type': 'reagent', 'quantity': '100 mL', 'specifications': 'pH 7.0, 50 mM Tris'},
            {'name': 'Starch substrate', 'type': 'reagent', 'quantity': '10 g', 'specifications': 'Soluble starch'},
            {'name': 'HCl stop solution', 'type': 'reagent', 'quantity': '50 mL', 'specifications': '0.1 M HCl'},
            {'name': 'Spectrophotometer', 'type': 'equipment', 'quantity': '1', 'specifications': 'UV-Vis, 405 nm'},
            {'name': 'Pipettes', 'type': 'equipment', 'quantity': 'Set', 'specifications': '1-1000 µL range'},
            {'name': 'Microcentrifuge tubes', 'type': 'consumable', 'quantity': '100', 'specifications': '1.5 mL, sterile'},
            {'name': 'Water bath', 'type': 'equipment', 'quantity': '1', 'specifications': '37°C ± 0.5°C'},
            {'name': 'Timer', 'type': 'equipment', 'quantity': '1', 'specifications': 'Digital timer'},
            {'name': 'Safety goggles', 'type': 'safety', 'quantity': '1', 'specifications': 'Chemical resistant'},
            {'name': 'Gloves', 'type': 'safety', 'quantity': '1 box', 'specifications': 'Nitrile, chemical resistant'}
        ]
    })
    return state 