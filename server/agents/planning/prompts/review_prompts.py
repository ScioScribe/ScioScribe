"""
Prompt templates for the Final Review & Export Agent.

This module contains all prompts and templates used by the Final Review & Export Agent
to guide users through final validation, plan compilation, and export processes.
"""

from typing import Dict, List, Any, Optional

# System prompts for the Final Review & Export Agent
REVIEW_SYSTEM_PROMPT = """You are the Final Review & Export Agent, a specialized AI assistant responsible for the final validation and compilation of complete experiment plans. Your role is to:

1. Conduct comprehensive validation of all experiment plan components
2. Identify any gaps, inconsistencies, or missing elements across all stages
3. Compile a complete, coherent experiment plan from all agent contributions
4. Provide final recommendations for plan optimization and improvement
5. Generate export-ready documents in multiple formats (JSON, PDF, Word)
6. Ensure the plan is ready for implementation and meets scientific standards

You should be thorough, systematic, and quality-focused in your approach. Focus on:
- Comprehensive validation across all planning stages
- Internal consistency checking between plan components
- Scientific rigor and methodological soundness
- Practical feasibility and implementation readiness
- Clear documentation and export preparation
- User satisfaction and final approval

Always ensure the final plan is complete, scientifically sound, and ready for implementation."""

# Question templates for final review
FINAL_VALIDATION_QUESTIONS = [
    "Does your research objective clearly align with your experimental design?",
    "Are all your variables properly defined and measurable?",
    "Do your experimental groups effectively test your hypothesis?",
    "Is your methodology detailed enough for reproducible execution?",
    "Are your data collection and analysis plans appropriate for your research question?",
    "Have you identified the most critical potential pitfalls and mitigation strategies?",
    "Are there any gaps or inconsistencies you've noticed in your plan?",
    "Do you have all necessary resources and equipment for implementation?",
    "Are there any ethical considerations or safety concerns we should address?",
    "What timeline do you expect for executing this experiment?"
]

PLAN_OPTIMIZATION_QUESTIONS = [
    "Are there any aspects of your plan you'd like to refine or improve?",
    "Would you like to add any additional controls or validation steps?",
    "Are there any cost-saving measures or efficiency improvements possible?",
    "Should we consider any alternative approaches or backup plans?",
    "Are there any regulatory or institutional requirements to address?",
    "Would you like to add any additional success metrics or endpoints?",
    "Are there any collaborations or external resources needed?",
    "Should we consider any scale-up or pilot study considerations?",
    "Are there any publication or dissemination plans to incorporate?",
    "Would you like to add any follow-up experiment considerations?"
]

EXPORT_PREPARATION_QUESTIONS = [
    "What format would you prefer for your final experiment plan?",
    "Who will be the primary users of this experiment plan?",
    "Do you need any specific formatting requirements for institutional use?",
    "Should the plan include detailed appendices or supplementary materials?",
    "Do you need separate documents for different audiences (overview vs. detailed protocol)?",
    "Are there any specific sections you'd like emphasized in the final document?",
    "Should we include a budget estimation section?",
    "Do you need a timeline or project management section?",
    "Should we include troubleshooting guides and contingency plans?",
    "Are there any references or citations that should be included?"
]

USER_APPROVAL_QUESTIONS = [
    "Are you satisfied with the completeness of your experiment plan?",
    "Does this plan address your original research question effectively?",
    "Are you confident you can execute this plan with your available resources?",
    "Are there any final modifications you'd like to make?",
    "Do you approve this plan for final export and implementation?",
    "Would you like to save different versions for different use cases?",
    "Are there any sections you'd like to revisit or modify?",
    "Should we create a summary version for quick reference?",
    "Are you ready to proceed with plan finalization and export?",
    "Do you need any additional documentation or support materials?"
]

# Response templates for different review scenarios
REVIEW_RESPONSE_TEMPLATES = {
    "initial_review": """
    Let me conduct a comprehensive review of your experiment plan.
    
    I'll examine each component for completeness and consistency:
    {review_summary}
    
    Overall assessment: {overall_status}
    
    Let's address any areas that need attention. {next_action}
    """,
    
    "validation_issues": """
    I've identified some areas that need attention before finalizing your plan:
    
    {validation_issues}
    
    These issues could impact the success of your experiment. 
    Would you like to address these concerns now?
    """,
    
    "plan_complete": """
    Excellent! Your experiment plan is comprehensive and well-structured:
    
    {plan_summary}
    
    The plan includes all necessary components and appears ready for implementation.
    Are you ready to proceed with export and finalization?
    """,
    
    "optimization_suggestions": """
    Your plan is solid, but I have some suggestions for optimization:
    
    {optimization_suggestions}
    
    These are optional improvements that could enhance your experiment.
    Would you like to implement any of these suggestions?
    """,
    
    "export_ready": """
    Your experiment plan is complete and ready for export!
    
    Plan summary:
    {final_summary}
    
    Available export formats:
    - JSON (for computational use)
    - PDF (for sharing and printing)
    - Word Document (for editing and collaboration)
    
    Which format would you prefer?
    """,
    
    "final_approval": """
    Thank you for your approval! Your experiment plan is now finalized.
    
    Final plan statistics:
    {plan_statistics}
    
    Your plan has been saved and is ready for implementation.
    Good luck with your experiment!
    """
}

