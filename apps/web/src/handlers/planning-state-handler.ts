/**
 * Planning State Handler
 * 
 * This module handles the conversion of raw planning state from the backend
 * into readable, structured text for display in the text editor.
 * It filters out technical details and focuses on user-relevant information.
 */

// Type definitions matching the backend planning state structure
interface ExperimentPlanState {
  // Core Identification
  experiment_id: string
  research_query: string
  experiment_objective?: string
  hypothesis?: string
  
  // Variables
  independent_variables: Array<{
    name: string
    type: string
    units: string
    levels: string[]
  }>
  dependent_variables: Array<{
    name: string
    type: string
    units: string
    measurement_method: string
  }>
  control_variables: Array<{
    name: string
    reason: string
    control_method: string
  }>
  
  // Experimental Design
  experimental_groups: Array<{
    name: string
    description: string
    conditions: Record<string, any>
  }>
  control_groups: Array<{
    type: string
    purpose: string
    description: string
  }>
  sample_size: {
    biological_replicates?: number
    technical_replicates?: number
    power_analysis?: string
  }
  
  // Methodology
  methodology_steps: Array<{
    step_number: number
    description: string
    parameters: Record<string, any>
    duration: string
  }>
  materials_equipment: Array<{
    name: string
    type: string
    quantity: string
    specifications: string
  }>
  
  // Data & Analysis
  data_collection_plan: {
    methods?: string[] | string
    timing?: string
    formats?: string[] | string
  }
  data_analysis_plan: {
    statistical_tests?: string[] | string
    visualizations?: string[] | string
    software?: string[] | string
  }
  expected_outcomes?: string
  potential_pitfalls: Array<{
    issue: string
    likelihood: string
    mitigation: string
  }>
  
  // Administrative (Optional)
  ethical_considerations?: string
  timeline?: Record<string, any>
  budget_estimate?: Record<string, any>
  
  // System State (to be filtered out)
  current_stage: string
  errors: string[]
  chat_history: Array<Record<string, any>>
}

/**
 * Converts raw planning state to readable, structured text
 * @param rawState Raw planning state from backend
 * @returns Formatted text for display in editor
 */
export function convertPlanningStateToText(rawState: Record<string, any>): string {
  try {
    if (!rawState || typeof rawState !== 'object') {
      return "# Experiment Plan\n\n*No planning data available yet. Start a planning session to begin.*"
    }

    const state = rawState as Partial<ExperimentPlanState>
    const sections: string[] = []

    // Header with research query
    sections.push("# Experiment Plan")
    
    if (state.research_query) {
      sections.push(`\n## Research Query\n${state.research_query}`)
    }

    // Core objectives and hypothesis
    if (state.experiment_objective) {
      sections.push(`\n## Objective\n${state.experiment_objective}`)
    }

    if (state.hypothesis) {
      sections.push(`\n## Hypothesis\n${state.hypothesis}`)
    }

    // Variables section
    if (hasVariables(state)) {
      sections.push(formatVariablesSection(state))
    }

    // Experimental design
    if (hasExperimentalDesign(state)) {
      sections.push(formatExperimentalDesignSection(state))
    }

    // Methodology
    if (hasMethodology(state)) {
      sections.push(formatMethodologySection(state))
    }

    // Data collection and analysis
    if (hasDataPlanning(state)) {
      sections.push(formatDataPlanningSection(state))
    }

    // Risk assessment
    if (state.potential_pitfalls && state.potential_pitfalls.length > 0) {
      sections.push(formatRiskAssessmentSection(state.potential_pitfalls))
    }

    // Administrative details
    if (hasAdministrativeDetails(state)) {
      sections.push(formatAdministrativeSection(state))
    }

    // Add planning status at the end
    sections.push(formatPlanningStatus(state))

    return sections.join('\n')

  } catch (error) {
    console.error("❌ Error converting planning state to text:", error)
    return `# Experiment Plan\n\n*Error formatting planning data: ${error instanceof Error ? error.message : 'Unknown error'}*`
  }
}

