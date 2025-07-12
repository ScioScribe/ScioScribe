"""
Pydantic models for structured data within the planning agent system.

This module defines the data structures used for agent inputs, outputs,
and structured content within the experiment planning process. These models
are crucial for ensuring type safety and structured communication between
different components of the system, especially for LLM outputs.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ObjectiveOutput(BaseModel):
    """
    Structured output for the ObjectiveAgent.
    
    This model defines the expected output from the LLM when processing
    the objective-setting stage. It ensures that the agent receives a clearly
    defined objective and a testable hypothesis.
    """
    experiment_objective: str = Field(
        ...,
        description="A specific, measurable, achievable, relevant, and time-bound (SMART) objective for the experiment. This should be a clear statement of what the research aims to accomplish."
    )
    hypothesis: Optional[str] = Field(
        None,
        description="A clear, testable hypothesis derived from the research objective. It should state the expected relationship between variables."
    )

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "experiment_objective": "To determine the effect of varying concentrations (0, 10, 50, 100 µM) of compound 'X' on the viability of 'A549' lung cancer cells over a 48-hour period.",
                "hypothesis": "Increasing concentrations of compound 'X' will lead to a dose-dependent decrease in the viability of 'A549' lung cancer cells."
            }
        }


# --- Variable Identification Models ---

class IndependentVariable(BaseModel):
    """Defines an independent variable, which is manipulated by the researcher."""
    name: str = Field(..., description="The name of the variable (e.g., 'Drug Concentration').")
    type: str = Field(..., description="The data type of the variable (e.g., 'Continuous', 'Categorical').")
    units: Optional[str] = Field(None, description="The units of measurement (e.g., 'µM', 'mg/mL').")
    levels: List[Any] = Field(..., description="The specific levels, values, or conditions of the variable being tested (e.g., [0, 10, 50, 100]).")

class DependentVariable(BaseModel):
    """Defines a dependent variable, which is measured in response to the independent variable."""
    name: str = Field(..., description="The name of the outcome variable being measured (e.g., 'Cell Viability').")
    type: str = Field(..., description="The data type of the variable (e.g., 'Quantitative', 'Qualitative').")
    units: Optional[str] = Field(None, description="The units of measurement (e.g., '%', 'absorbance units').")
    measurement_method: str = Field(..., description="The specific technique or assay used to measure the variable (e.g., 'MTT Assay', 'Flow Cytometry').")

class ControlVariable(BaseModel):
    """Defines a control variable, which is kept constant to prevent it from influencing the outcome."""
    name: str = Field(..., description="The name of the variable being controlled (e.g., 'Incubation Temperature').")
    reason: str = Field(..., description="The reason why it's important to control this variable.")
    control_method: str = Field(..., description="The method used to keep this variable constant (e.g., 'CO2 Incubator at 37°C').")

class VariableOutput(BaseModel):
    """
    Structured output for the VariableAgent.
    
    This model defines the expected output from the LLM when processing
    the variable identification stage. It ensures the agent receives a comprehensive
    list of all relevant variables for the experiment.
    """
    independent_variables: List[IndependentVariable] = Field(..., description="List of independent variables to be manipulated.")
    dependent_variables: List[DependentVariable] = Field(..., description="List of dependent variables to be measured.")
    control_variables: List[ControlVariable] = Field(..., description="List of variables to be kept constant.")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "independent_variables": [
                    {"name": "Compound 'X' Concentration", "type": "Continuous", "units": "µM", "levels": [0, 10, 50, 100]}
                ],
                "dependent_variables": [
                    {"name": "A549 Cell Viability", "type": "Quantitative", "units": "%", "measurement_method": "MTT Assay after 48 hours"}
                ],
                "control_variables": [
                    {"name": "Temperature", "reason": "Cell growth is temperature-dependent.", "control_method": "Maintain at 37°C in a CO2 incubator."},
                    {"name": "Cell Seeding Density", "reason": "Ensures a consistent starting number of cells for all treatments.", "control_method": "Seed 5,000 cells per well."}
                ]
            }
        } 


# --- Experimental Design Models ---

class ExperimentalGroup(BaseModel):
    """Defines an experimental group, representing a specific condition being tested."""
    name: str = Field(..., description="A unique, descriptive name for the experimental group (e.g., '10 µM Compound X').")
    description: str = Field(..., description="A brief explanation of what this group represents and its purpose in the experiment.")
    conditions: Dict[str, Any] = Field(..., description="A dictionary detailing the specific conditions for this group, linking independent variables to their levels (e.g., {'Compound 'X' Concentration': 10, 'Timepoint': '48h'}).")

class ControlGroup(BaseModel):
    """Defines a control group, used as a baseline for comparison."""
    name: str = Field(..., description="A unique, descriptive name for the control group (e.g., 'Vehicle Control').")
    type: str = Field(..., description="The type of control, such as 'positive', 'negative', or 'vehicle'.")
    purpose: str = Field(..., description="A clear explanation of why this control is necessary and what it controls for.")
    description: str = Field(..., description="A brief description of the control group's setup and conditions.")

class PowerAnalysis(BaseModel):
    """Details of the statistical power analysis."""
    effect_size: float = Field(..., description="The expected magnitude of the effect (e.g., Cohen's d).")
    alpha: float = Field(..., description="The significance level (Type I error rate), typically 0.05.")
    power: float = Field(..., description="The desired statistical power (1 - Type II error rate), typically 0.8 or 0.9.")
    required_sample_size: int = Field(..., description="The minimum number of samples required per group to achieve the desired power.")
    statistical_test: str = Field(..., description="The statistical test used for the power calculation (e.g., 'two_sample_ttest').")

class SampleSize(BaseModel):
    """Defines the sample size and replication strategy."""
    biological_replicates: int = Field(..., description="The number of independent biological samples or subjects per group.")
    technical_replicates: int = Field(..., description="The number of times each biological sample is measured.")
    power_analysis: PowerAnalysis = Field(..., description="The detailed statistical power analysis supporting the sample size decision.")

class DesignOutput(BaseModel):
    """
    Structured output for the DesignAgent.
    
    This model defines the expected output from the LLM when processing
    the experimental design stage. It ensures the agent receives a comprehensive
    and statistically sound experimental design.
    """
    experimental_groups: List[ExperimentalGroup] = Field(..., description="A list of all experimental (or treatment) groups.")
    control_groups: List[ControlGroup] = Field(..., description="A list of all necessary control groups for the experiment.")
    sample_size: SampleSize = Field(..., description="The detailed sample size and power analysis for the experiment.")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "experimental_groups": [
                    {
                        "name": "10 µM Compound X",
                        "description": "Test group receiving 10 µM of Compound X to assess its effect on cell viability.",
                        "conditions": {"Compound 'X' Concentration": 10}
                    },
                    {
                        "name": "50 µM Compound X",
                        "description": "Test group receiving 50 µM of Compound X to assess its effect on cell viability.",
                        "conditions": {"Compound 'X' Concentration": 50}
                    }
                ],
                "control_groups": [
                    {
                        "name": "Vehicle Control",
                        "type": "negative",
                        "purpose": "To control for the effects of the solvent (e.g., DMSO) used to dissolve Compound X.",
                        "description": "Cells treated with the same volume of vehicle (DMSO) as the experimental groups."
                    },
                    {
                        "name": "Positive Control",
                        "type": "positive",
                        "purpose": "To ensure the assay is working correctly by using a substance known to induce cell death.",
                        "description": "Cells treated with a known cytotoxic agent like Staurosporine."
                    }
                ],
                "sample_size": {
                    "biological_replicates": 3,
                    "technical_replicates": 3,
                    "power_analysis": {
                        "effect_size": 0.8,
                        "alpha": 0.05,
                        "power": 0.8,
                        "required_sample_size": 26,
                        "statistical_test": "ANOVA"
                    }
                }
            }
        } 


# --- Methodology & Protocol Models ---

class MethodologyStep(BaseModel):
    """Defines a single, sequential step in the experimental protocol."""
    step_number: int = Field(..., description="The sequential number of the step in the protocol (e.g., 1, 2, 3).")
    description: str = Field(..., description="A detailed, clear description of the action to be performed in this step.")
    parameters: Dict[str, Any] = Field(..., description="A dictionary of critical parameters for this step, such as volumes, concentrations, or temperatures (e.g., {'incubation_time': '2 hours', 'temperature': '37°C'}).")
    duration: Optional[str] = Field(None, description="The estimated time required to complete this step (e.g., '15 minutes', 'overnight').")

class MaterialEquipment(BaseModel):
    """Defines a required material, reagent, or piece of equipment for the experiment."""
    name: str = Field(..., description="The specific name of the item (e.g., 'DMEM High Glucose Medium', 'T75 Flasks', 'Confocal Microscope').")
    type: str = Field(..., description="The category of the item, such as 'reagent', 'consumable', or 'equipment'.")
    quantity: Optional[str] = Field(None, description="The estimated amount needed for the experiment (e.g., '500 mL', '10 flasks').")
    specifications: Optional[str] = Field(None, description="Any important specifications, such as grade, model, or supplier (e.g., 'Gibco, Cat# 11965092', 'Leica SP8').")

class MethodologyOutput(BaseModel):
    """
    Structured output for the MethodologyAgent.
    
    This model defines the expected output from the LLM when processing
    the methodology and protocol design stage. It ensures the agent receives a
    detailed, reproducible protocol and a comprehensive list of materials.
    """
    methodology_steps: List[MethodologyStep] = Field(..., description="A complete, step-by-step protocol for the experiment.")
    materials_equipment: List[MaterialEquipment] = Field(..., description="A comprehensive list of all materials, reagents, and equipment required.")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "methodology_steps": [
                    {
                        "step_number": 1,
                        "description": "Seed A549 cells into a 96-well plate at a density of 5,000 cells per well.",
                        "parameters": {"cell_density": "5,000 cells/well", "plate_format": "96-well"},
                        "duration": "30 minutes"
                    },
                    {
                        "step_number": 2,
                        "description": "Allow cells to adhere overnight in a CO2 incubator.",
                        "parameters": {"temperature": "37°C", "co2_level": "5%"},
                        "duration": "16 hours"
                    },
                    {
                        "step_number": 3,
                        "description": "Treat cells with varying concentrations of Compound X (0, 10, 50, 100 µM) and incubate for 48 hours.",
                        "parameters": {"concentrations": "[0, 10, 50, 100] µM", "incubation_time": "48 hours"},
                        "duration": "48 hours"
                    },
                     {
                        "step_number": 4,
                        "description": "Perform MTT assay to measure cell viability according to the manufacturer's protocol.",
                        "parameters": {"assay_kit": "Sigma, Cat# M5655"},
                        "duration": "4 hours"
                    }
                ],
                "materials_equipment": [
                    {
                        "name": "A549 human lung carcinoma cell line",
                        "type": "reagent",
                        "quantity": "1 vial",
                        "specifications": "ATCC, Cat# CCL-185"
                    },
                    {
                        "name": "DMEM High Glucose Medium",
                        "type": "reagent",
                        "quantity": "500 mL",
                        "specifications": "Gibco, Cat# 11965092"
                    },
                    {
                        "name": "96-well flat-bottom plates",
                        "type": "consumable",
                        "quantity": "5 plates",
                        "specifications": "Corning, Cat# 3596"
                    },
                    {
                        "name": "CO2 Incubator",
                        "type": "equipment",
                        "quantity": "1",
                        "specifications": "Maintained at 37°C and 5% CO2"
                    }
                ]
            }
        } 


# --- Data & Analysis Models ---

class DataCollectionPlan(BaseModel):
    """Defines the plan for how data will be collected during the experiment."""
    methods: str = Field(..., description="The specific techniques and instruments that will be used to collect data (e.g., 'Confocal microscopy for imaging, plate reader for absorbance').")
    timing: str = Field(..., description="When and how often data will be collected (e.g., 'At 24, 48, and 72-hour timepoints').")
    formats: str = Field(..., description="The file formats in which the raw data will be saved (e.g., '.czi for images, .csv for plate reader data').")
    quality_control: str = Field(..., description="Procedures to ensure data quality and consistency (e.g., 'Daily calibration of the plate reader, inclusion of positive and negative controls in every assay').")

class DataAnalysisPlan(BaseModel):
    """Defines the plan for how the collected data will be analyzed."""
    statistical_tests: str = Field(..., description="The specific statistical tests that will be used to analyze the data and test the hypothesis (e.g., 'Two-way ANOVA followed by Tukey's post-hoc test').")
    visualizations: str = Field(..., description="The types of charts and graphs that will be created to visualize the results (e.g., 'Bar charts with error bars for group comparisons, heatmaps for gene expression').")
    software: str = Field(..., description="The software that will be used for analysis and visualization (e.g., 'GraphPad Prism 9, R with ggplot2').")

class PotentialPitfall(BaseModel):
    """Identifies a potential issue, its likelihood, and a plan to mitigate it."""
    issue: str = Field(..., description="A description of the potential problem or source of error (e.g., 'Cell culture contamination').")
    likelihood: str = Field(..., description="The estimated likelihood of the issue occurring (e.g., 'Low', 'Medium', 'High').")
    mitigation: str = Field(..., description="A clear plan to prevent or handle the issue if it occurs (e.g., 'Strict aseptic technique, regular screening for mycoplasma').")

class DataOutput(BaseModel):
    """
    Structured output for the DataAgent.
    
    This model defines the expected output from the LLM when processing
    the data planning and quality assurance stage. It ensures the agent receives
    a comprehensive plan for data collection, analysis, and risk management.
    """
    data_collection_plan: DataCollectionPlan = Field(..., description="The detailed plan for data collection.")
    data_analysis_plan: DataAnalysisPlan = Field(..., description="The detailed plan for data analysis.")
    expected_outcomes: str = Field(..., description="A clear statement describing the anticipated results if the hypothesis is correct.")
    potential_pitfalls: List[PotentialPitfall] = Field(..., description="A list of at least three potential pitfalls and their mitigation strategies.")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "data_collection_plan": {
                    "methods": "Cell viability will be measured using an MTT assay with a spectrophotometric plate reader. Images will be captured on an EVOS M5000 microscope.",
                    "timing": "Data will be collected at the 48-hour timepoint after treatment.",
                    "formats": "Plate reader output will be saved as .csv files. Images will be saved as .tiff files.",
                    "quality_control": "Each plate will include vehicle controls and positive controls (Staurosporine). All measurements will be performed in triplicate."
                },
                "data_analysis_plan": {
                    "statistical_tests": "A one-way ANOVA will be used to compare the means of the different treatment groups, followed by Dunnett's test to compare each group to the vehicle control.",
                    "visualizations": "Results will be visualized as a bar chart showing mean cell viability (%) vs. Compound X concentration, with error bars representing the standard deviation.",
                    "software": "GraphPad Prism 9 will be used for statistical analysis and visualization."
                },
                "expected_outcomes": "We expect to see a dose-dependent decrease in A549 cell viability with increasing concentrations of Compound X. The positive control should show a significant reduction in viability, while the vehicle control should show high viability.",
                "potential_pitfalls": [
                    {
                        "issue": "High variability between technical replicates in the MTT assay.",
                        "likelihood": "Medium",
                        "mitigation": "Ensure consistent cell seeding density and careful, consistent pipetting technique. Exclude wells on the outer edges of the plate, which are prone to evaporation."
                    },
                    {
                        "issue": "Compound X precipitates out of solution at high concentrations.",
                        "likelihood": "Low",
                        "mitigation": "Visually inspect all solutions under a microscope before adding to cells. If precipitation is observed, prepare fresh stock solutions or test a lower concentration range."
                    },
                    {
                        "issue": "Inconsistent incubation times for different plates.",
                        "likelihood": "Medium",
                        "mitigation": "Use a detailed and timed worksheet to ensure all plates are processed with identical incubation periods. Process plates in small, manageable batches."
                    }
                ]
            }
        } 


# --- Final Review & Export Models ---

class ReviewOutput(BaseModel):
    """
    Structured output for the ReviewAgent.
    
    This model defines the expected output from the LLM after it performs a
    holistic review of the entire experiment plan. It ensures the agent receives
    a comprehensive, actionable assessment.
    """
    quality_score: int = Field(..., description="An overall quality score for the experiment plan, from 0 to 100.", ge=0, le=100)
    strengths: List[str] = Field(..., description="A list of the strongest aspects of the experimental plan.")
    suggestions_for_improvement: List[str] = Field(..., description="A list of specific, actionable suggestions to improve the plan's robustness and clarity.")
    final_summary: str = Field(..., description="A concise, executive summary of the complete experimental plan, suitable for export.")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "quality_score": 92,
                "strengths": [
                    "The research objective is clear and the hypothesis is directly testable.",
                    "The experimental design includes both positive and negative controls, which will provide robust data.",
                    "The sample size calculation is well-justified with a statistical power analysis."
                ],
                "suggestions_for_improvement": [
                    "Consider adding a third timepoint (e.g., 72 hours) to the data collection plan to observe long-term effects of Compound X.",
                    "Specify the supplier and catalog number for the MTT assay kit in the materials list to ensure reproducibility.",
                    "The data analysis plan could be strengthened by mentioning a test for normality (e.g., Shapiro-Wilk test) before applying the ANOVA."
                ],
                "final_summary": "This experiment aims to determine the effect of varying concentrations of Compound X on A549 lung cancer cell viability. The plan outlines a well-controlled experiment using an MTT assay, with a sample size of 26 per group determined by a power analysis. Data will be analyzed using a one-way ANOVA. Key risks, such as replicate variability, have been identified and mitigated. The expected outcome is a dose-dependent decrease in cell viability."
            }
        }


class StageClassificationOutput(BaseModel):
    """
    Structured output for determining which planning stage a user wants to edit.
    
    This model ensures reliable classification of user edit requests to the correct
    planning stage based on context and content analysis.
    """
    target_stage: str = Field(
        ..., 
        description="The planning stage that best matches the user's edit request. Must be one of: objective_setting, variable_identification, experimental_design, methodology_protocol, data_planning, final_review"
    )
    confidence: float = Field(
        ..., 
        description="Confidence level in the classification decision, from 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this stage was chosen based on the user's request and current context"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "target_stage": "variable_identification",
                "confidence": 0.95,
                "reasoning": "User wants to modify dependent variables and control variables, which are core components of the variable identification stage."
            }
        } 