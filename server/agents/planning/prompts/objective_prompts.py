"""
Prompt templates for the Objective Setting Agent.

This module contains all prompts and templates used by the Objective Setting Agent
to guide users through clarifying research objectives and developing SMART goals.
"""

from typing import Dict, List, Any, Optional

# System prompts for the Objective Setting Agent
OBJECTIVE_SYSTEM_PROMPT = """You are the Objective Setting Agent, a specialized AI assistant helping researchers clarify and refine their experimental objectives. Your role is to:

1. Transform vague research ideas into specific, measurable objectives
2. Guide users through SMART goal development (Specific, Measurable, Achievable, Relevant, Time-bound)
3. Identify clear hypotheses that can be tested experimentally
4. Ensure objectives are scientifically sound and feasible

You should be conversational, encouraging, and methodical in your approach. Ask clarifying questions one at a time to avoid overwhelming the user. Draw from your knowledge of scientific methodology and biotech research practices.

Always focus on:
- Clarity and specificity in objectives
- Measurable outcomes
- Realistic scope and timeline
- Scientific rigor and methodology
- Practical feasibility in a lab setting"""

# Question templates for objective clarification
INITIAL_CLARIFICATION_QUESTIONS = [
    "What specific biological process, phenomenon, or system are you interested in studying?",
    "What outcome or result do you hope to achieve or measure in your experiment?",
    "What problem are you trying to solve or what question are you trying to answer?",
    "Are you comparing different conditions, treatments, or groups?",
    "What would success look like for this experiment?",
    "What specific measurements or data do you plan to collect?",
    "How does this experiment relate to existing research in your field?",
    "What time frame are you working within for this experiment?",
    "What resources and equipment do you have available?",
    "Are there any specific constraints or limitations I should be aware of?"
]

SMART_OBJECTIVE_QUESTIONS = [
    "Can you make your objective more specific? What exactly will you measure or observe?",
    "How will you quantify your results? What units or metrics will you use?",
    "Is this objective achievable with your current resources and timeline?",
    "How does this objective relate to your broader research goals?",
    "What is your target timeline for completing this experiment?",
    "What would constitute a successful outcome versus a null result?",
    "Are there any confounding variables we should consider controlling for?",
    "What baseline or control condition will you compare against?",
    "How will you ensure reproducibility of your results?",
    "What statistical analysis do you plan to use to evaluate your results?"
]

HYPOTHESIS_DEVELOPMENT_QUESTIONS = [
    "Based on your objective, what do you predict will happen?",
    "What scientific literature or previous research supports your prediction?",
    "Can you state your hypothesis as a testable prediction?",
    "What would prove your hypothesis wrong?",
    "Are there alternative hypotheses that could explain your expected results?",
    "How confident are you in your hypothesis and why?",
    "What assumptions is your hypothesis based on?",
    "How does your hypothesis relate to established scientific principles?",
    "What would be the implications if your hypothesis is correct?",
    "What would be the implications if your hypothesis is incorrect?"
]

# Response templates for different scenarios
OBJECTIVE_CLARIFICATION_RESPONSES = {
    "vague_initial": "I understand you're interested in {research_area}. To help develop a clear experimental objective, could you tell me more about {clarification_focus}?",
    
    "needs_specificity": "That's a good start! To make your objective more specific and measurable, {specific_guidance}. {follow_up_question}",
    
    "good_direction": "Excellent! Your objective is becoming clearer. Now let's focus on {next_aspect}. {guiding_question}",
    
    "hypothesis_prompt": "Based on your objective of {objective}, what do you predict will happen? {hypothesis_guidance}",
    
    "validation_needed": "Your objective looks good, but I'd like to verify a few things to ensure it's feasible: {validation_questions}",
    
    "completion_ready": "Great work! Your objective is now well-defined and measurable. Let me summarize what we've established: {objective_summary}"
}

# Validation criteria for objectives
OBJECTIVE_VALIDATION_CRITERIA = {
    "specificity": {
        "description": "Objective clearly defines what will be studied",
        "keywords": ["specific", "particular", "defined", "clear"],
        "questions": ["What exactly will you measure?", "Which specific system/process?"]
    },
    
    "measurability": {
        "description": "Objective includes measurable outcomes",
        "keywords": ["measure", "quantify", "assess", "evaluate", "analyze"],
        "questions": ["How will you measure this?", "What units will you use?"]
    },
    
    "feasibility": {
        "description": "Objective is achievable with available resources",
        "keywords": ["feasible", "realistic", "achievable", "practical"],
        "questions": ["Do you have the necessary equipment?", "Is the timeline realistic?"]
    },
    
    "relevance": {
        "description": "Objective addresses a meaningful scientific question",
        "keywords": ["relevant", "important", "significant", "meaningful"],
        "questions": ["Why is this important?", "How does this advance the field?"]
    },
    
    "time_bound": {
        "description": "Objective has a clear timeline",
        "keywords": ["timeline", "duration", "time", "schedule"],
        "questions": ["What's your timeline?", "How long will this take?"]
    }
}

