/**
 * Database API functions
 * 
 * This module provides functions to interact with the database service
 * through the /api/database endpoint for managing experiments.
 */

const BASE_URL = 'http://localhost:8000/api/database'

export interface Experiment {
  id: string
  title?: string
  description?: string
  experimental_plan?: string
  visualization_html?: string
  csv_data?: string
  previous_csv?: string
  csv_version: number
  agent_modified_at?: string
  modification_source: string
  created_at: string
  updated_at: string
}

export interface CreateExperimentRequest {
  title?: string
  description?: string
  experimental_plan?: string
  visualization_html?: string
  csv_data?: string
}

export interface UpdateExperimentRequest {
  experimental_plan?: string
  visualization_html?: string
  csv_data?: string
}

export interface DatabaseError {
  error: string
  message: string
  details?: string
}

/**
 * Creates a new experiment
 * 
 * @param request - The experiment data to create
 * @returns Promise resolving to the created experiment
 * @throws Error if the request fails or returns an error
 */
export async function createExperiment(request: CreateExperimentRequest): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to create experiment: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while creating experiment')
  }
}

/**
 * Gets all experiments
 * 
 * @returns Promise resolving to array of experiments
 * @throws Error if the request fails or returns an error
 */
export async function getExperiments(): Promise<Experiment[]> {
  try {
    const response = await fetch(`${BASE_URL}/experiments`)

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to fetch experiments: ${errorData.message}`)
    }

    const result: { experiments: Experiment[], total_count: number } = await response.json()
    return result.experiments
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while fetching experiments')
  }
}

/**
 * Gets a specific experiment by ID
 * 
 * @param id - The experiment ID
 * @returns Promise resolving to the experiment
 * @throws Error if the request fails or returns an error
 */
export async function getExperiment(id: string): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}`)

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to fetch experiment: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while fetching experiment')
  }
}

/**
 * Updates the experimental plan for an experiment
 * 
 * @param id - The experiment ID
 * @param plan - The new experimental plan
 * @returns Promise resolving to the updated experiment
 * @throws Error if the request fails or returns an error
 */
export async function updateExperimentPlan(id: string, plan: string): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}/plan`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ experimental_plan: plan }),
    })

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to update experiment plan: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while updating experiment plan')
  }
}

/**
 * Updates the visualization HTML for an experiment
 * 
 * @param id - The experiment ID
 * @param html - The new visualization HTML
 * @returns Promise resolving to the updated experiment
 * @throws Error if the request fails or returns an error
 */
export async function updateExperimentHtml(id: string, html: string): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}/html`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ visualization_html: html }),
    })

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to update experiment HTML: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while updating experiment HTML')
  }
}

/**
 * Updates the CSV data for an experiment
 * 
 * @param id - The experiment ID
 * @param csv - The new CSV data
 * @param options - Optional parameters for versioning
 * @returns Promise resolving to the updated experiment
 * @throws Error if the request fails or returns an error
 */
export async function updateExperimentCsv(
  id: string, 
  csv: string,
  options?: {
    isAgentUpdate?: boolean
    expectedVersion?: number
  }
): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}/csv`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        csv_data: csv,
        is_agent_update: options?.isAgentUpdate || false,
        expected_version: options?.expectedVersion
      }),
    })

    if (!response.ok) {
      if (response.status === 409) {
        throw new Error('Version conflict: The data has been modified by another process')
      }
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to update experiment CSV: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while updating experiment CSV')
  }
}

/**
 * Updates the title for an experiment
 * 
 * @param id - The experiment ID
 * @param title - The new experiment title
 * @returns Promise resolving to the updated experiment
 * @throws Error if the request fails or returns an error
 */
export async function updateExperimentTitle(id: string, title: string): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}/title`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    })

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to update experiment title: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while updating experiment title')
  }
}

/**
 * Deletes an experiment
 * 
 * @param id - The experiment ID
 * @returns Promise resolving when deletion is complete
 * @throws Error if the request fails or returns an error
 */
export async function deleteExperiment(id: string): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to delete experiment: ${errorData.message}`)
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while deleting experiment')
  }
}

export interface ExperimentDiff {
  experiment_id: string
  has_diff: boolean
  current_csv?: string
  previous_csv?: string
  csv_version?: number
  agent_modified_at?: string
  modification_source?: string
  message?: string
}

/**
 * Get CSV differences for an experiment
 * 
 * @param id - The experiment ID
 * @returns Promise resolving to diff information
 * @throws Error if the request fails
 */
export async function getExperimentDiff(id: string): Promise<ExperimentDiff> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}/diff`)

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to get experiment diff: ${errorData.message}`)
    }

    const result: ExperimentDiff = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while getting experiment diff')
  }
}

/**
 * Accept or reject CSV changes for an experiment
 * 
 * @param id - The experiment ID
 * @param action - 'accept' or 'reject'
 * @returns Promise resolving to the updated experiment
 * @throws Error if the request fails
 */
export async function acceptRejectCsvChanges(
  id: string, 
  action: 'accept' | 'reject'
): Promise<Experiment> {
  try {
    const response = await fetch(`${BASE_URL}/experiments/${id}/csv/accept-reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ action }),
    })

    if (!response.ok) {
      const errorData: DatabaseError = await response.json()
      throw new Error(`Failed to ${action} CSV changes: ${errorData.message}`)
    }

    const result: Experiment = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error(`Unknown error occurred while ${action}ing CSV changes`)
  }
} 