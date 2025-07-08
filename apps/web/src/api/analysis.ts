/**
 * Analysis API functions
 * 
 * This module provides functions to interact with the chart generation service
 * through the /api/analysis/generate-chart endpoint.
 */

const BASE_URL = '/api/analysis'

export interface GenerateChartRequest {
  prompt: string
  plan: string
  csv: string
}

export interface GenerateChartResponse {
  html: string
}

export interface AnalysisError {
  error: string
  message: string
  details?: string
}

/**
 * Generates a Plotly chart based on user prompt, plan, and CSV data
 * 
 * @param request - The chart generation request containing prompt, plan, and CSV data
 * @returns Promise resolving to HTML containing the Plotly chart
 * @throws Error if the request fails or returns an error
 */
export async function generateChart(request: GenerateChartRequest): Promise<GenerateChartResponse> {
  try {
    const response = await fetch(`${BASE_URL}/generate-chart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Chart generation failed: ${errorData.message}`)
    }

    const result: GenerateChartResponse = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during chart generation')
  }
} 