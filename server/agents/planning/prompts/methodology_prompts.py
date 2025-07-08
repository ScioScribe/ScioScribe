"""
Prompt templates for the Methodology & Protocol Agent.

This module contains all prompts and templates used by the Methodology & Protocol Agent
to guide users through developing detailed experimental protocols and material lists.
"""

from typing import Dict, List, Any, Optional

# System prompts for the Methodology & Protocol Agent
METHODOLOGY_SYSTEM_PROMPT = """You are the Methodology & Protocol Agent, a specialized AI assistant helping researchers develop detailed, step-by-step experimental protocols. Your role is to:

1. Generate comprehensive, actionable experimental protocols with specific parameters
2. Create detailed materials and equipment lists with specifications
3. Provide domain-specific methodology guidance and best practices
4. Ensure protocols are scientifically rigorous and reproducible
5. Identify potential technical challenges and provide solutions

You should be methodical, precise, and practical in your approach. Focus on:
- Step-by-step procedures with specific parameters (concentrations, volumes, temperatures, timing)
- Complete materials and equipment lists with specifications
- Safety considerations and precautions
- Quality control measures and validation steps
- Troubleshooting guidance for common issues
- Reference to established protocols and best practices

Always ensure protocols are detailed enough for a researcher to follow exactly."""

# Question templates for methodology development
METHODOLOGY_DEVELOPMENT_QUESTIONS = [
    "What specific techniques or methods will you use to manipulate your independent variables?",
    "How will you prepare your samples or experimental materials?",
    "What equipment and instruments will you need for your measurements?",
    "What are the specific parameters for your experimental conditions (concentrations, temperatures, pH, etc.)?",
    "How long will each step of your protocol take?",
    "What quality control measures will you implement?",
    "Are there any time-sensitive steps that require precise timing?",
    "What safety precautions are needed for your experimental procedures?",
    "Do you have any specific protocol references or standards to follow?",
    "What are the critical steps that could affect your results?"
]

# Protocol generation questions
PROTOCOL_GENERATION_QUESTIONS = [
    "What is the overall workflow for your experiment from start to finish?",
    "How will you prepare your experimental setup?",
    "What are the specific steps for sample preparation?",
    "How will you execute your experimental treatments?",
    "What measurements will you take and when?",
    "How will you clean up and store samples between steps?",
    "What documentation will you maintain during the experiment?",
    "Are there any critical timing considerations?",
    "What calibration or validation steps are needed?",
    "How will you handle waste disposal and cleanup?"
]

# Materials and equipment questions
MATERIALS_EQUIPMENT_QUESTIONS = [
    "What chemicals and reagents will you need, and in what quantities?",
    "What laboratory equipment and instruments are required?",
    "Are there any specialized tools or consumables needed?",
    "What safety equipment and personal protective equipment (PPE) is required?",
    "Do you need any specific grades or purities of materials?",
    "Are there any materials that need special storage conditions?",
    "What backup supplies should you have on hand?",
    "Are there any single-use items that need to be accounted for?",
    "Do you need any calibration standards or reference materials?",
    "What cleaning supplies will you need for equipment maintenance?"
]

# Response templates for different methodology scenarios
METHODOLOGY_RESPONSE_TEMPLATES = {
    "protocol_development": """
    Based on your experimental design, I'll help you develop a detailed protocol. 
    Let's start with the overall workflow and then break it down into specific steps.
    
    {context}
    
    What is the main technique or method you'll be using for this experiment?
    """,
    
    "materials_needed": """
    Now let's identify all the materials and equipment you'll need. 
    I'll help you create a comprehensive list with specifications.
    
    {current_materials}
    
    What specific chemicals, reagents, or biological materials will you be working with?
    """,
    
    "protocol_refinement": """
    Let's refine your protocol to ensure it's detailed and reproducible.
    
    Current protocol summary:
    {protocol_summary}
    
    {refinement_focus}
    """,
    
    "safety_considerations": """
    Safety is crucial for your experimental procedures. Let me help you identify 
    the necessary safety measures and precautions.
    
    {safety_context}
    
    Are you working with any hazardous materials or procedures that require special safety measures?
    """,
    
    "methodology_complete": """
    Excellent! Your methodology and protocol are now complete:
    
    {methodology_summary}
    
    This protocol includes {step_count} detailed steps and {material_count} materials/equipment items.
    Ready to move to the next planning stage?
    """
}