/**
 * Check if state contains variable information
 */
function hasVariables(state: Partial<ExperimentPlanState>): boolean {
  return !!(
    (state.independent_variables && state.independent_variables.length > 0) ||
    (state.dependent_variables && state.dependent_variables.length > 0) ||
    (state.control_variables && state.control_variables.length > 0)
  )
}

/**
 * Format variables section
 */
function formatVariablesSection(state: Partial<ExperimentPlanState>): string {
  const sections: string[] = ['\n## Variables']

  if (state.independent_variables && state.independent_variables.length > 0) {
    sections.push('\n### Independent Variables')
    state.independent_variables.forEach(variable => {
      sections.push(`**${variable.name}**`)
      sections.push(`- Type: ${variable.type}`)
      sections.push(`- Units: ${variable.units}`)
      if (variable.levels && variable.levels.length > 0) {
        sections.push(`- Levels: ${variable.levels.join(', ')}`)
      }
      sections.push('')
    })
  }

  if (state.dependent_variables && state.dependent_variables.length > 0) {
    sections.push('\n### Dependent Variables')
    state.dependent_variables.forEach(variable => {
      sections.push(`**${variable.name}**`)
      sections.push(`- Type: ${variable.type}`)
      sections.push(`- Units: ${variable.units}`)
      sections.push(`- Measurement: ${variable.measurement_method}`)
      sections.push('')
    })
  }

  if (state.control_variables && state.control_variables.length > 0) {
    sections.push('\n### Control Variables')
    state.control_variables.forEach(variable => {
      sections.push(`**${variable.name}**`)
      sections.push(`- Reason: ${variable.reason}`)
      sections.push(`- Control Method: ${variable.control_method}`)
      sections.push('')
    })
  }

  return sections.join('\n')
}

/**
 * Check if state contains experimental design information
 */
function hasExperimentalDesign(state: Partial<ExperimentPlanState>): boolean {
  return !!(
    (state.experimental_groups && state.experimental_groups.length > 0) ||
    (state.control_groups && state.control_groups.length > 0) ||
    state.sample_size
  )
}

/**
 * Format experimental design section
 */
function formatExperimentalDesignSection(state: Partial<ExperimentPlanState>): string {
  const sections: string[] = ['\n## Experimental Design']

  if (state.experimental_groups && state.experimental_groups.length > 0) {
    sections.push('\n### Experimental Groups')
    state.experimental_groups.forEach(group => {
      sections.push(`**${group.name}**`)
      sections.push(`${group.description}`)
      if (group.conditions && Object.keys(group.conditions).length > 0) {
        sections.push('Conditions:')
        Object.entries(group.conditions).forEach(([key, value]) => {
          sections.push(`- ${key}: ${value}`)
        })
      }
      sections.push('')
    })
  }

  if (state.control_groups && state.control_groups.length > 0) {
    sections.push('\n### Control Groups')
    state.control_groups.forEach(group => {
      sections.push(`**${group.type}**`)
      sections.push(`Purpose: ${group.purpose}`)
      sections.push(`${group.description}`)
      sections.push('')
    })
  }

  if (state.sample_size) {
    sections.push('\n### Sample Size')
    if (state.sample_size.biological_replicates) {
      sections.push(`- Biological replicates: ${state.sample_size.biological_replicates}`)
    }
    if (state.sample_size.technical_replicates) {
      sections.push(`- Technical replicates: ${state.sample_size.technical_replicates}`)
    }
    if (state.sample_size.power_analysis) {
      sections.push(`- Power analysis: ${state.sample_size.power_analysis}`)
    }
  }

  return sections.join('\n')
}

/**
 * Check if state contains methodology information
 */