# Validation criteria for final review
FINAL_VALIDATION_CRITERIA = {
    "objective_clarity": {
        "description": "Research objective is clear, specific, and measurable",
        "weight": 15,
        "checks": [
            "Objective is specific and well-defined",
            "Hypothesis is testable and falsifiable",
            "Success criteria are clear"
        ]
    },
    
    "variable_completeness": {
        "description": "All variables are properly defined and measurable",
        "weight": 15,
        "checks": [
            "Independent variables are clearly defined",
            "Dependent variables have measurement methods",
            "Control variables are identified and justified"
        ]
    },
    
    "experimental_design": {
        "description": "Experimental design is scientifically sound",
        "weight": 20,
        "checks": [
            "Experimental groups test the hypothesis",
            "Control groups are appropriate",
            "Sample size is statistically adequate"
        ]
    },
    
    "methodology_detail": {
        "description": "Methodology is detailed and reproducible",
        "weight": 20,
        "checks": [
            "Protocol steps are specific and detailed",
            "Materials and equipment are listed",
            "Parameters are clearly specified"
        ]
    },
    
    "data_planning": {
        "description": "Data collection and analysis are well-planned",
        "weight": 15,
        "checks": [
            "Data collection methods are appropriate",
            "Statistical analysis plan is suitable",
            "Potential pitfalls are identified"
        ]
    },
    
    "feasibility": {
        "description": "Plan is feasible and implementable",
        "weight": 15,
        "checks": [
            "Resources are available",
            "Timeline is realistic",
            "Safety considerations are addressed"
        ]
    }
}

# Export format specifications
EXPORT_FORMATS = {
    "json": {
        "description": "Machine-readable format for computational use",
        "extension": ".json",
        "use_cases": ["API integration", "data processing", "archival storage"],
        "structure": "structured_data"
    },
    
    "pdf": {
        "description": "Professional document for sharing and printing",
        "extension": ".pdf",
        "use_cases": ["presentations", "sharing", "printing", "archival"],
        "structure": "formatted_document"
    },
    
    "word": {
        "description": "Editable document for collaboration and modification",
        "extension": ".docx",
        "use_cases": ["editing", "collaboration", "institutional submissions"],
        "structure": "editable_document"
    },
    
    "markdown": {
        "description": "Plain text format for version control and documentation",
        "extension": ".md",
        "use_cases": ["version control", "documentation", "web publishing"],
        "structure": "structured_text"
    }
}

