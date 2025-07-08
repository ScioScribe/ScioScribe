"""
Final Review & Export Agent for the experiment planning system.

This agent specializes in conducting comprehensive validation of complete experiment plans,
identifying gaps and inconsistencies, and generating export-ready documents in multiple formats.
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
from datetime import datetime

from .base_agent import BaseAgent
from ..state import ExperimentPlanState
from ..factory import add_chat_message, update_state_timestamp
from ..prompts.review_prompts import (
    REVIEW_SYSTEM_PROMPT,
    FINAL_VALIDATION_QUESTIONS,
    PLAN_OPTIMIZATION_QUESTIONS,
    EXPORT_PREPARATION_QUESTIONS,
    USER_APPROVAL_QUESTIONS,
    REVIEW_RESPONSE_TEMPLATES,
    FINAL_VALIDATION_CRITERIA,
    EXPORT_FORMATS,
    validate_final_plan_completeness,
    generate_plan_summary,
    format_review_response,
    generate_export_metadata
)


class ReviewAgent(BaseAgent):
    """
    Agent responsible for final review and export of experiment plans.
    
    This agent guides users through:
    - Comprehensive validation of all experiment plan components
    - Identification of gaps, inconsistencies, and missing elements
    - Plan optimization suggestions and improvements
    - Export preparation and format selection
    - Final user approval and plan finalization
    - Generation of export-ready documents in multiple formats
    """
    
    def __init__(self, debugger: Optional[Any] = None, log_level: str = "INFO"):
        """
        Initialize the Final Review & Export Agent.
        
        Args:
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        super().__init__(
            agent_name="review_agent",
            stage="final_review",
            debugger=debugger,
            log_level=log_level
        )
        
        self.logger.info("ReviewAgent initialized for final review stage")
    
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state to conduct final review and export preparation.
        
        Validates the complete experiment plan, identifies issues, provides optimization
        suggestions, and prepares for export based on user preferences.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState with review results and export preparation
        """
        self.logger.info(f"Processing final review for experiment: {state.get('experiment_id')}")
        
        # Get the latest user input from chat history
        user_input = self._get_latest_user_input(state)
        
        # Validate the complete plan
        validation_results = validate_final_plan_completeness(state)
        
        # Generate comprehensive plan summary
        plan_summary = generate_plan_summary(state)
        
        # Determine the current review action based on validation and user input
        review_action = self._determine_review_action(state, validation_results, user_input)
        
        # Process based on current review needs
        if review_action == "initial_validation":
            updated_state = self._conduct_initial_validation(state, validation_results, plan_summary)
        elif review_action == "address_issues":
            updated_state = self._address_validation_issues(state, validation_results, user_input)
        elif review_action == "optimization":
            updated_state = self._provide_optimization_suggestions(state, plan_summary, user_input)
        elif review_action == "export_preparation":
            updated_state = self._prepare_for_export(state, plan_summary, user_input)
        elif review_action == "generate_export":
            updated_state = self._generate_export_document(state, user_input)
        elif review_action == "user_approval":
            updated_state = self._handle_user_approval(state, user_input)
        elif review_action == "finalization":
            updated_state = self._finalize_plan(state, user_input)
        else:
            updated_state = self._conduct_comprehensive_review(state, validation_results, plan_summary)
        
        # Generate agent response
        response = self._generate_review_response(updated_state, review_action, validation_results)
        updated_state = add_chat_message(updated_state, "assistant", response)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        self.logger.info(f"Final review processing complete for action: {review_action}")
        
        return updated_state
    
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions based on the current review state.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of questions appropriate for the current review stage
        """
        # Validate the plan to understand what questions are needed
        validation_results = validate_final_plan_completeness(state)
        
        # If plan has issues, focus on validation questions
        if validation_results["status"] == "needs_attention":
            return FINAL_VALIDATION_QUESTIONS[:3]  # Focus on key validation questions
        
        # If plan is complete, move to optimization and export questions
        if validation_results["percentage"] >= 90:
            # Check if user has indicated readiness for export
            recent_messages = state.get('chat_history', [])[-3:]  # Look at recent messages
            
            if any('export' in msg.get('content', '').lower() for msg in recent_messages):
                return EXPORT_PREPARATION_QUESTIONS[:3]
            elif any('approve' in msg.get('content', '').lower() for msg in recent_messages):
                return USER_APPROVAL_QUESTIONS[:3]
            else:
                return PLAN_OPTIMIZATION_QUESTIONS[:3]
        
        # Default to general validation questions
        return FINAL_VALIDATION_QUESTIONS[:5]
    
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the final review stage requirements are met.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_complete, list_of_missing_requirements)
        """
        # Use comprehensive validation
        validation_results = validate_final_plan_completeness(state)
        
        # Check if plan is sufficiently complete (>= 90%)
        is_complete = validation_results["percentage"] >= 90
        
        # Get missing requirements
        missing_requirements = validation_results["missing_elements"]
        
        # Also check if user has approved the plan
        user_approved = self._check_user_approval(state)
        
        if not user_approved and is_complete:
            missing_requirements.append("User approval required")
            is_complete = False
        
        return is_complete, missing_requirements
    
    def _get_latest_user_input(self, state: ExperimentPlanState) -> str:
        """Extract the latest user input from chat history."""
        chat_history = state.get('chat_history', [])
        
        # Find the most recent user message
        for message in reversed(chat_history):
            if message.get('role') == 'user':
                return message.get('content', '')
        
        return ''
    
    def _determine_review_action(self, state: ExperimentPlanState, validation_results: Dict[str, Any], user_input: str) -> str:
        """Determine the appropriate review action based on current state."""
        # Check validation status
        validation_status = validation_results.get("status", "needs_attention")
        completion_percentage = validation_results.get("percentage", 0)
        
        # Check user input for specific intents
        user_input_lower = user_input.lower()
        
        # User explicitly requesting export
        if any(keyword in user_input_lower for keyword in ['export', 'generate', 'download', 'save']):
            if completion_percentage >= 90:
                return "generate_export"
            else:
                return "address_issues"
        
        # User approval process
        if any(keyword in user_input_lower for keyword in ['approve', 'yes', 'ready', 'finalize']):
            return "user_approval"
        
        # User requesting optimization
        if any(keyword in user_input_lower for keyword in ['optimize', 'improve', 'enhance', 'better']):
            return "optimization"
        
        # Based on validation status
        if validation_status == "needs_attention":
            return "address_issues"
        elif completion_percentage >= 90:
            # Plan is complete, check if user has been through approval process
            if self._check_user_approval(state):
                return "finalization"
            else:
                return "user_approval"
        else:
            return "initial_validation"
    
    def _conduct_initial_validation(self, state: ExperimentPlanState, validation_results: Dict[str, Any], plan_summary: Dict[str, Any]) -> ExperimentPlanState:
        """Conduct initial comprehensive validation of the experiment plan."""
        # Store validation results in state for reference
        state = state.copy()
        state['validation_results'] = validation_results
        state['plan_summary'] = plan_summary
        
        # Mark that initial validation has been conducted
        state['review_stage'] = 'initial_validation'
        
        return state
    
    def _address_validation_issues(self, state: ExperimentPlanState, validation_results: Dict[str, Any], user_input: str) -> ExperimentPlanState:
        """Address specific validation issues identified in the plan."""
        state = state.copy()
        
        # Process user input to address specific issues
        missing_elements = validation_results.get("missing_elements", [])
        
        # Update state to reflect addressing issues
        state['review_stage'] = 'addressing_issues'
        state['validation_issues'] = missing_elements
        
        return state
    
    def _provide_optimization_suggestions(self, state: ExperimentPlanState, plan_summary: Dict[str, Any], user_input: str) -> ExperimentPlanState:
        """Provide optimization suggestions for the experiment plan."""
        state = state.copy()
        
        # Generate optimization suggestions based on plan content
        optimization_suggestions = self._generate_optimization_suggestions(plan_summary)
        
        # Update state with optimization suggestions
        state['review_stage'] = 'optimization'
        state['optimization_suggestions'] = optimization_suggestions
        
        return state
    
    def _prepare_for_export(self, state: ExperimentPlanState, plan_summary: Dict[str, Any], user_input: str) -> ExperimentPlanState:
        """Prepare the experiment plan for export."""
        state = state.copy()
        
        # Determine preferred export format from user input
        preferred_format = self._determine_export_format(user_input)
        
        # Generate export metadata
        export_metadata = generate_export_metadata(state, preferred_format)
        
        # Update state with export preparation
        state['review_stage'] = 'export_preparation'
        state['export_format'] = preferred_format
        state['export_metadata'] = export_metadata
        
        return state
    
    def _generate_export_document(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Generate the export document in the requested format."""
        state = state.copy()
        
        # Get export format (default to JSON if not specified)
        export_format = state.get('export_format', 'json')
        
        # Generate export document
        export_document = self._create_export_document(state, export_format)
        
        # Update state with generated document
        state['review_stage'] = 'export_generated'
        state['export_document'] = export_document
        state['export_timestamp'] = datetime.utcnow().isoformat()
        
        return state
    
    def _handle_user_approval(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Handle user approval process."""
        state = state.copy()
        
        # Check if user is approving or requesting changes
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ['approve', 'yes', 'ready', 'good']):
            state['user_approved'] = True
            state['review_stage'] = 'approved'
        elif any(keyword in user_input_lower for keyword in ['no', 'change', 'modify', 'revise']):
            state['user_approved'] = False
            state['review_stage'] = 'requires_changes'
        else:
            state['review_stage'] = 'awaiting_approval'
        
        return state
    
    def _finalize_plan(self, state: ExperimentPlanState, user_input: str) -> ExperimentPlanState:
        """Finalize the experiment plan."""
        state = state.copy()
        
        # Mark plan as finalized
        state['review_stage'] = 'finalized'
        state['finalized_at'] = datetime.utcnow().isoformat()
        
        # Add final review to completed stages
        if 'final_review' not in state.get('completed_stages', []):
            state['completed_stages'].append('final_review')
        
        return state
    
    def _conduct_comprehensive_review(self, state: ExperimentPlanState, validation_results: Dict[str, Any], plan_summary: Dict[str, Any]) -> ExperimentPlanState:
        """Conduct a comprehensive review of the experiment plan."""
        state = state.copy()
        
        # Store comprehensive review results
        state['validation_results'] = validation_results
        state['plan_summary'] = plan_summary
        state['review_stage'] = 'comprehensive_review'
        
        return state
    
    def _generate_review_response(self, state: ExperimentPlanState, review_action: str, validation_results: Dict[str, Any]) -> str:
        """Generate appropriate response based on review action."""
        review_stage = state.get('review_stage', 'initial')
        
        if review_action == "initial_validation":
            return self._format_initial_validation_response(validation_results)
        elif review_action == "address_issues":
            return self._format_validation_issues_response(validation_results)
        elif review_action == "optimization":
            return self._format_optimization_response(state)
        elif review_action == "export_preparation":
            return self._format_export_preparation_response(state)
        elif review_action == "generate_export":
            return self._format_export_generated_response(state)
        elif review_action == "user_approval":
            return self._format_user_approval_response(state)
        elif review_action == "finalization":
            return self._format_finalization_response(state)
        else:
            return self._format_comprehensive_review_response(validation_results)
    
    def _format_initial_validation_response(self, validation_results: Dict[str, Any]) -> str:
        """Format response for initial validation."""
        overall_status = "Complete" if validation_results["status"] == "complete" else "Needs Attention"
        percentage = validation_results["percentage"]
        
        review_summary = f"Completion: {percentage:.1f}%"
        next_action = "Let's address the missing elements." if validation_results["missing_elements"] else "Your plan looks great!"
        
        return format_review_response("initial_review", {
            "review_summary": review_summary,
            "overall_status": overall_status,
            "next_action": next_action
        })
    
    def _format_validation_issues_response(self, validation_results: Dict[str, Any]) -> str:
        """Format response for validation issues."""
        issues = validation_results.get("missing_elements", [])
        validation_issues = "• " + "\n• ".join(issues) if issues else "No issues found"
        
        return format_review_response("validation_issues", {
            "validation_issues": validation_issues
        })
    
    def _format_optimization_response(self, state: ExperimentPlanState) -> str:
        """Format response for optimization suggestions."""
        suggestions = state.get('optimization_suggestions', [])
        optimization_suggestions = "• " + "\n• ".join(suggestions) if suggestions else "No specific optimizations needed"
        
        return format_review_response("optimization_suggestions", {
            "optimization_suggestions": optimization_suggestions
        })
    
    def _format_export_preparation_response(self, state: ExperimentPlanState) -> str:
        """Format response for export preparation."""
        export_format = state.get('export_format', 'json')
        format_info = EXPORT_FORMATS.get(export_format, {})
        
        final_summary = f"Format: {export_format.upper()}\nDescription: {format_info.get('description', 'Unknown format')}"
        
        return format_review_response("export_ready", {
            "final_summary": final_summary
        })
    
    def _format_export_generated_response(self, state: ExperimentPlanState) -> str:
        """Format response for generated export."""
        export_format = state.get('export_format', 'json')
        export_timestamp = state.get('export_timestamp', 'Unknown')
        
        return f"Your experiment plan has been exported in {export_format.upper()} format at {export_timestamp}. The document is ready for download and implementation."
    
    def _format_user_approval_response(self, state: ExperimentPlanState) -> str:
        """Format response for user approval."""
        user_approved = state.get('user_approved', False)
        
        if user_approved:
            return "Thank you for approving the plan! I'll now proceed with finalization."
        else:
            return "I understand you'd like to make changes. Please let me know which sections you'd like to modify."
    
    def _format_finalization_response(self, state: ExperimentPlanState) -> str:
        """Format response for plan finalization."""
        plan_summary = state.get('plan_summary', {})
        
        stats = {
            "total_variables": sum(plan_summary.get('variables', {}).values()),
            "experimental_groups": plan_summary.get('experimental_design', {}).get('experimental_groups', 0),
            "protocol_steps": plan_summary.get('methodology', {}).get('protocol_steps', 0),
            "identified_pitfalls": plan_summary.get('data_planning', {}).get('identified_pitfalls', 0)
        }
        
        plan_statistics = f"Variables: {stats['total_variables']}, Groups: {stats['experimental_groups']}, Steps: {stats['protocol_steps']}, Pitfalls: {stats['identified_pitfalls']}"
        
        return format_review_response("final_approval", {
            "plan_statistics": plan_statistics
        })
    
    def _format_comprehensive_review_response(self, validation_results: Dict[str, Any]) -> str:
        """Format response for comprehensive review."""
        return self._format_initial_validation_response(validation_results)
    
    def _check_user_approval(self, state: ExperimentPlanState) -> bool:
        """Check if the user has approved the plan."""
        return state.get('user_approved', False)
    
    def _generate_optimization_suggestions(self, plan_summary: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on plan content."""
        suggestions = []
        
        # Check variables
        variables = plan_summary.get('variables', {})
        if variables.get('control', 0) < 2:
            suggestions.append("Consider adding more control variables to strengthen your experimental design")
        
        # Check experimental design
        design = plan_summary.get('experimental_design', {})
        if design.get('control_groups', 0) < 2:
            suggestions.append("Adding additional control groups could improve result interpretation")
        
        # Check methodology
        methodology = plan_summary.get('methodology', {})
        if methodology.get('protocol_steps', 0) < 5:
            suggestions.append("Consider breaking down your methodology into more detailed steps")
        
        # Check data planning
        data_planning = plan_summary.get('data_planning', {})
        if data_planning.get('identified_pitfalls', 0) < 3:
            suggestions.append("Identifying more potential pitfalls could improve experiment success")
        
        # Administrative suggestions
        admin = plan_summary.get('administrative', {})
        if not admin.get('ethical_considerations'):
            suggestions.append("Adding ethical considerations documentation would be valuable")
        
        if admin.get('budget') == 'Not estimated':
            suggestions.append("Including a budget estimate would help with resource planning")
        
        return suggestions if suggestions else ["Your plan is well-optimized and ready for implementation!"]
    
    def _determine_export_format(self, user_input: str) -> str:
        """Determine export format from user input."""
        user_input_lower = user_input.lower()
        
        if 'pdf' in user_input_lower:
            return 'pdf'
        elif 'word' in user_input_lower or 'docx' in user_input_lower:
            return 'word'
        elif 'markdown' in user_input_lower or 'md' in user_input_lower:
            return 'markdown'
        else:
            return 'json'  # Default format
    
    def _create_export_document(self, state: ExperimentPlanState, export_format: str) -> Dict[str, Any]:
        """Create export document in specified format."""
        # For now, return a structured representation
        # In a full implementation, this would generate actual PDF/Word documents
        
        export_data = {
            "metadata": generate_export_metadata(state, export_format),
            "experiment_plan": {
                "identification": {
                    "experiment_id": state.get('experiment_id'),
                    "research_query": state.get('research_query'),
                    "objective": state.get('experiment_objective'),
                    "hypothesis": state.get('hypothesis')
                },
                "variables": {
                    "independent": state.get('independent_variables', []),
                    "dependent": state.get('dependent_variables', []),
                    "control": state.get('control_variables', [])
                },
                "experimental_design": {
                    "experimental_groups": state.get('experimental_groups', []),
                    "control_groups": state.get('control_groups', []),
                    "sample_size": state.get('sample_size', {})
                },
                "methodology": {
                    "protocol_steps": state.get('methodology_steps', []),
                    "materials_equipment": state.get('materials_equipment', [])
                },
                "data_planning": {
                    "collection_plan": state.get('data_collection_plan', {}),
                    "analysis_plan": state.get('data_analysis_plan', {}),
                    "potential_pitfalls": state.get('potential_pitfalls', [])
                },
                "administrative": {
                    "expected_outcomes": state.get('expected_outcomes'),
                    "timeline": state.get('timeline'),
                    "budget_estimate": state.get('budget_estimate'),
                    "ethical_considerations": state.get('ethical_considerations')
                }
            }
        }
        
        return export_data 