function hasMethodology(state: Partial<ExperimentPlanState>): boolean {
  return !!(
    (state.methodology_steps && state.methodology_steps.length > 0) ||
    (state.materials_equipment && state.materials_equipment.length > 0)
  )
}

/**
 * Format methodology section
 */
function formatMethodologySection(state: Partial<ExperimentPlanState>): string {
  const sections: string[] = ['\n## Methodology']

  if (state.methodology_steps && state.methodology_steps.length > 0) {
    sections.push('\n### Procedure')
    state.methodology_steps
      .sort((a, b) => a.step_number - b.step_number)
      .forEach(step => {
        sections.push(`${step.step_number}. ${step.description}`)
        if (step.duration) {
          sections.push(`   Duration: ${step.duration}`)
        }
        if (step.parameters && Object.keys(step.parameters).length > 0) {
          sections.push('   Parameters:')
          Object.entries(step.parameters).forEach(([key, value]) => {
            sections.push(`   - ${key}: ${value}`)
          })
        }
        sections.push('')
      })
  }

  if (state.materials_equipment && state.materials_equipment.length > 0) {
    sections.push('\n### Materials and Equipment')
    state.materials_equipment.forEach(item => {
      sections.push(`**${item.name}** (${item.type})`)
      sections.push(`- Quantity: ${item.quantity}`)
      if (item.specifications) {
        sections.push(`- Specifications: ${item.specifications}`)
      }
      sections.push('')
    })
  }

  return sections.join('\n')
}

/**
 * Check if state contains data planning information
 */
function hasDataPlanning(state: Partial<ExperimentPlanState>): boolean {
  return !!(
    state.data_collection_plan ||
    state.data_analysis_plan ||
    state.expected_outcomes
  )
}

/**
 * Format data planning section
 */
function formatDataPlanningSection(state: Partial<ExperimentPlanState>): string {
  const sections: string[] = ['\n## Data Collection & Analysis']

  if (state.data_collection_plan) {
    sections.push('\n### Data Collection')
    
    // Handle methods - could be array or string
    if (state.data_collection_plan.methods) {
      if (Array.isArray(state.data_collection_plan.methods) && state.data_collection_plan.methods.length > 0) {
        sections.push(`Methods: ${state.data_collection_plan.methods.join(', ')}`)
      } else if (typeof state.data_collection_plan.methods === 'string') {
        sections.push(`Methods: ${state.data_collection_plan.methods}`)
      }
    }
    
    if (state.data_collection_plan.timing) {
      sections.push(`Timing: ${state.data_collection_plan.timing}`)
    }
    
    // Handle formats - could be array or string
    if (state.data_collection_plan.formats) {
      if (Array.isArray(state.data_collection_plan.formats) && state.data_collection_plan.formats.length > 0) {
        sections.push(`Formats: ${state.data_collection_plan.formats.join(', ')}`)
      } else if (typeof state.data_collection_plan.formats === 'string') {
        sections.push(`Formats: ${state.data_collection_plan.formats}`)
      }
    }
  }

  if (state.data_analysis_plan) {
    sections.push('\n### Data Analysis')
    
    // Handle statistical_tests - could be array or string
    if (state.data_analysis_plan.statistical_tests) {
      if (Array.isArray(state.data_analysis_plan.statistical_tests) && state.data_analysis_plan.statistical_tests.length > 0) {
        sections.push(`Statistical Tests: ${state.data_analysis_plan.statistical_tests.join(', ')}`)
      } else if (typeof state.data_analysis_plan.statistical_tests === 'string') {
        sections.push(`Statistical Tests: ${state.data_analysis_plan.statistical_tests}`)
      }
    }
    
    // Handle visualizations - could be array or string
    if (state.data_analysis_plan.visualizations) {
      if (Array.isArray(state.data_analysis_plan.visualizations) && state.data_analysis_plan.visualizations.length > 0) {
        sections.push(`Visualizations: ${state.data_analysis_plan.visualizations.join(', ')}`)
      } else if (typeof state.data_analysis_plan.visualizations === 'string') {
        sections.push(`Visualizations: ${state.data_analysis_plan.visualizations}`)
      }
    }
    
    // Handle software - could be array or string
    if (state.data_analysis_plan.software) {
      if (Array.isArray(state.data_analysis_plan.software) && state.data_analysis_plan.software.length > 0) {
        sections.push(`Software: ${state.data_analysis_plan.software.join(', ')}`)
      } else if (typeof state.data_analysis_plan.software === 'string') {
        sections.push(`Software: ${state.data_analysis_plan.software}`)
      }
    }
  }

  if (state.expected_outcomes) {
    sections.push('\n### Expected Outcomes')
    sections.push(state.expected_outcomes)
  }

  return sections.join('\n')
}

