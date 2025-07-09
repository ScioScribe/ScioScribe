"""
Prompts and templates for the Experimental Design Agent.

This module provides prompts, response templates, and domain-specific guidance
for designing experiments, selecting control groups, and calculating statistical power.
"""

from typing import Dict, List, Any, Optional


# System prompt for the design agent
DESIGN_SYSTEM_PROMPT = """
You are an expert experimental design consultant specializing in biotech and laboratory research.
Your role is to guide researchers through designing robust experimental frameworks that will
yield statistically valid and scientifically meaningful results.

Key responsibilities:
1. Design experimental groups that test the hypothesis effectively
2. Recommend appropriate control groups (negative, positive, vehicle, technical)
3. Calculate statistical power and determine optimal sample sizes
4. Suggest randomization and blinding strategies
5. Identify potential confounding variables and design solutions

Always consider:
- Statistical power and effect size
- Practical constraints and resource limitations
- Domain-specific best practices
- Ethical considerations
- Reproducibility and replicability

CRITICAL OUTPUT FORMAT REQUIREMENTS:
When generating experimental groups, you MUST include:
- name: A descriptive name for the group
- description: A brief explanation of the group's purpose
- conditions: A dictionary mapping independent variable names to their specific values

Example experimental group structure:
{{
    "name": "10 µM Compound X",
    "description": "Test group receiving 10 µM of Compound X to assess its effect on cell viability.",
    "conditions": {{"Compound X Concentration": 10, "Treatment Duration": "48 hours"}}
}}

The conditions field is MANDATORY and must contain key-value pairs where:
- Keys are the names of independent variables being manipulated
- Values are the specific levels/values for this experimental group

For control groups, include:
- name: A descriptive name
- type: The control type (negative, positive, vehicle, technical)
- purpose: Clear explanation of what this control validates
- description: Brief description of the control setup

Provide clear, actionable recommendations with scientific justification.
"""

# Questions for experimental group design
EXPERIMENTAL_GROUP_QUESTIONS = [
    "What specific conditions or treatments will you test in your experiment?",
    "How many different levels or doses of your independent variable will you test?",
    "What are the key experimental conditions that will help test your hypothesis?",
    "Are there any specific treatment groups or experimental manipulations you want to include?",
    "What experimental conditions will allow you to measure the effect of your independent variable?",
    "Do you need to test multiple concentrations, doses, or intensities?",
    "What treatment combinations are essential for your research question?",
    "Are there any time-course or duration considerations for your experimental groups?"
]

# Questions for control group design
CONTROL_GROUP_QUESTIONS = [
    "What would be an appropriate negative control for your experiment?",
    "Do you have a positive control that should produce a known result?",
    "Will you need a vehicle control (e.g., solvent, buffer, carrier)?",
    "Are there any technical controls needed to validate your methods?",
    "What control conditions will help you interpret your results?",
    "Do you need controls for any equipment, reagents, or environmental factors?",
    "Are there any baseline or reference conditions that should be included?",
    "What controls will help rule out alternative explanations?"
]

# Questions for sample size and power analysis
SAMPLE_SIZE_QUESTIONS = [
    "What effect size do you expect to detect in your experiment?",
    "What is your desired statistical power (typically 80% or higher)?",
    "What significance level (alpha) will you use (typically 0.05)?",
    "How many biological replicates can you realistically include?",
    "How many technical replicates will you perform for each biological replicate?",
    "Are there any practical constraints on your sample size?",
    "What is the smallest meaningful difference you want to detect?",
    "Do you have any preliminary data to estimate variability?"
]

