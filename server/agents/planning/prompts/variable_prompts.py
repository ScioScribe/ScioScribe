"""
Prompt templates for the Variable Identification Agent.

This module contains all prompts and templates used by the Variable Identification Agent
to guide users through identifying and defining experimental variables (independent, dependent, control).
"""

from typing import Dict, List, Any, Optional

# System prompts for the Variable Identification Agent
VARIABLE_SYSTEM_PROMPT = """You are the Variable Identification Agent, a specialized AI assistant helping researchers identify and define experimental variables. Your role is to:

1. Identify independent variables (factors being manipulated)
2. Identify dependent variables (outcomes being measured)
3. Identify control variables (factors being held constant)
4. Suggest appropriate measurement methods for each variable
5. Ensure variables are properly defined and measurable

You should be systematic, methodical, and knowledgeable about biotech research practices. Ask focused questions to help researchers clearly define their variables and measurement approaches.

Always focus on:
- Clear operational definitions of variables
- Measurable and quantifiable outcomes
- Appropriate controls for experimental validity
- Practical measurement methods
- Domain-specific best practices"""

# Question templates for variable identification
INDEPENDENT_VARIABLE_QUESTIONS = [
    "What specific factor or condition will you be changing or manipulating in your experiment?",
    "Are you testing different concentrations, doses, or treatment conditions?",
    "Will you be comparing different time points, temperatures, or environmental conditions?",
    "Are you testing different cell lines, organisms, or biological samples?",
    "What specific interventions or treatments will you apply?",
    "Are you varying any physical parameters like pH, temperature, or pressure?",
    "Will you be testing different compounds, drugs, or chemical treatments?",
    "Are you manipulating genetic factors, gene expression, or protein levels?",
    "What different groups or conditions will you be comparing?",
    "Are there multiple factors you plan to vary simultaneously?"
]

DEPENDENT_VARIABLE_QUESTIONS = [
    "What specific outcome or response will you be measuring?",
    "How will you quantify the effect of your treatment or intervention?",
    "What biological markers, indicators, or readouts will you measure?",
    "Are you measuring growth, viability, activity, or expression levels?",
    "What specific assay or measurement technique will you use?",
    "Will you be measuring multiple endpoints or just one primary outcome?",
    "How will you detect changes in your system?",
    "What units or scale will you use for your measurements?",
    "Are you measuring qualitative or quantitative changes?",
    "What equipment or instruments will you use for measurements?"
]

CONTROL_VARIABLE_QUESTIONS = [
    "What factors need to remain constant throughout your experiment?",
    "What environmental conditions will you control (temperature, humidity, pH)?",
    "Are there any biological factors that need to be standardized?",
    "What experimental conditions will be the same across all groups?",
    "Are there any confounding variables you need to account for?",
    "What baseline or reference conditions will you use?",
    "Do you need negative controls (no treatment) or positive controls (known effect)?",
    "Are there any technical variables that need to be controlled?",
    "What aspects of your experimental setup will remain unchanged?",
    "Are there any external factors that could influence your results?"
]

# Domain-specific variable guidance
DOMAIN_VARIABLE_GUIDANCE = {
    "molecular_biology": {
        "common_independent": [
            "protein concentration", "gene expression level", "enzyme amount",
            "plasmid copy number", "induction time", "substrate concentration"
        ],
        "common_dependent": [
            "protein expression level", "enzyme activity", "binding affinity",
            "gene transcription level", "protein stability", "enzymatic rate"
        ],
        "common_controls": [
            "negative control (no treatment)", "positive control (known activator)",
            "vehicle control", "empty vector control", "buffer control"
        ],
        "measurement_methods": [
            "Western blot", "qPCR", "ELISA", "enzyme assay", "fluorescence",
            "spectrophotometry", "mass spectrometry", "gel electrophoresis"
        ]
    },
    
    "cell_biology": {
        "common_independent": [
            "drug concentration", "treatment time", "serum concentration",
            "cell density", "passage number", "culture conditions"
        ],
        "common_dependent": [
            "cell viability", "proliferation rate", "apoptosis level",
            "differentiation markers", "metabolic activity", "cell morphology"
        ],
        "common_controls": [
            "untreated cells", "vehicle control", "positive control (known treatment)",
            "negative control (toxic compound)", "sham treatment"
        ],
        "measurement_methods": [
            "MTT assay", "cell counting", "flow cytometry", "microscopy",
            "immunofluorescence", "viability staining", "proliferation assay"
        ]
    },
    
    "biochemistry": {
        "common_independent": [
            "substrate concentration", "pH", "temperature", "ionic strength",
            "inhibitor concentration", "cofactor concentration"
        ],
        "common_dependent": [
            "enzyme activity", "reaction rate", "binding affinity", "Km value",
            "Vmax", "IC50", "product formation", "substrate consumption"
        ],
        "common_controls": [
            "no enzyme control", "no substrate control", "buffer control",
            "heat-inactivated enzyme", "vehicle control"
        ],
        "measurement_methods": [
            "spectrophotometry", "fluorometry", "HPLC", "mass spectrometry",
            "enzyme kinetics", "binding assays", "chromatography"
        ]
    },
    
    "microbiology": {
        "common_independent": [
            "antibiotic concentration", "growth medium", "incubation time",
            "temperature", "pH", "oxygen levels", "bacterial strain"
        ],
        "common_dependent": [
            "growth rate", "optical density", "colony count", "zone of inhibition",
            "biofilm formation", "metabolic activity", "viability"
        ],
        "common_controls": [
            "sterile medium", "no antibiotic control", "positive control (known antibiotic)",
            "negative control (no bacteria)", "vehicle control"
        ],
        "measurement_methods": [
            "plate counting", "optical density", "turbidimetry", "zone measurement",
            "biofilm quantification", "metabolic assays", "viability staining"
        ]
    }
}

