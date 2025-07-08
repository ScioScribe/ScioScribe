"""
Prompt templates for the Data Planning & QA Agent.

This module contains all prompts and templates used by the Data Planning & QA Agent
to guide users through data collection planning, statistical analysis recommendations,
and troubleshooting strategies.
"""

from typing import Dict, List, Any, Optional

# System prompts for the Data Planning & QA Agent
DATA_SYSTEM_PROMPT = """You are the Data Planning & QA Agent, a specialized AI assistant helping researchers plan comprehensive data collection and analysis strategies. Your role is to:

1. Design data collection plans with appropriate methods, timing, and formats
2. Recommend statistical analysis approaches based on experimental design and variables
3. Suggest visualization strategies for effective data presentation
4. Identify potential experimental pitfalls and provide mitigation strategies
5. Define success criteria and expected outcomes
6. Create troubleshooting guides for common experimental problems

You should be analytical, thorough, and practical in your approach. Focus on:
- Appropriate data collection methods for the experimental design
- Statistical tests that match the data types and research questions
- Clear visualization strategies that highlight key findings
- Proactive identification of potential problems and solutions
- Realistic success criteria and outcome expectations
- Actionable troubleshooting guidance

Always ensure your recommendations are scientifically sound and practically implementable."""

# Question templates for data planning
DATA_COLLECTION_QUESTIONS = [
    "What specific data points will you need to collect to test your hypothesis?",
    "At what time intervals will you take measurements or collect samples?",
    "What format will your data be in (numerical, categorical, ordinal, binary)?",
    "How will you record and store your data during the experiment?",
    "What software or tools will you use for data collection and management?",
    "Are there any automated data collection systems you'll be using?",
    "How will you ensure data quality and accuracy during collection?",
    "What backup or redundancy measures will you have for your data?",
    "Are there any regulatory or ethical considerations for your data collection?",
    "What metadata will you need to track alongside your primary data?"
]

STATISTICAL_ANALYSIS_QUESTIONS = [
    "What is your primary research question that needs statistical testing?",
    "Are you comparing groups, looking for correlations, or testing relationships?",
    "What type of data will you be analyzing (continuous, categorical, count data)?",
    "Do you expect your data to follow a normal distribution?",
    "Are there any assumptions you need to check before statistical testing?",
    "What significance level will you use for your statistical tests?",
    "Do you need to correct for multiple comparisons?",
    "Are there any confounding variables you need to account for?",
    "What statistical software are you planning to use?",
    "Do you need help interpreting the results of your statistical tests?"
]

VISUALIZATION_QUESTIONS = [
    "What key findings do you want to highlight in your visualizations?",
    "Who is your target audience for these visualizations?",
    "What type of charts or graphs would best represent your data?",
    "Do you need to show individual data points or summary statistics?",
    "Are there any specific formatting requirements for your visualizations?",
    "Will you need publication-ready figures or presentation slides?",
    "Do you want to show statistical significance in your plots?",
    "Are there any color schemes or accessibility considerations?",
    "What software will you use for creating visualizations?",
    "Do you need interactive or static visualizations?"
]

PITFALL_IDENTIFICATION_QUESTIONS = [
    "What are the most critical steps in your experimental protocol?",
    "Where have you seen similar experiments fail or have issues?",
    "What environmental factors could affect your results?",
    "Are there any technical limitations with your equipment or methods?",
    "What sample size issues might you encounter?",
    "Are there any contamination or quality control risks?",
    "What time-sensitive aspects of your experiment need special attention?",
    "Are there any seasonal or temporal factors that could impact results?",
    "What are the most common errors in your type of experiment?",
    "Do you have contingency plans for equipment failures or other issues?"
]

SUCCESS_CRITERIA_QUESTIONS = [
    "What would constitute a successful outcome for your experiment?",
    "What specific results would support your hypothesis?",
    "What magnitude of effect would be biologically or practically significant?",
    "Are there any secondary outcomes you're hoping to observe?",
    "What would indicate that your experiment needs to be repeated or modified?",
    "How will you determine if your results are reliable and reproducible?",
    "What quality control measures will indicate successful execution?",
    "Are there any negative results that would still be valuable?",
    "What statistical power do you need to detect meaningful effects?",
    "How will you validate your findings?"
]

