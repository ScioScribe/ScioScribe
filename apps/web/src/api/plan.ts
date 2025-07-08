/**
 * Plan API functions
 * 
 * This module provides functions to interact with the experiment planning service
 * through the /api/plan endpoint.
 */

const BASE_URL = '/api/plan'

export interface PlanRequest {
  objective: string
  dataDescription?: string
  constraints?: {
    timeLimit?: string
    budget?: number
    resources?: string[]
    technicalRequirements?: string[]
  }
  preferences?: {
    analysisType?: 'descriptive' | 'exploratory' | 'confirmatory' | 'predictive'
    complexity?: 'simple' | 'intermediate' | 'advanced'
    visualization?: boolean
    statisticalTests?: boolean
  }
}

export interface PlanResponse {
  success: boolean
  plan: {
    title: string
    objective: string
    overview: string
    steps: Array<{
      id: string
      title: string
      description: string
      estimatedTime: string
      prerequisites: string[]
      deliverables: string[]
      resources: string[]
      order: number
    }>
    timeline: {
      totalEstimatedTime: string
      phases: Array<{
        name: string
        duration: string
        steps: string[]
      }>
    }
    requirements: {
      data: string[]
      tools: string[]
      skills: string[]
      resources: string[]
    }
    expectedOutcomes: string[]
    risks: Array<{
      risk: string
      probability: 'low' | 'medium' | 'high'
      impact: 'low' | 'medium' | 'high'
      mitigation: string
    }>
    qualityChecks: string[]
  }
  message?: string
}

export interface PlanError {
  error: string
  message: string
  details?: string
}

/**
 * Generates an experiment plan based on the provided objective and constraints
 * 
 * @param request - The plan request containing objective and preferences
 * @returns Promise resolving to generated experiment plan
 * @throws Error if the request fails or returns an error
 */
export async function generatePlan(request: PlanRequest): Promise<PlanResponse> {
  try {
    const response = await fetch(BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: PlanError = await response.json()
      throw new Error(`Plan generation failed: ${errorData.message}`)
    }

    const result: PlanResponse = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during plan generation')
  }
}

/**
 * Validates a plan request before generating the plan
 * 
 * @param request - The plan request to validate
 * @returns Promise resolving to validation result
 */
export async function validatePlanRequest(request: PlanRequest): Promise<{
  valid: boolean
  issues: string[]
  suggestions: string[]
}> {
  try {
    const response = await fetch(`${BASE_URL}/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: PlanError = await response.json()
      throw new Error(`Plan validation failed: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during plan validation')
  }
}

/**
 * Updates an existing plan with new requirements or modifications
 * 
 * @param planId - The ID of the plan to update
 * @param updates - The updates to apply to the plan
 * @returns Promise resolving to updated plan
 */
export async function updatePlan(
  planId: string,
  updates: Partial<PlanRequest>
): Promise<PlanResponse> {
  try {
    const response = await fetch(`${BASE_URL}/${planId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      const errorData: PlanError = await response.json()
      throw new Error(`Plan update failed: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during plan update')
  }
}

/**
 * Gets plan templates for common experiment types
 * 
 * @returns Promise resolving to available plan templates
 */
export async function getPlanTemplates(): Promise<{
  templates: Array<{
    id: string
    name: string
    description: string
    category: string
    objective: string
    estimatedTime: string
    complexity: 'simple' | 'intermediate' | 'advanced'
    tags: string[]
  }>
}> {
  try {
    const response = await fetch(`${BASE_URL}/templates`)

    if (!response.ok) {
      const errorData: PlanError = await response.json()
      throw new Error(`Failed to fetch plan templates: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while fetching plan templates')
  }
}

/**
 * Creates a plan from a template with custom modifications
 * 
 * @param templateId - The ID of the template to use
 * @param customizations - Custom modifications to apply to the template
 * @returns Promise resolving to generated plan from template
 */
export async function createPlanFromTemplate(
  templateId: string,
  customizations?: {
    objective?: string
    constraints?: PlanRequest['constraints']
    preferences?: PlanRequest['preferences']
  }
): Promise<PlanResponse> {
  try {
    const response = await fetch(`${BASE_URL}/template/${templateId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(customizations || {}),
    })

    if (!response.ok) {
      const errorData: PlanError = await response.json()
      throw new Error(`Plan creation from template failed: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during plan creation from template')
  }
}

/**
 * Exports a plan to different formats (markdown, pdf, etc.)
 * 
 * @param planId - The ID of the plan to export
 * @param format - The export format
 * @returns Promise resolving to exported plan data
 */
export async function exportPlan(
  planId: string,
  format: 'markdown' | 'pdf' | 'json' | 'html'
): Promise<{
  success: boolean
  data: string | ArrayBuffer
  filename: string
  contentType: string
}> {
  try {
    const response = await fetch(`${BASE_URL}/${planId}/export?format=${format}`)

    if (!response.ok) {
      const errorData: PlanError = await response.json()
      throw new Error(`Plan export failed: ${errorData.message}`)
    }

    const contentType = response.headers.get('content-type') || 'application/octet-stream'
    const filename = response.headers.get('content-disposition')?.split('filename=')[1] || `plan.${format}`

    const data = format === 'pdf' ? await response.arrayBuffer() : await response.text()

    return {
      success: true,
      data,
      filename,
      contentType,
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during plan export')
  }
} 