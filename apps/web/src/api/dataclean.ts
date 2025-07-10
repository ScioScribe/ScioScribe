/**
 * Data cleaning API functions
 * 
 * This module provides functions to interact with the data cleaning service
 * through the /api/dataclean endpoint.
 */

const BASE_URL = 'http://localhost:8000/api/dataclean'

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

// Conversation API interfaces and functions
export interface StartConversationRequest {
  user_id?: string
  session_id?: string
  artifact_id?: string
  file_path?: string
}

export interface StartConversationResponse {
  session_id: string
  user_id: string
  status: string
  message: string
  capabilities: string[]
  session_info: {
    created_at: string
    session_type: string
    state: string
  }
}

export interface ConversationMessageRequest {
  user_message: string
  session_id: string
  user_id?: string
  artifact_id?: string
}

export interface ConversationMessageResponse {
  session_id: string
  response_type: "text" | "data_preview" | "suggestion" | "confirmation" | "error"
  message: string
  data?: unknown
  suggestions?: Array<{
    id: string
    type: string
    description: string
    confidence: number
  }>
  requires_confirmation?: boolean
  next_steps?: string[]
}

export interface ConversationConfirmationRequest {
  session_id: string
  confirmed: boolean
  user_id?: string
}

export interface ConversationSessionSummary {
  session_id: string
  user_id: string
  status: string
  created_at: string
  last_activity: string
  message_count: number
  operations_performed: number
  current_state: string
}

export interface ConversationCapabilitiesResponse {
  status: string
  capabilities: {
    supported_intents: string[]
    supported_operations: string[]
    supported_formats: string[]
    features: string[]
  }
}

/**
 * Start a new conversation session for data cleaning
 * 
 * @param request - The conversation start request
 * @returns Promise resolving to session information
 */
export async function startConversation(request: StartConversationRequest): Promise<StartConversationResponse> {
  try {
    const response = await fetch(`${BASE_URL}/conversation/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to start conversation: ${errorData.message}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error starting conversation:", error)
    throw error
  }
}

/**
 * Send a message in an active conversation session
 * 
 * @param request - The conversation message request
 * @returns Promise resolving to conversation response
 */
export async function sendConversationMessage(request: ConversationMessageRequest): Promise<ConversationMessageResponse> {
  try {
    const response = await fetch(`${BASE_URL}/conversation/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to send message: ${errorData.message}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error sending conversation message:", error)
    throw error
  }
}

/**
 * Handle confirmation for operations that require approval
 * 
 * @param request - The confirmation request
 * @returns Promise resolving to confirmation response
 */
export async function handleConversationConfirmation(request: ConversationConfirmationRequest): Promise<ConversationMessageResponse> {
  try {
    const response = await fetch(`${BASE_URL}/conversation/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to handle confirmation: ${errorData.message}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error handling confirmation:", error)
    throw error
  }
}

/**
 * Get conversation session summary
 * 
 * @param sessionId - The session ID
 * @returns Promise resolving to session summary
 */
export async function getConversationSession(sessionId: string): Promise<ConversationSessionSummary> {
  try {
    const response = await fetch(`${BASE_URL}/conversation/session/${sessionId}`)

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to get session: ${errorData.message}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error getting session:", error)
    throw error
  }
}

/**
 * Get conversation capabilities
 * 
 * @returns Promise resolving to capabilities information
 */
export async function getConversationCapabilities(): Promise<ConversationCapabilitiesResponse> {
  try {
    const response = await fetch(`${BASE_URL}/conversation/capabilities`)

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to get capabilities: ${errorData.message}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error getting capabilities:", error)
    throw error
  }
} 

// Minimal subset of fields we rely on from the /process-file-complete response
export interface ProcessFileCompleteResponse {
  success: boolean
  artifact_id: string
  cleaned_data?: unknown
  data_shape?: number[]
  [key: string]: unknown // allow additional backend fields without strict typing
}

/**
 * Upload a CSV (as text) to the dataclean service using the "process-file-complete"
 * endpoint. This performs end-to-end processing (upload + quality analysis) in one call.
 *
 * The backend returns a rich response; we only require the generated `artifact_id`.
 */
export async function uploadCsvFile(csvText: string, experimentId: string = "demo-experiment"): Promise<ProcessFileCompleteResponse> {
  const formData = new FormData()
  const blob = new Blob([csvText], { type: 'text/csv' })
  const file = new File([blob], 'dataset.csv', { type: 'text/csv' })

  formData.append('file', file)
  // Back-end endpoint parameters – providing experiment_id; the rest use defaults
  formData.append('experiment_id', experimentId)

  // ---- DEBUG: Log request body ----
  try {
    console.group("📤 process-file-complete Request Body")
    for (const [key, value] of formData.entries()) {
      if (value instanceof File) {
        console.log(`${key}: File(name=${value.name}, size=${value.size} bytes, type=${value.type})`)
      } else {
        console.log(`${key}:`, value)
      }
    }
    console.groupEnd()
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  catch (_err) {
    /* silently ignore logging errors (e.g., non-browser env) */
  }

  const response = await fetch(`${BASE_URL}/process-file-complete`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ message: response.statusText }))
    throw new Error(err.message || 'Upload failed')
  }

  return await response.json()
} 