# Domain-specific guidance for common research areas
METHODOLOGY_DOMAIN_GUIDANCE = {
    "cell_culture": {
        "common_protocols": [
            "Cell passage and maintenance",
            "Cell viability assays",
            "Transfection procedures",
            "Protein expression analysis",
            "Flow cytometry analysis"
        ],
        "essential_materials": [
            "Cell culture media",
            "Serum (FBS/FCS)",
            "Antibiotics",
            "Trypsin-EDTA",
            "PBS buffer",
            "Cell culture flasks/plates"
        ],
        "key_parameters": [
            "Incubation temperature (37°C)",
            "CO2 concentration (5%)",
            "Humidity conditions",
            "Passage ratios",
            "Seeding densities"
        ]
    },
    
    "molecular_biology": {
        "common_protocols": [
            "DNA/RNA extraction",
            "PCR amplification",
            "Gel electrophoresis",
            "Cloning procedures",
            "Sequencing preparation"
        ],
        "essential_materials": [
            "DNA/RNA extraction kits",
            "PCR reagents and primers",
            "Agarose/polyacrylamide gels",
            "Restriction enzymes",
            "Competent cells",
            "Antibiotics for selection"
        ],
        "key_parameters": [
            "Annealing temperatures",
            "Cycle numbers",
            "Incubation times",
            "Buffer compositions",
            "Enzyme concentrations"
        ]
    },
    
    "biochemistry": {
        "common_protocols": [
            "Protein purification",
            "Enzyme assays",
            "Western blotting",
            "Chromatography",
            "Spectroscopic analysis"
        ],
        "essential_materials": [
            "Protein standards",
            "Chromatography resins",
            "Antibodies",
            "Buffers and salts",
            "Enzyme substrates",
            "Detection reagents"
        ],
        "key_parameters": [
            "Buffer pH and ionic strength",
            "Protein concentrations",
            "Incubation temperatures",
            "Reaction times",
            "Detection wavelengths"
        ]
    }
}

# Validation criteria for methodology completeness
METHODOLOGY_VALIDATION_CRITERIA = {
    "protocol_steps": {
        "required_fields": ["step_number", "description", "parameters", "duration"],
        "min_score": 80,
        "weight": 40
    },
    "materials_equipment": {
        "required_fields": ["name", "type", "quantity", "specifications"],
        "min_score": 75,
        "weight": 35
    },
    "completeness": {
        "min_steps": 5,
        "min_materials": 10,
        "weight": 25
    }
}