# Response templates for different design stages
DESIGN_RESPONSE_TEMPLATES = {
    "experimental_groups_needed": """
    Now let's design your experimental groups. Based on your variables: {variables}
    
    I need to understand what specific conditions you want to test. This will help ensure
    your experimental design can effectively test your hypothesis.
    """,
    
    "control_groups_needed": """
    Excellent experimental groups! Now let's design appropriate control groups.
    
    Here are some control types I recommend for your experiment:
    {suggested_controls}
    
    Which of these controls are most relevant to your experimental design?
    """,
    
    "sample_size_needed": """
    Great design structure! Now let's determine the optimal sample size.
    
    With {design_complexity} total groups, we need to calculate the sample size
    that will give you sufficient statistical power to detect meaningful effects.
    
    What effect size do you expect to detect? (small: 0.2, medium: 0.5, large: 0.8)
    """,
    
    "design_complete": """
    Excellent! Your experimental design is complete:
    
    {design_summary}
    
    This design should provide robust, statistically valid results for your research question.
    Ready to move on to developing the detailed methodology?
    """,
    
    "needs_refinement": """
    Your experimental design needs some refinement:
    
    {specific_guidance}
    
    {follow_up_question}
    """,
    
    "statistical_power_low": """
    Your current sample size may not provide sufficient statistical power.
    
    Recommended sample size: {recommended_n} per group
    Current sample size: {current_n} per group
    
    Would you like to adjust your sample size or effect size expectations?
    """
}

# Statistical considerations and guidelines
STATISTICAL_CONSIDERATIONS = {
    "minimum_sample_size": 3,
    "recommended_power": 0.8,
    "standard_alpha": 0.05,
    "effect_sizes": {
        "small": 0.2,
        "medium": 0.5,
        "large": 0.8
    },
    "control_types": [
        "negative",
        "positive", 
        "vehicle",
        "technical",
        "baseline"
    ]
}

# Domain-specific design guidance
DOMAIN_GUIDANCE = {
    "biotechnology": {
        "common_controls": [
            {"type": "negative", "description": "Untreated cells or samples"},
            {"type": "vehicle", "description": "Solvent or buffer control"},
            {"type": "positive", "description": "Known treatment with expected effect"},
            {"type": "technical", "description": "Control for handling/processing"}
        ],
        "typical_replicates": {"biological": 3, "technical": 3},
        "design_considerations": [
            "Cell passage number consistency",
            "Batch effects in reagents",
            "Incubation time standardization",
            "Environmental control (temperature, CO2)",
            "Contamination controls"
        ]
    },
    "cell_biology": {
        "common_controls": [
            {"type": "negative", "description": "Untreated cells"},
            {"type": "vehicle", "description": "DMSO or media control"},
            {"type": "positive", "description": "Known pathway activator/inhibitor"},
            {"type": "technical", "description": "Cell viability control"}
        ],
        "typical_replicates": {"biological": 3, "technical": 3},
        "design_considerations": [
            "Cell line authentication",
            "Passage number effects",
            "Serum batch variability",
            "Mycoplasma testing",
            "Cell density effects"
        ]
    },
    "biochemistry": {
        "common_controls": [
            {"type": "negative", "description": "No enzyme or substrate"},
            {"type": "positive", "description": "Known substrate/inhibitor"},
            {"type": "vehicle", "description": "Buffer or solvent control"},
            {"type": "technical", "description": "Heat-inactivated enzyme"}
        ],
        "typical_replicates": {"biological": 3, "technical": 3},
        "design_considerations": [
            "Enzyme activity validation",
            "Substrate concentration optimization",
            "Temperature and pH control",
            "Cofactor requirements",
            "Inhibitor specificity"
        ]
    },
    "pharmacology": {
        "common_controls": [
            {"type": "negative", "description": "Vehicle-treated group"},
            {"type": "positive", "description": "Standard drug control"},
            {"type": "vehicle", "description": "Solvent control"},
            {"type": "technical", "description": "Dosing accuracy control"}
        ],
        "typical_replicates": {"biological": 6, "technical": 2},
        "design_considerations": [
            "Dose-response relationships",
            "Time-course effects",
            "Drug stability",
            "Pharmacokinetic factors",
            "Species/strain differences"
        ]
    }
}


