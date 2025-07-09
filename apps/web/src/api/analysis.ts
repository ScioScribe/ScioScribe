/**
 * Analysis API functions
 * 
 * This module provides functions to interact with the visualization generation service
 * through the /api/analysis/generate-visualization endpoint.
 */

const BASE_URL = 'http://localhost:8000/api/analysis'

export interface GenerateVisualizationRequest {
  prompt: string
  plan: string
  csv: string
}

export interface GenerateVisualizationResponse {
  html: string
  message: string
}

export interface AnalysisError {
  error: string
  message: string
  details?: string
}

/**
 * Generates a Plotly visualization based on user prompt, plan, and CSV data
 * 
 * @param request - The visualization generation request containing prompt, plan, and CSV data
 * @returns Promise resolving to HTML containing the Plotly visualization
 * @throws Error if the request fails or returns an error
 */
export async function generateVisualization(request: GenerateVisualizationRequest): Promise<GenerateVisualizationResponse> {
  try {
    const response = await fetch(`${BASE_URL}/generate-visualization`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Visualization generation failed: ${errorData.message}`)
    }

    const result: GenerateVisualizationResponse = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during visualization generation')
  }
} 