def validate_final_plan_completeness(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the completeness of the entire experiment plan.
    
    Args:
        state: Complete experiment plan state
        
    Returns:
        Validation results dictionary
    """
    total_score = 0
    max_score = 100
    validation_results = {}
    missing_elements = []
    
    # Check each validation criterion
    for criterion_key, criterion in FINAL_VALIDATION_CRITERIA.items():
        criterion_score = 0
        criterion_max = criterion["weight"]
        criterion_issues = []
        
        # Perform specific checks based on criterion
        if criterion_key == "objective_clarity":
            if state.get('experiment_objective'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing experiment objective")
            
            if state.get('hypothesis'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing hypothesis")
            
            if state.get('expected_outcomes'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing expected outcomes")
        
        elif criterion_key == "variable_completeness":
            if state.get('independent_variables'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing independent variables")
            
            if state.get('dependent_variables'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing dependent variables")
            
            if state.get('control_variables'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing control variables")
        
        elif criterion_key == "experimental_design":
            if state.get('experimental_groups'):
                criterion_score += 7
            else:
                criterion_issues.append("Missing experimental groups")
            
            if state.get('control_groups'):
                criterion_score += 7
            else:
                criterion_issues.append("Missing control groups")
            
            if state.get('sample_size'):
                criterion_score += 6
            else:
                criterion_issues.append("Missing sample size calculation")
        
        elif criterion_key == "methodology_detail":
            if state.get('methodology_steps'):
                criterion_score += 10
            else:
                criterion_issues.append("Missing methodology steps")
            
            if state.get('materials_equipment'):
                criterion_score += 10
            else:
                criterion_issues.append("Missing materials and equipment list")
        
        elif criterion_key == "data_planning":
            if state.get('data_collection_plan'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing data collection plan")
            
            if state.get('data_analysis_plan'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing data analysis plan")
            
            if state.get('potential_pitfalls'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing potential pitfalls")
        
        elif criterion_key == "feasibility":
            if state.get('timeline'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing timeline")
            
            if state.get('ethical_considerations'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing ethical considerations")
            
            if state.get('budget_estimate'):
                criterion_score += 5
            else:
                criterion_issues.append("Missing budget estimate")
        
        # Store criterion results
        validation_results[criterion_key] = {
            "score": criterion_score,
            "max_score": criterion_max,
            "percentage": (criterion_score / criterion_max) * 100,
            "issues": criterion_issues,
            "status": "complete" if criterion_score == criterion_max else "incomplete"
        }
        
        total_score += criterion_score
        if criterion_issues:
            missing_elements.extend(criterion_issues)
    
    # Overall validation results
    overall_percentage = (total_score / max_score) * 100
    
    return {
        "overall_score": total_score,
        "max_score": max_score,
        "percentage": overall_percentage,
        "status": "complete" if overall_percentage >= 90 else "needs_attention",
        "missing_elements": missing_elements,
        "criterion_results": validation_results,
        "recommendations": _generate_completion_recommendations(validation_results)
    }

def _generate_completion_recommendations(validation_results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on validation results."""
    recommendations = []
    
    for criterion_key, results in validation_results.items():
        if results["status"] == "incomplete":
            criterion_name = criterion_key.replace("_", " ").title()
            recommendations.append(f"Complete {criterion_name}: {', '.join(results['issues'])}")
    
    return recommendations

def generate_plan_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive summary of the experiment plan.
    
    Args:
        state: Complete experiment plan state
        
    Returns:
        Plan summary dictionary
    """
    summary = {
        "experiment_id": state.get('experiment_id', 'Unknown'),
        "research_query": state.get('research_query', 'Not specified'),
        "objective": state.get('experiment_objective', 'Not defined'),
        "hypothesis": state.get('hypothesis', 'Not specified'),
        "variables": {
            "independent": len(state.get('independent_variables', [])),
            "dependent": len(state.get('dependent_variables', [])),
            "control": len(state.get('control_variables', []))
        },
        "experimental_design": {
            "experimental_groups": len(state.get('experimental_groups', [])),
            "control_groups": len(state.get('control_groups', [])),
            "sample_size": state.get('sample_size') or {}
        },
        "methodology": {
            "protocol_steps": len(state.get('methodology_steps', [])),
            "materials_equipment": len(state.get('materials_equipment', []))
        },
        "data_planning": {
            "collection_methods": len((state.get('data_collection_plan') or {}).get('methods', [])),
            "analysis_approaches": len((state.get('data_analysis_plan') or {}).get('statistical_tests', [])),
            "identified_pitfalls": len(state.get('potential_pitfalls', []))
        },
        "administrative": {
            "timeline": (state.get('timeline') or {}).get('duration', 'Not specified'),
            "budget": (state.get('budget_estimate') or {}).get('total', 'Not estimated'),
            "ethical_considerations": bool(state.get('ethical_considerations'))
        },
        "completion_status": {
            "completed_stages": len(state.get('completed_stages', [])),
            "current_stage": state.get('current_stage', 'Unknown'),
            "total_stages": len(state.get('completed_stages', []))
        }
    }
    
    return summary

def format_review_response(template_key: str, context: Dict[str, Any]) -> str:
    """
    Format a review response using the specified template.
    
    Args:
        template_key: Key for the response template
        context: Context variables for template formatting
        
    Returns:
        Formatted response string
    """
    template = REVIEW_RESPONSE_TEMPLATES.get(template_key, "")
    
    try:
        return template.format(**context)
    except KeyError as e:
        return f"Error formatting response: Missing context key {e}"

def generate_export_metadata(state: Dict[str, Any], export_format: str) -> Dict[str, Any]:
    """
    Generate metadata for export based on the selected format.
    
    Args:
        state: Complete experiment plan state
        export_format: Desired export format
        
    Returns:
        Export metadata dictionary
    """
    format_info = EXPORT_FORMATS.get(export_format, {})
    
    metadata = {
        "format": export_format,
        "extension": format_info.get("extension", ""),
        "description": format_info.get("description", ""),
        "generated_at": state.get('updated_at', ''),
        "experiment_id": state.get('experiment_id', ''),
        "title": f"Experiment Plan: {state.get('experiment_objective', 'Untitled')}",
        "author": "ScioScribe Planning Agent",
        "version": "1.0",
        "structure": format_info.get("structure", "unknown")
    }
    
    return metadata 