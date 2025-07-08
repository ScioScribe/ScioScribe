/**
 * Data cleaning API functions
 * 
 * This module provides functions to interact with the data cleaning service
 * through the /api/dataclean endpoint.
 */

const BASE_URL = '/api/dataclean'

export interface DataCleanRequest {
  data: unknown[]
  options?: {
    removeNulls?: boolean
    removeDuplicates?: boolean
    standardizeFormats?: boolean
    fillMissingValues?: boolean
  }
}

export interface DataCleanResponse {
  success: boolean
  data: unknown[]
  message?: string
  stats?: {
    originalRows: number
    cleanedRows: number
    removedRows: number
    modifications: string[]
  }
}

export interface DataCleanError {
  error: string
  message: string
  details?: string
}

/**
 * Cleans the provided dataset using the data cleaning service
 * 
 * @param request - The data cleaning request containing data and options
 * @returns Promise resolving to cleaned data response
 * @throws Error if the request fails or returns an error
 */
export async function cleanData(request: DataCleanRequest): Promise<DataCleanResponse> {
  try {
    const response = await fetch(BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Data cleaning failed: ${errorData.message}`)
    }

    const result: DataCleanResponse = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during data cleaning')
  }
}

/**
 * Validates data format before cleaning
 * 
 * @param data - The data to validate
 * @returns Promise resolving to validation result
 */
export async function validateDataFormat(data: unknown[]): Promise<{
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
      body: JSON.stringify({ data }),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Data validation failed: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred during data validation')
  }
}

/**
 * Gets available data cleaning options and their descriptions
 * 
 * @returns Promise resolving to available cleaning options
 */
export async function getCleaningOptions(): Promise<{
  options: Array<{
    key: string
    name: string
    description: string
    default: boolean
  }>
}> {
  try {
    const response = await fetch(`${BASE_URL}/options`)

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to fetch cleaning options: ${errorData.message}`)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while fetching cleaning options')
  }
} 