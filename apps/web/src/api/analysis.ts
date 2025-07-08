/**
 * Analysis API functions
 * 
 * This module provides functions to interact with the data analysis service
 * through the /api/analysis endpoint.
 */

const BASE_URL = '/api/analysis'

export interface AnalysisRequest {
  data: unknown[]
  analysisType: 'descriptive' | 'exploratory' | 'statistical' | 'predictive'
  options?: {
    includeCharts?: boolean
    includeCorrelations?: boolean
    includeOutliers?: boolean
    confidenceLevel?: number
  }
}

export interface AnalysisResponse {
  success: boolean
  results: {
    summary: {
      totalRows: number
      totalColumns: number
      dataTypes: Record<string, string>
      missingValues: Record<string, number>
    }
    statistics?: {
      numerical: Record<string, {
        mean: number
        median: number
        mode: number
        standardDeviation: number
        min: number
        max: number
        quartiles: [number, number, number]
      }>
      categorical: Record<string, {
        uniqueValues: number
        mostFrequent: string
        frequency: Record<string, number>
      }>
    }
    correlations?: Record<string, Record<string, number>>
    outliers?: Array<{
      column: string
      value: unknown
      index: number
      score: number
    }>
    charts?: Array<{
      type: 'bar' | 'line' | 'scatter' | 'histogram' | 'box'
      data: unknown
      config: Record<string, unknown>
    }>
  }
  message?: string
}

export interface AnalysisError {
  error: string
  message: string
  details?: string
}

/**
 * Performs data analysis on the provided dataset
 * 
 * @param request - The analysis request containing data and analysis options
 * @returns Promise resolving to analysis results
 * @throws Error if the request fails or returns an error
 */
export async function analyzeData(request: AnalysisRequest): Promise<AnalysisResponse> {
  try {
    const response = await fetch(BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Analysis failed: ${errorData.message}`)
    }

    const result: AnalysisResponse = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during analysis')
  }
}

/**
 * Generates a specific type of chart from the data
 * 
 * @param data - The dataset to visualize
 * @param chartType - The type of chart to generate
 * @param options - Chart configuration options
 * @returns Promise resolving to chart data and configuration
 */
export async function generateChart(
  data: unknown[],
  chartType: 'bar' | 'line' | 'scatter' | 'histogram' | 'box',
  options?: {
    xAxis?: string
    yAxis?: string
    groupBy?: string
    title?: string
    colors?: string[]
  }
): Promise<{
  success: boolean
  chartData: unknown
  config: Record<string, unknown>
  htmlOutput?: string
}> {
  try {
    const response = await fetch(`${BASE_URL}/chart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        data,
        chartType,
        options,
      }),
    })

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Chart generation failed: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during chart generation')
  }
}

/**
 * Gets insights and recommendations based on the data analysis
 * 
 * @param analysisResults - The results from a previous analysis
 * @returns Promise resolving to insights and recommendations
 */
export async function getInsights(analysisResults: AnalysisResponse['results']): Promise<{
  insights: Array<{
    type: 'trend' | 'anomaly' | 'pattern' | 'recommendation'
    title: string
    description: string
    confidence: number
    data?: unknown
  }>
}> {
  try {
    const response = await fetch(`${BASE_URL}/insights`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ results: analysisResults }),
    })

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Insights generation failed: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during insights generation')
  }
}

/**
 * Gets available analysis types and their descriptions
 * 
 * @returns Promise resolving to available analysis types
 */
export async function getAnalysisTypes(): Promise<{
  types: Array<{
    key: string
    name: string
    description: string
    requiredFields: string[]
    optionalFields: string[]
  }>
}> {
  try {
    const response = await fetch(`${BASE_URL}/types`)

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Failed to fetch analysis types: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while fetching analysis types')
  }
} 