/**
 * Format risk assessment section
 */
function formatRiskAssessmentSection(pitfalls: Array<{ issue: string; likelihood: string; mitigation: string }>): string {
  const sections: string[] = ['\n## Risk Assessment']

  pitfalls.forEach(pitfall => {
    sections.push(`**${pitfall.issue}**`)
    sections.push(`- Likelihood: ${pitfall.likelihood}`)
    sections.push(`- Mitigation: ${pitfall.mitigation}`)
    sections.push('')
  })

  return sections.join('\n')
}

/**
 * Check if state contains administrative details
 */
function hasAdministrativeDetails(state: Partial<ExperimentPlanState>): boolean {
  return !!(
    state.ethical_considerations ||
    state.timeline ||
    state.budget_estimate
  )
}

/**
 * Format administrative section
 */
function formatAdministrativeSection(state: Partial<ExperimentPlanState>): string {
  const sections: string[] = ['\n## Administrative Details']

  if (state.ethical_considerations) {
    sections.push('\n### Ethical Considerations')
    sections.push(state.ethical_considerations)
  }

  if (state.timeline && Object.keys(state.timeline).length > 0) {
    sections.push('\n### Timeline')
    Object.entries(state.timeline).forEach(([phase, duration]) => {
      sections.push(`- ${phase}: ${duration}`)
    })
  }

  if (state.budget_estimate && Object.keys(state.budget_estimate).length > 0) {
    sections.push('\n### Budget Estimate')
    Object.entries(state.budget_estimate).forEach(([category, amount]) => {
      sections.push(`- ${category}: ${amount}`)
    })
  }

  return sections.join('\n')
}

/**
 * Format planning status section
 */
function formatPlanningStatus(state: Partial<ExperimentPlanState>): string {
  const sections: string[] = ['\n---\n## Planning Status']

  if (state.current_stage) {
    const stageNames: Record<string, string> = {
      'objective_setting': 'Objective Setting',
      'variable_identification': 'Variable Identification',
      'experimental_design': 'Experimental Design',
      'methodology_protocol': 'Methodology Protocol',
      'data_planning': 'Data Planning',
      'final_review': 'Final Review'
    }
    
    const stageName = stageNames[state.current_stage] || state.current_stage
    sections.push(`Current Stage: ${stageName}`)
  }

  // Show completion status based on available data
  const completedSections: string[] = []
  if (state.experiment_objective) completedSections.push('Objective')
  if (hasVariables(state)) completedSections.push('Variables')
  if (hasExperimentalDesign(state)) completedSections.push('Design')
  if (hasMethodology(state)) completedSections.push('Methodology')
  if (hasDataPlanning(state)) completedSections.push('Data Planning')

  if (completedSections.length > 0) {
    sections.push(`Completed Sections: ${completedSections.join(', ')}`)
  }

  sections.push(`\n*Last updated: ${new Date().toLocaleString()}*`)

  return sections.join('\n')
}

/**
 * Legacy function for backward compatibility
 * Maintains the same interface as the original function
 */
export function convertPlanningStateToString(planningState: Record<string, any>): string {
  return convertPlanningStateToText(planningState)
}