# Response templates for data planning
DATA_RESPONSE_TEMPLATES = {
    "data_collection_needed": """
    Let's plan how you'll collect your data systematically.
    
    {context}
    
    {specific_question}
    """,
    
    "statistical_analysis_needed": """
    Now let's determine the appropriate statistical approach for your data.
    
    Based on your experimental design:
    {design_context}
    
    {analysis_question}
    """,
    
    "visualization_planning": """
    Let's plan how you'll visualize and present your results.
    
    {data_context}
    
    {visualization_question}
    """,
    
    "pitfall_identification": """
    Let's identify potential issues and create mitigation strategies.
    
    {experimental_context}
    
    {pitfall_question}
    """,
    
    "success_criteria": """
    Let's define what success looks like for your experiment.
    
    {objective_context}
    
    {success_question}
    """,
    
    "troubleshooting_guide": """
    Let's create a troubleshooting guide for common issues.
    
    {protocol_context}
    
    {troubleshooting_question}
    """,
    
    "data_planning_complete": """
    Excellent! Your data collection and analysis plan is now complete:
    
    {data_plan_summary}
    
    This plan includes {collection_methods_count} data collection methods, 
    {statistical_tests_count} statistical approaches, and {pitfalls_count} identified potential issues.
    
    Ready to move to the final review stage?
    """
}

# Statistical test recommendations based on data types and design
STATISTICAL_TEST_RECOMMENDATIONS = {
    "two_group_continuous": {
        "parametric": "Independent t-test",
        "non_parametric": "Mann-Whitney U test",
        "description": "Comparing means between two independent groups"
    },
    
    "multiple_group_continuous": {
        "parametric": "One-way ANOVA",
        "non_parametric": "Kruskal-Wallis test",
        "description": "Comparing means among multiple groups"
    },
    
    "paired_continuous": {
        "parametric": "Paired t-test",
        "non_parametric": "Wilcoxon signed-rank test",
        "description": "Comparing before/after or matched pairs"
    },
    
    "correlation": {
        "parametric": "Pearson correlation",
        "non_parametric": "Spearman correlation",
        "description": "Assessing relationship between continuous variables"
    },
    
    "categorical_association": {
        "test": "Chi-square test",
        "alternative": "Fisher's exact test",
        "description": "Testing association between categorical variables"
    },
    
    "regression": {
        "linear": "Linear regression",
        "logistic": "Logistic regression",
        "description": "Modeling relationships and predictions"
    }
}

# Visualization recommendations based on data types
VISUALIZATION_RECOMMENDATIONS = {
    "continuous_single": {
        "histogram": "Distribution of a single continuous variable",
        "box_plot": "Summary statistics and outliers",
        "density_plot": "Smooth distribution curve"
    },
    
    "continuous_comparison": {
        "box_plot": "Compare distributions between groups",
        "violin_plot": "Distribution shape and summary statistics",
        "bar_chart": "Mean values with error bars"
    },
    
    "categorical": {
        "bar_chart": "Frequency or proportions of categories",
        "pie_chart": "Proportions of a whole (use sparingly)",
        "stacked_bar": "Comparing categories across groups"
    },
    
    "time_series": {
        "line_plot": "Changes over time",
        "area_plot": "Cumulative changes",
        "heat_map": "Patterns across time and categories"
    },
    
    "correlation": {
        "scatter_plot": "Relationship between two continuous variables",
        "correlation_matrix": "Multiple variable relationships",
        "regression_line": "Fitted relationship with confidence intervals"
    }
}

# Common experimental pitfalls and solutions
COMMON_PITFALLS = {
    "sample_size": {
        "issue": "Insufficient sample size leading to underpowered study",
        "likelihood": "high",
        "mitigation": "Perform power analysis before starting, consider pilot studies"
    },
    
    "contamination": {
        "issue": "Cross-contamination between samples or groups",
        "likelihood": "medium",
        "mitigation": "Use proper sterile technique, separate workspaces, control samples"
    },
    
    "measurement_error": {
        "issue": "Inconsistent or inaccurate measurements",
        "likelihood": "medium",
        "mitigation": "Calibrate instruments, use technical replicates, train operators"
    },
    
    "temporal_effects": {
        "issue": "Time-dependent changes affecting results",
        "likelihood": "medium",
        "mitigation": "Randomize timing, use time-matched controls, monitor temporal trends"
    },
    
    "batch_effects": {
        "issue": "Systematic differences between experimental batches",
        "likelihood": "high",
        "mitigation": "Randomize samples across batches, include batch controls"
    },
    
    "equipment_failure": {
        "issue": "Instrument malfunction or inconsistent performance",
        "likelihood": "medium",
        "mitigation": "Regular maintenance, backup equipment, quality control checks"
    },
    
    "environmental_variation": {
        "issue": "Uncontrolled environmental factors affecting results",
        "likelihood": "high",
        "mitigation": "Monitor and control temperature, humidity, lighting conditions"
    }
}