def get_methodology_domain_guidance(research_query: str, experimental_design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get domain-specific guidance for methodology development.
    
    Args:
        research_query: The user's research question
        experimental_design: Current experimental design information
        
    Returns:
        Dictionary with domain-specific guidance
    """
    query_lower = research_query.lower()
    
    # Determine domain based on research query
    if any(term in query_lower for term in ["cell", "culture", "viability", "proliferation"]):
        domain = "cell_culture"
    elif any(term in query_lower for term in ["dna", "rna", "pcr", "gene", "sequencing"]):
        domain = "molecular_biology"
    elif any(term in query_lower for term in ["protein", "enzyme", "assay", "purification"]):
        domain = "biochemistry"
    else:
        domain = "general"
    
    if domain in METHODOLOGY_DOMAIN_GUIDANCE:
        guidance = METHODOLOGY_DOMAIN_GUIDANCE[domain].copy()
        guidance["domain"] = domain
        
        # Add experimental design context
        groups = experimental_design.get("experimental_groups", [])
        if groups:
            guidance["experimental_context"] = [g.get("name", "") for g in groups]
        
        return guidance
    
    return {
        "domain": "general",
        "common_protocols": ["Sample preparation", "Experimental treatment", "Data collection"],
        "essential_materials": ["Basic laboratory supplies", "Measurement instruments"],
        "key_parameters": ["Temperature", "Time", "Concentrations"],
        "experimental_context": []
    }

def format_methodology_response(template_key: str, context: Dict[str, Any]) -> str:
    """
    Format a methodology response using the specified template.
    
    Args:
        template_key: Key for the response template
        context: Context variables for template formatting
        
    Returns:
        Formatted response string
    """
    if template_key not in METHODOLOGY_RESPONSE_TEMPLATES:
        return f"I'm ready to help you develop your methodology. {context.get('fallback_message', '')}"
    
    template = METHODOLOGY_RESPONSE_TEMPLATES[template_key]
    
    try:
        return template.format(**context)
    except KeyError as e:
        return f"I'm ready to help you develop your methodology. Please provide more details about your experimental approach."

def validate_methodology_completeness(methodology_steps: List[Dict[str, Any]], 
                                    materials_equipment: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate the completeness of methodology and protocol information.
    
    Args:
        methodology_steps: List of protocol steps
        materials_equipment: List of materials and equipment
        
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        "is_complete": False,
        "score": 0,
        "missing_elements": [],
        "suggestions": []
    }
    
    # Validate methodology steps
    steps_score = 0
    if methodology_steps:
        valid_steps = 0
        for step in methodology_steps:
            if all(field in step and step[field] for field in METHODOLOGY_VALIDATION_CRITERIA["protocol_steps"]["required_fields"]):
                valid_steps += 1
        
        if methodology_steps:
            steps_score = (valid_steps / len(methodology_steps)) * 100
        
        if len(methodology_steps) < METHODOLOGY_VALIDATION_CRITERIA["completeness"]["min_steps"]:
            validation_results["missing_elements"].append(f"Need at least {METHODOLOGY_VALIDATION_CRITERIA['completeness']['min_steps']} detailed protocol steps")
    else:
        validation_results["missing_elements"].append("No protocol steps defined")
    
    # Validate materials and equipment
    materials_score = 0
    if materials_equipment:
        valid_materials = 0
        for item in materials_equipment:
            if all(field in item and item[field] for field in METHODOLOGY_VALIDATION_CRITERIA["materials_equipment"]["required_fields"]):
                valid_materials += 1
        
        if materials_equipment:
            materials_score = (valid_materials / len(materials_equipment)) * 100
        
        if len(materials_equipment) < METHODOLOGY_VALIDATION_CRITERIA["completeness"]["min_materials"]:
            validation_results["missing_elements"].append(f"Need at least {METHODOLOGY_VALIDATION_CRITERIA['completeness']['min_materials']} materials/equipment items")
    else:
        validation_results["missing_elements"].append("No materials or equipment defined")
    
    # Calculate overall score
    validation_results["score"] = (
        steps_score * METHODOLOGY_VALIDATION_CRITERIA["protocol_steps"]["weight"] / 100 +
        materials_score * METHODOLOGY_VALIDATION_CRITERIA["materials_equipment"]["weight"] / 100 +
        (50 if methodology_steps and materials_equipment else 0) * METHODOLOGY_VALIDATION_CRITERIA["completeness"]["weight"] / 100
    )
    
    # Determine completeness
    validation_results["is_complete"] = (
        validation_results["score"] >= 80 and
        len(validation_results["missing_elements"]) == 0
    )
    
    # Add suggestions
    if steps_score < 80:
        validation_results["suggestions"].append("Add more detailed protocol steps with specific parameters")
    if materials_score < 75:
        validation_results["suggestions"].append("Provide complete specifications for all materials and equipment")
    if not validation_results["is_complete"]:
        validation_results["suggestions"].append("Ensure all protocol steps include timing, parameters, and safety considerations")
    
    return validation_results

def suggest_protocol_steps(domain: str, experimental_design: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Suggest protocol steps based on domain and experimental design.
    
    Args:
        domain: Research domain
        experimental_design: Current experimental design
        
    Returns:
        List of suggested protocol steps
    """
    if domain not in METHODOLOGY_DOMAIN_GUIDANCE:
        domain = "general"
    
    guidance = METHODOLOGY_DOMAIN_GUIDANCE[domain]
    suggested_steps = []
    
    # Generate basic protocol structure
    base_steps = [
        {"step_number": 1, "description": "Prepare experimental setup and materials", "category": "preparation"},
        {"step_number": 2, "description": "Perform sample preparation", "category": "sample_prep"},
        {"step_number": 3, "description": "Apply experimental treatments", "category": "treatment"},
        {"step_number": 4, "description": "Collect measurements and data", "category": "measurement"},
        {"step_number": 5, "description": "Clean up and store samples", "category": "cleanup"}
    ]
    
    # Customize based on domain
    for step in base_steps:
        if domain == "cell_culture" and step["category"] == "sample_prep":
            step["description"] = "Prepare cell cultures and ensure proper confluence"
        elif domain == "molecular_biology" and step["category"] == "sample_prep":
            step["description"] = "Extract and prepare DNA/RNA samples"
        elif domain == "biochemistry" and step["category"] == "treatment":
            step["description"] = "Apply enzymatic or chemical treatments"
        
        suggested_steps.append(step)
    
    return suggested_steps

def generate_materials_list(domain: str, experimental_design: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate a materials list based on domain and experimental design.
    
    Args:
        domain: Research domain
        experimental_design: Current experimental design
        
    Returns:
        List of suggested materials and equipment
    """
    if domain not in METHODOLOGY_DOMAIN_GUIDANCE:
        domain = "general"
    
    guidance = METHODOLOGY_DOMAIN_GUIDANCE[domain]
    materials_list = []
    
    # Add essential materials for the domain
    for material in guidance["essential_materials"]:
        materials_list.append({
            "name": material,
            "type": "reagent" if "buffer" in material.lower() or "media" in material.lower() else "consumable",
            "quantity": "As needed",
            "specifications": "Laboratory grade"
        })
    
    # Add basic laboratory equipment
    basic_equipment = [
        {"name": "Pipettes", "type": "equipment", "quantity": "Set", "specifications": "1-1000 µL range"},
        {"name": "Microcentrifuge tubes", "type": "consumable", "quantity": "100", "specifications": "1.5 mL, sterile"},
        {"name": "Incubator", "type": "equipment", "quantity": "1", "specifications": "37°C, CO2 control"},
        {"name": "Centrifuge", "type": "equipment", "quantity": "1", "specifications": "Benchtop, 15000 rpm"},
        {"name": "pH meter", "type": "equipment", "quantity": "1", "specifications": "±0.1 pH accuracy"}
    ]
    
    materials_list.extend(basic_equipment)
    
    return materials_list 