# Response templates for variable identification
VARIABLE_RESPONSE_TEMPLATES = {
    "independent_needed": "Based on your objective, I need to understand what you'll be changing or manipulating. {specific_question}",
    
    "dependent_needed": "Now let's identify what you'll be measuring as your outcome. {measurement_question}",
    
    "control_needed": "To ensure valid results, we need to identify what should remain constant. {control_question}",
    
    "measurement_method": "How will you measure {variable_name}? {method_suggestion}",
    
    "variable_refinement": "Let's refine your {variable_type} variable. {refinement_guidance}",
    
    "validation_check": "I want to verify your variables are well-defined: {validation_question}",
    
    "completion_summary": "Excellent! Here's your complete variable set: {variable_summary}"
}

# Variable validation criteria
VARIABLE_VALIDATION_CRITERIA = {
    "independent": {
        "required_fields": ["name", "type", "units", "levels"],
        "validation_checks": [
            "Has clear operational definition",
            "Is manipulable/controllable",
            "Has specified levels or ranges",
            "Is relevant to research objective"
        ]
    },
    
    "dependent": {
        "required_fields": ["name", "type", "units", "measurement_method"],
        "validation_checks": [
            "Is measurable and quantifiable",
            "Has appropriate measurement method",
            "Is relevant to research objective",
            "Has clear units or scale"
        ]
    },
    
    "control": {
        "required_fields": ["name", "reason", "control_method"],
        "validation_checks": [
            "Is clearly defined",
            "Has justification for control",
            "Has method for maintaining constant",
            "Is relevant to experimental validity"
        ]
    }
}

# Common variable types and their characteristics
VARIABLE_TYPES = {
    "categorical": {
        "description": "Variables with distinct categories or groups",
        "examples": ["cell line", "treatment type", "genotype"],
        "considerations": ["Number of categories", "Clear definitions", "Mutually exclusive"]
    },
    
    "continuous": {
        "description": "Variables with numerical values on a continuous scale",
        "examples": ["concentration", "time", "temperature"],
        "considerations": ["Range", "Precision", "Units", "Measurement accuracy"]
    },
    
    "ordinal": {
        "description": "Variables with ordered categories",
        "examples": ["low/medium/high", "stage of disease", "severity score"],
        "considerations": ["Clear ordering", "Consistent intervals", "Objective criteria"]
    },
    
    "binary": {
        "description": "Variables with two possible states",
        "examples": ["presence/absence", "alive/dead", "positive/negative"],
        "considerations": ["Clear definitions", "Objective criteria", "Consistent classification"]
    }
}

def get_variable_domain_guidance(research_query: str, objective: str = "") -> Dict[str, Any]:
    """
    Get domain-specific variable guidance based on research query and objective.
    
    Args:
        research_query: The user's research question
        objective: The experimental objective
        
    Returns:
        Dictionary with domain-specific variable guidance
    """
    combined_text = f"{research_query} {objective}".lower()
    
    for domain, guidance in DOMAIN_VARIABLE_GUIDANCE.items():
        # Check if domain keywords appear in text
        domain_keywords = guidance.get("common_independent", []) + guidance.get("common_dependent", [])
        if any(keyword.lower() in combined_text for keyword in domain_keywords):
            return {
                "domain": domain,
                "guidance": guidance,
                "suggested_questions": _get_domain_variable_questions(domain)
            }
    
    return {
        "domain": "general",
        "guidance": {},
        "suggested_questions": {
            "independent": INDEPENDENT_VARIABLE_QUESTIONS[:3],
            "dependent": DEPENDENT_VARIABLE_QUESTIONS[:3],
            "control": CONTROL_VARIABLE_QUESTIONS[:3]
        }
    }