# Common research domains and their specific guidance
DOMAIN_SPECIFIC_GUIDANCE = {
    "molecular_biology": {
        "common_objectives": ["protein expression", "gene regulation", "enzyme activity"],
        "measurement_types": ["concentration", "activity", "expression level"],
        "typical_controls": ["negative control", "positive control", "vehicle control"],
        "considerations": ["purity", "stability", "reproducibility"]
    },
    
    "cell_biology": {
        "common_objectives": ["cell viability", "proliferation", "differentiation"],
        "measurement_types": ["cell count", "viability percentage", "marker expression"],
        "typical_controls": ["untreated cells", "vehicle control", "positive control"],
        "considerations": ["cell passage number", "culture conditions", "contamination"]
    },
    
    "biochemistry": {
        "common_objectives": ["enzyme kinetics", "binding affinity", "structural analysis"],
        "measurement_types": ["Km", "Vmax", "IC50", "dissociation constant"],
        "typical_controls": ["buffer control", "inhibitor control", "substrate control"],
        "considerations": ["pH", "temperature", "ionic strength", "cofactors"]
    },
    
    "microbiology": {
        "common_objectives": ["growth inhibition", "antimicrobial activity", "biofilm formation"],
        "measurement_types": ["colony count", "optical density", "zone of inhibition"],
        "typical_controls": ["sterile control", "growth control", "antibiotic control"],
        "considerations": ["sterility", "culture medium", "incubation conditions"]
    }
}

# Template for objective refinement
OBJECTIVE_REFINEMENT_TEMPLATE = """
Original idea: {original_query}
Refined objective: {refined_objective}
Hypothesis: {hypothesis}
Measurable outcomes: {outcomes}
Timeline: {timeline}
Success criteria: {success_criteria}
"""

# Error handling messages
ERROR_MESSAGES = {
    "too_broad": "Your objective is quite broad. Let's narrow it down to something more specific and testable.",
    "unmeasurable": "I'm not sure how we would measure that outcome. Could you suggest a quantifiable metric?",
    "unrealistic": "That might be challenging with typical lab resources. Let's consider a more feasible approach.",
    "unclear_hypothesis": "I need help understanding your expected outcome. What do you predict will happen?",
    "missing_controls": "What will you compare your results against to draw meaningful conclusions?"
}

def get_domain_guidance(research_query: str) -> Dict[str, Any]:
    """
    Get domain-specific guidance based on research query.
    
    Args:
        research_query: The user's research question or area
        
    Returns:
        Dictionary with domain-specific guidance
    """
    query_lower = research_query.lower()
    
    for domain, guidance in DOMAIN_SPECIFIC_GUIDANCE.items():
        if any(term in query_lower for term in guidance["common_objectives"]):
            return {
                "domain": domain,
                "guidance": guidance,
                "suggested_questions": _get_domain_questions(domain)
            }
    
    return {
        "domain": "general",
        "guidance": {},
        "suggested_questions": INITIAL_CLARIFICATION_QUESTIONS[:3]
    }

def _get_domain_questions(domain: str) -> List[str]:
    """Get domain-specific questions for objective clarification."""
    domain_questions = {
        "molecular_biology": [
            "What specific protein or gene are you studying?",
            "Are you looking at expression levels, activity, or interactions?",
            "What cell type or organism will you use?"
        ],
        "cell_biology": [
            "What cell line or primary cells will you use?",
            "Are you studying cell growth, death, or differentiation?",
            "What treatment or condition will you test?"
        ],
        "biochemistry": [
            "What enzyme or protein are you characterizing?",
            "Are you measuring activity, binding, or structure?",
            "What substrate or ligand will you use?"
        ],
        "microbiology": [
            "What microorganism are you studying?",
            "Are you testing antimicrobial compounds or growth conditions?",
            "What growth medium and conditions will you use?"
        ]
    }
    
    return domain_questions.get(domain, INITIAL_CLARIFICATION_QUESTIONS[:3])

def format_objective_response(
    template_key: str, 
    context: Dict[str, Any]
) -> str:
    """
    Format an objective response using the specified template.
    
    Args:
        template_key: Key for the response template
        context: Context variables for template formatting
        
    Returns:
        Formatted response string
    """
    template = OBJECTIVE_CLARIFICATION_RESPONSES.get(template_key, "")
    
    try:
        return template.format(**context)
    except KeyError as e:
        return f"I'm here to help clarify your research objective. Could you tell me more about {context.get('research_area', 'your research')}?"

def validate_objective_completeness(
    objective: Optional[str],
    hypothesis: Optional[str],
    research_query: str
) -> Dict[str, Any]:
    """
    Validate the completeness of an objective.
    
    Args:
        objective: The proposed objective
        hypothesis: The proposed hypothesis
        research_query: Original research query
        
    Returns:
        Validation results dictionary
    """
    results = {
        "is_complete": False,
        "missing_elements": [],
        "score": 0,
        "suggestions": []
    }
    
    # Check for objective presence and quality
    if not objective or len(objective.strip()) < 20:
        results["missing_elements"].append("Clear, detailed objective")
        results["suggestions"].append("Provide a more detailed description of what you want to study")
    else:
        results["score"] += 50
        
        # Check for SMART criteria
        objective_lower = objective.lower()
        
        # Specificity
        if any(word in objective_lower for word in ["specific", "particular", "examine", "investigate"]):
            results["score"] += 10
        else:
            results["suggestions"].append("Make your objective more specific")
        
        # Measurability
        if any(word in objective_lower for word in ["measure", "quantify", "assess", "determine", "analyze"]):
            results["score"] += 10
        else:
            results["suggestions"].append("Include how you will measure your outcomes")
        
        # Achievability indicators
        if any(word in objective_lower for word in ["using", "with", "in", "by"]):
            results["score"] += 10
        else:
            results["suggestions"].append("Specify your approach or methods")
    
    # Check for hypothesis
    if not hypothesis or len(hypothesis.strip()) < 10:
        results["missing_elements"].append("Testable hypothesis")
        results["suggestions"].append("Develop a clear hypothesis about what you expect to find")
    else:
        results["score"] += 20
    
    # Determine completeness
    results["is_complete"] = results["score"] >= 80 and len(results["missing_elements"]) == 0
    
    return results 