def get_data_domain_guidance(research_query: str, experimental_design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get general guidance for data planning based on research query and experimental design.
    
    Args:
        research_query: The research question
        experimental_design: Current experimental design
        
    Returns:
        General guidance dictionary
    """
    # Extract key information from experimental design
    variables = experimental_design.get('variables', {})
    groups = experimental_design.get('groups', [])
    
    # Determine data collection approach
    data_collection_approach = _determine_data_collection_approach(variables, groups)
    
    # Suggest statistical tests
    statistical_suggestions = _suggest_statistical_tests(variables, groups)
    
    # Recommend visualizations
    visualization_suggestions = _suggest_visualizations(variables, groups)
    
    # Identify likely pitfalls
    likely_pitfalls = _identify_likely_pitfalls(research_query, experimental_design)
    
    return {
        "data_collection": data_collection_approach,
        "statistical_tests": statistical_suggestions,
        "visualizations": visualization_suggestions,
        "pitfalls": likely_pitfalls,
        "success_criteria": _generate_success_criteria(research_query, variables)
    }

def _determine_data_collection_approach(variables: Dict[str, Any], groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Determine appropriate data collection approach based on variables and groups."""
    approach = {
        "methods": [],
        "timing": "single_timepoint",
        "format": "quantitative",
        "storage": "digital"
    }
    
    # Check for time-series data
    if any('time' in str(var).lower() for var in variables.get('independent_variables', [])):
        approach["timing"] = "multiple_timepoints"
    
    # Check for qualitative data
    if any('qualitative' in str(var).lower() for var in variables.get('dependent_variables', [])):
        approach["format"] = "mixed"
    
    # Suggest collection methods
    approach["methods"] = [
        "Standardized measurement protocols",
        "Quality control checkpoints",
        "Data validation procedures",
        "Backup and redundancy measures"
    ]
    
    return approach

def _suggest_statistical_tests(variables: Dict[str, Any], groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Suggest appropriate statistical tests based on variables and groups."""
    suggestions = []
    
    # Basic group comparison
    if len(groups) == 2:
        suggestions.append({
            "test": "Two-group comparison",
            "parametric": "Independent t-test",
            "non_parametric": "Mann-Whitney U test",
            "assumptions": "Check normality and equal variances"
        })
    elif len(groups) > 2:
        suggestions.append({
            "test": "Multiple group comparison",
            "parametric": "One-way ANOVA",
            "non_parametric": "Kruskal-Wallis test",
            "assumptions": "Check normality and homoscedasticity"
        })
    
    # Add correlation if multiple continuous variables
    dep_vars = variables.get('dependent_variables', [])
    if len(dep_vars) > 1:
        suggestions.append({
            "test": "Correlation analysis",
            "parametric": "Pearson correlation",
            "non_parametric": "Spearman correlation",
            "assumptions": "Check linearity and normality"
        })
    
    return suggestions

def _suggest_visualizations(variables: Dict[str, Any], groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Suggest appropriate visualizations based on variables and groups."""
    suggestions = []
    
    # Group comparisons
    if len(groups) >= 2:
        suggestions.append({
            "type": "Box plot",
            "purpose": "Compare distributions between groups",
            "software": "R, Python, GraphPad Prism"
        })
        
        suggestions.append({
            "type": "Bar chart with error bars",
            "purpose": "Compare means between groups",
            "software": "Excel, R, Python, GraphPad Prism"
        })
    
    # Individual data points
    suggestions.append({
        "type": "Scatter plot",
        "purpose": "Show individual data points and relationships",
        "software": "R, Python, GraphPad Prism"
    })
    
    # Distribution visualization
    suggestions.append({
        "type": "Histogram",
        "purpose": "Show data distribution",
        "software": "R, Python, Excel"
    })
    
    return suggestions

def _identify_likely_pitfalls(research_query: str, experimental_design: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify likely pitfalls based on research query and experimental design."""
    pitfalls = []
    
    # Always include these common pitfalls
    pitfalls.extend([
        COMMON_PITFALLS["sample_size"],
        COMMON_PITFALLS["measurement_error"],
        COMMON_PITFALLS["batch_effects"]
    ])
    
    # Add specific pitfalls based on context
    if 'cell' in research_query.lower() or 'culture' in research_query.lower():
        pitfalls.append(COMMON_PITFALLS["contamination"])
    
    if 'time' in research_query.lower() or 'temporal' in research_query.lower():
        pitfalls.append(COMMON_PITFALLS["temporal_effects"])
    
    # Add environmental variation for lab-based experiments
    pitfalls.append(COMMON_PITFALLS["environmental_variation"])
    
    return pitfalls

def _generate_success_criteria(research_query: str, variables: Dict[str, Any]) -> List[str]:
    """Generate success criteria based on research query and variables."""
    criteria = [
        "Data collection completed according to protocol",
        "All planned measurements obtained successfully",
        "Quality control checks passed",
        "Statistical power achieved for primary endpoint"
    ]
    
    # Add specific criteria based on variables
    dep_vars = variables.get('dependent_variables', [])
    if dep_vars:
        criteria.append(f"Meaningful change detected in {len(dep_vars)} outcome variable(s)")
    
    criteria.extend([
        "Results are reproducible and consistent",
        "Findings address the original research question",
        "Data meets publication or reporting standards"
    ])
    
    return criteria

def format_data_response(template_key: str, context: Dict[str, Any]) -> str:
    """
    Format a data planning response using the specified template.
    
    Args:
        template_key: Key for the response template
        context: Context variables for template formatting
        
    Returns:
        Formatted response string
    """
    template = DATA_RESPONSE_TEMPLATES.get(template_key, "")
    
    try:
        return template.format(**context)
    except KeyError as e:
        return f"Error formatting response: Missing context key {e}"

def validate_data_plan_completeness(data_collection_plan: Dict[str, Any], 
                                  data_analysis_plan: Dict[str, Any],
                                  potential_pitfalls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate the completeness of the data planning stage.
    
    Args:
        data_collection_plan: Data collection plan
        data_analysis_plan: Data analysis plan
        potential_pitfalls: List of identified pitfalls
        
    Returns:
        Validation results dictionary
    """
    score = 0
    max_score = 100
    missing_elements = []
    
    # Check data collection plan (40 points)
    if data_collection_plan.get('methods'):
        score += 15
    else:
        missing_elements.append("Data collection methods")
    
    if data_collection_plan.get('timing'):
        score += 10
    else:
        missing_elements.append("Data collection timing")
    
    if data_collection_plan.get('formats'):
        score += 10
    else:
        missing_elements.append("Data formats specification")
    
    if data_collection_plan.get('storage'):
        score += 5
    else:
        missing_elements.append("Data storage plan")
    
    # Check data analysis plan (40 points)
    if data_analysis_plan.get('statistical_tests'):
        score += 20
    else:
        missing_elements.append("Statistical analysis plan")
    
    if data_analysis_plan.get('visualizations'):
        score += 10
    else:
        missing_elements.append("Visualization strategy")
    
    if data_analysis_plan.get('software'):
        score += 5
    else:
        missing_elements.append("Analysis software specification")
    
    if data_analysis_plan.get('expected_outcomes'):
        score += 5
    else:
        missing_elements.append("Expected outcomes definition")
    
    # Check pitfalls identification (20 points)
    if potential_pitfalls and len(potential_pitfalls) >= 3:
        score += 20
    elif potential_pitfalls and len(potential_pitfalls) >= 1:
        score += 10
    else:
        missing_elements.append("Potential pitfalls identification")
    
    return {
        "score": score,
        "max_score": max_score,
        "percentage": (score / max_score) * 100,
        "is_complete": score >= 80,
        "missing_elements": missing_elements
    }

def generate_troubleshooting_guide(methodology_steps: List[Dict[str, Any]], 
                                 potential_pitfalls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate a troubleshooting guide based on methodology and pitfalls.
    
    Args:
        methodology_steps: List of methodology steps
        potential_pitfalls: List of identified pitfalls
        
    Returns:
        List of troubleshooting items
    """
    troubleshooting_guide = []
    
    # Add general troubleshooting items
    troubleshooting_guide.extend([
        {
            "issue": "Unexpected results or outliers",
            "symptoms": "Data points far from expected range",
            "solution": "Check calculation errors, instrument calibration, and sample preparation"
        },
        {
            "issue": "Inconsistent results between replicates",
            "symptoms": "High variability in technical or biological replicates",
            "solution": "Review technique consistency, check for contamination, increase sample size"
        },
        {
            "issue": "Equipment malfunction",
            "symptoms": "Instrument error messages, inconsistent readings",
            "solution": "Check calibration, contact technical support, use backup equipment"
        }
    ])
    
    # Add pitfall-specific troubleshooting
    for pitfall in potential_pitfalls:
        troubleshooting_guide.append({
            "issue": pitfall.get('issue', 'Unknown issue'),
            "symptoms": f"Indicators of {pitfall.get('issue', 'issue')}",
            "solution": pitfall.get('mitigation', 'Apply appropriate mitigation strategy')
        })
    
    return troubleshooting_guide 