def _get_domain_variable_questions(domain: str) -> Dict[str, List[str]]:
    """Get domain-specific variable questions."""
    domain_questions = {
        "molecular_biology": {
            "independent": [
                "What protein, gene, or enzyme are you manipulating?",
                "Are you varying expression levels or activity?",
                "What concentrations or conditions will you test?"
            ],
            "dependent": [
                "How will you measure protein expression or activity?",
                "What specific assay will you use?",
                "Are you measuring binding, activity, or expression?"
            ],
            "control": [
                "Do you need an empty vector control?",
                "Will you include a positive control with known activity?",
                "What buffer or vehicle controls are needed?"
            ]
        },
        "cell_biology": {
            "independent": [
                "What treatment or compound will you test?",
                "Are you varying concentration or time?",
                "What cell conditions will you manipulate?"
            ],
            "dependent": [
                "How will you measure cell response?",
                "Are you measuring viability, proliferation, or function?",
                "What specific assay will you use?"
            ],
            "control": [
                "Do you need untreated control cells?",
                "Will you include a vehicle control?",
                "Are positive and negative controls needed?"
            ]
        }
    }
    
    return domain_questions.get(domain, {
        "independent": INDEPENDENT_VARIABLE_QUESTIONS[:3],
        "dependent": DEPENDENT_VARIABLE_QUESTIONS[:3],
        "control": CONTROL_VARIABLE_QUESTIONS[:3]
    })

def format_variable_response(template_key: str, context: Dict[str, Any]) -> str:
    """
    Format a variable response using the specified template.
    
    Args:
        template_key: Key for the response template
        context: Context variables for template formatting
        
    Returns:
        Formatted response string
    """
    template = VARIABLE_RESPONSE_TEMPLATES.get(template_key, "")
    
    try:
        return template.format(**context)
    except KeyError:
        return f"Let's work on identifying your experimental variables. {context.get('fallback_question', 'What will you be measuring in your experiment?')}"

def validate_variable_set(
    independent_vars: List[Dict[str, Any]],
    dependent_vars: List[Dict[str, Any]],
    control_vars: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate the completeness and quality of a variable set.
    
    Args:
        independent_vars: List of independent variables
        dependent_vars: List of dependent variables
        control_vars: List of control variables
        
    Returns:
        Validation results dictionary
    """
    results = {
        "is_complete": False,
        "missing_elements": [],
        "score": 0,
        "suggestions": []
    }
    
    # Check independent variables
    if not independent_vars:
        results["missing_elements"].append("Independent variables (what you're manipulating)")
        results["suggestions"].append("Identify what factors you'll be changing or testing")
    else:
        results["score"] += 30
        for var in independent_vars:
            if not all(field in var for field in ["name", "type", "levels"]):
                results["suggestions"].append(f"Complete definition for independent variable: {var.get('name', 'unnamed')}")
    
    # Check dependent variables
    if not dependent_vars:
        results["missing_elements"].append("Dependent variables (what you're measuring)")
        results["suggestions"].append("Identify what outcomes you'll be measuring")
    else:
        results["score"] += 40
        for var in dependent_vars:
            if not all(field in var for field in ["name", "type", "measurement_method"]):
                results["suggestions"].append(f"Complete definition for dependent variable: {var.get('name', 'unnamed')}")
    
    # Check control variables
    if not control_vars:
        results["missing_elements"].append("Control variables (what you're keeping constant)")
        results["suggestions"].append("Identify what factors need to remain constant")
    else:
        results["score"] += 30
        for var in control_vars:
            if not all(field in var for field in ["name", "reason"]):
                results["suggestions"].append(f"Complete definition for control variable: {var.get('name', 'unnamed')}")
    
    # Determine completeness
    results["is_complete"] = results["score"] >= 80 and len(results["missing_elements"]) == 0
    
    return results

def suggest_measurement_methods(variable_name: str, variable_type: str, domain: str) -> List[str]:
    """
    Suggest appropriate measurement methods for a variable.
    
    Args:
        variable_name: Name of the variable
        variable_type: Type of variable (independent/dependent/control)
        domain: Research domain
        
    Returns:
        List of suggested measurement methods
    """
    domain_guidance = DOMAIN_VARIABLE_GUIDANCE.get(domain, {})
    methods = domain_guidance.get("measurement_methods", [])
    
    # Variable-specific suggestions
    variable_lower = variable_name.lower()
    
    if "viability" in variable_lower:
        return ["MTT assay", "trypan blue exclusion", "alamar blue assay"]
    elif "expression" in variable_lower:
        return ["qPCR", "Western blot", "immunofluorescence"]
    elif "activity" in variable_lower:
        return ["enzyme assay", "reporter assay", "functional assay"]
    elif "concentration" in variable_lower:
        return ["ELISA", "Bradford assay", "spectrophotometry"]
    elif "growth" in variable_lower:
        return ["optical density", "cell counting", "colony counting"]
    
    return methods[:3] if methods else ["spectrophotometry", "microscopy", "quantitative assay"]

def get_variable_examples(domain: str, variable_type: str) -> List[Dict[str, str]]:
    """
    Get examples of variables for a specific domain and type.
    
    Args:
        domain: Research domain
        variable_type: Type of variable (independent/dependent/control)
        
    Returns:
        List of variable examples
    """
    domain_guidance = DOMAIN_VARIABLE_GUIDANCE.get(domain, {})
    
    if variable_type == "independent":
        variables = domain_guidance.get("common_independent", [])
    elif variable_type == "dependent":
        variables = domain_guidance.get("common_dependent", [])
    elif variable_type == "control":
        variables = domain_guidance.get("common_controls", [])
    else:
        return []
    
    return [{"name": var, "example": f"Example: {var}"} for var in variables[:5]] 