def get_design_domain_guidance(research_query: str, objective: str, variables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Provide domain-specific guidance for experimental design.
    
    Args:
        research_query: The research question
        objective: The experiment objective
        variables: List of experimental variables
        
    Returns:
        Domain-specific guidance dictionary
    """
    # Simple domain detection based on keywords
    domain = detect_research_domain(research_query + " " + (objective or ""))
    
    base_guidance = DOMAIN_GUIDANCE.get(domain, DOMAIN_GUIDANCE["biotechnology"])
    
    # Customize questions based on variables
    suggested_questions = {
        "experimental": _customize_experimental_questions(variables, domain),
        "control": _customize_control_questions(variables, domain),
        "sample_size": _customize_sample_size_questions(variables, domain)
    }
    
    return {
        "domain": domain,
        "common_controls": base_guidance["common_controls"],
        "typical_replicates": base_guidance["typical_replicates"],
        "design_considerations": base_guidance["design_considerations"],
        "suggested_questions": suggested_questions
    }


def detect_research_domain(text: str) -> str:
    """Detect research domain from text."""
    text_lower = text.lower()
    
    if any(term in text_lower for term in ["cell", "culture", "transfection", "protein"]):
        return "cell_biology"
    elif any(term in text_lower for term in ["enzyme", "kinetic", "binding", "assay"]):
        return "biochemistry"
    elif any(term in text_lower for term in ["drug", "compound", "dose", "treatment"]):
        return "pharmacology"
    else:
        return "biotechnology"


def _customize_experimental_questions(variables: List[Dict[str, Any]], domain: str) -> List[str]:
    """Customize experimental questions based on variables."""
    questions = EXPERIMENTAL_GROUP_QUESTIONS.copy()
    
    if variables:
        var_names = [var.get('name', '') for var in variables[:3]]
        questions.insert(0, f"How will you vary {', '.join(var_names)} in your experimental groups?")
    
    return questions[:5]  # Limit to 5 questions


def _customize_control_questions(variables: List[Dict[str, Any]], domain: str) -> List[str]:
    """Customize control questions based on variables and domain."""
    questions = CONTROL_GROUP_QUESTIONS.copy()
    
    domain_guidance = DOMAIN_GUIDANCE.get(domain, {})
    common_controls = domain_guidance.get("common_controls", [])
    
    if common_controls:
        control_types = [control["type"] for control in common_controls]
        questions.insert(0, f"Which of these controls are relevant: {', '.join(control_types)}?")
    
    return questions[:5]  # Limit to 5 questions


def _customize_sample_size_questions(variables: List[Dict[str, Any]], domain: str) -> List[str]:
    """Customize sample size questions based on domain."""
    questions = SAMPLE_SIZE_QUESTIONS.copy()
    
    domain_guidance = DOMAIN_GUIDANCE.get(domain, {})
    typical_replicates = domain_guidance.get("typical_replicates", {})
    
    if typical_replicates:
        bio_reps = typical_replicates.get("biological", 3)
        tech_reps = typical_replicates.get("technical", 3)
        questions.insert(0, f"For {domain}, typically {bio_reps} biological and {tech_reps} technical replicates are used. Does this fit your experiment?")
    
    return questions[:5]  # Limit to 5 questions


def format_design_response(template_key: str, context: Dict[str, Any]) -> str:
    """Format a design response using templates."""
    template = DESIGN_RESPONSE_TEMPLATES.get(template_key, "")
    
    try:
        return template.format(**context)
    except KeyError as e:
        return f"Response template error: missing key {e}"


def suggest_control_groups(domain: str, variables: List[Dict[str, Any]]) -> List[str]:
    """Suggest appropriate control groups for the domain."""
    domain_guidance = DOMAIN_GUIDANCE.get(domain, DOMAIN_GUIDANCE["biotechnology"])
    controls = domain_guidance["common_controls"]
    
    suggestions = []
    for control in controls:
        suggestions.append(f"• {control['type'].title()} Control: {control['description']}")
    
    return suggestions


def validate_experimental_design(
    experimental_groups: List[Dict[str, Any]], 
    control_groups: List[Dict[str, Any]], 
    sample_size: Dict[str, Any],
    independent_vars: List[Dict[str, Any]],
    dependent_vars: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate the completeness and quality of experimental design.
    
    Args:
        experimental_groups: List of experimental groups
        control_groups: List of control groups  
        sample_size: Sample size information
        independent_vars: Independent variables
        dependent_vars: Dependent variables
        
    Returns:
        Validation results dictionary
    """
    missing_elements = []
    suggestions = []
    score = 0
    
    # Check experimental groups
    if not experimental_groups:
        missing_elements.append("Experimental groups")
    else:
        score += 30
        if len(experimental_groups) < len(independent_vars):
            suggestions.append("Consider if you need more experimental groups to test all variables")
    
    # Check control groups
    if not control_groups:
        missing_elements.append("Control groups")
    else:
        score += 25
        control_types = [group.get('type', '') for group in control_groups]
        if 'negative' not in control_types:
            suggestions.append("Consider adding a negative control group")
        if 'positive' not in control_types:
            suggestions.append("Consider adding a positive control group")
    
    # Check sample size
    if not sample_size:
        missing_elements.append("Sample size calculation")
    else:
        score += 25
        power_analysis = sample_size.get('power_analysis', {})
        if not power_analysis:
            suggestions.append("Perform statistical power analysis")
        elif power_analysis.get('power', 0) < 0.8:
            suggestions.append("Consider increasing sample size for better statistical power")
    
    # Check design completeness
    if experimental_groups and control_groups and sample_size:
        score += 20
        total_groups = len(experimental_groups) + len(control_groups)
        if total_groups < 3:
            suggestions.append("Consider if your design has sufficient groups for comparison")
    
    # Additional design quality checks
    if score >= 60:
        if not any('randomization' in str(group).lower() for group in experimental_groups):
            suggestions.append("Consider randomization strategy for group assignment")
        if not any('blinding' in str(group).lower() for group in experimental_groups):
            suggestions.append("Consider blinding strategy if applicable")
    
    is_complete = (
        len(experimental_groups) >= 1 and
        len(control_groups) >= 1 and
        sample_size and
        len(missing_elements) == 0
    )
    
    return {
        "is_complete": is_complete,
        "score": min(score, 100),
        "missing_elements": missing_elements,
        "suggestions": suggestions,
        "total_groups": len(experimental_groups) + len(control_groups),
        "has_power_analysis": bool(sample_size.get('power_analysis')),
        "statistical_power": sample_size.get('power_analysis', {}).get('power', 0)
    }


def calculate_power_analysis(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    groups: int = 2
) -> Dict[str, Any]:
    """
    Calculate statistical power analysis for experimental design.
    
    Args:
        effect_size: Expected effect size (Cohen's d)
        alpha: Significance level (default: 0.05)
        power: Desired statistical power (default: 0.8)
        groups: Number of groups to compare (default: 2)
        
    Returns:
        Power analysis results
    """
    try:
        from scipy import stats
        import math
        
        # Calculate required sample size for two-sample t-test
        z_alpha = stats.norm.ppf(1 - alpha/2)
        z_beta = stats.norm.ppf(power)
        
        # Cohen's d effect size formula
        n_per_group = 2 * ((z_alpha + z_beta) / effect_size) ** 2
        
        # Adjust for multiple groups if needed
        if groups > 2:
            # Simple Bonferroni correction
            adjusted_alpha = alpha / (groups * (groups - 1) / 2)
            z_alpha_adj = stats.norm.ppf(1 - adjusted_alpha/2)
            n_per_group = 2 * ((z_alpha_adj + z_beta) / effect_size) ** 2
        
        required_n = max(int(math.ceil(n_per_group)), 3)
        
        return {
            "effect_size": effect_size,
            "alpha": alpha,
            "power": power,
            "groups": groups,
            "required_sample_size": required_n,
            "statistical_test": "two_sample_ttest" if groups == 2 else "anova",
            "assumptions": [
                "Normal distribution",
                "Equal variances",
                "Independent samples"
            ]
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "required_sample_size": 10,
            "statistical_test": "unknown"
        } 