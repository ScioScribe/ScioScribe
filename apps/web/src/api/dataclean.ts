/**
 * Data cleaning API functions
 * 
 * This module provides functions to interact with the data cleaning service
 * through the /api/dataclean endpoint.
 */

const BASE_URL = 'http://localhost:8000/api/dataclean'

export interface DataCleanError {
  error: string
  message: string
  details?: string
}

// Conversation API interfaces and functions
export interface StartConversationRequest {
  user_id?: string
  session_id?: string
  artifact_id?: string
  file_path?: string
  csv_data?: string // optional raw CSV string to bootstrap the conversation
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
 * Start a new CSV conversation session for data cleaning
 * 
 * @param request - The conversation start request
 * @returns Promise resolving to session information
 */
export async function startConversation(request: StartConversationRequest): Promise<StartConversationResponse> {
  try {
    console.log("🧹 Starting CSV conversation with new endpoint")
    
    // Use CSV-specific endpoint instead of general conversation endpoint
    const csvRequest = {
      csv_data: request.csv_data || "", // Include CSV if provided
      user_message: "Hi", // Default greeting message
      session_id: request.session_id || `csv-session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      user_id: request.user_id || "demo-user"
    }
    
    const response = await fetch(`${BASE_URL}/csv-conversation/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(csvRequest),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to start CSV conversation: ${errorData.message}`)
    }

    const result = await response.json()
    
    // Convert CSV response to conversation response format
    const conversationResponse: StartConversationResponse = {
      session_id: result.session_id,
      user_id: csvRequest.user_id,
      status: result.success ? "active" : "error",
      message: result.response_message || "CSV conversation started",
      capabilities: ["csv_analysis", "data_cleaning", "quality_assessment"],
      session_info: {
        created_at: new Date().toISOString(),
        session_type: "csv_conversation",
        state: result.success ? "active" : "error"
      }
    }
    
    return conversationResponse
  } catch (error) {
    console.error("❌ Error starting CSV conversation:", error)
    throw error
  }
}

/**
 * Send a message in an active CSV conversation session
 * 
 * @param request - The conversation message request
 * @returns Promise resolving to conversation response
 */
export async function sendConversationMessage(request: ConversationMessageRequest): Promise<ConversationMessageResponse> {
  try {
    console.log("🧹 Sending CSV conversation message with new endpoint")
    
    // Use CSV-specific endpoint instead of general conversation endpoint
    const csvRequest = {
      csv_data: "", // Empty CSV data for text-only messages
      user_message: request.user_message,
      session_id: request.session_id,
      user_id: request.user_id || "demo-user"
    }
    
    const response = await fetch(`${BASE_URL}/csv-conversation/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(csvRequest),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to send CSV message: ${errorData.message}`)
    }

    const result = await response.json()
    
    // Convert CSV response to conversation response format
    const conversationResponse: ConversationMessageResponse = {
      session_id: result.session_id,
      response_type: result.success ? "text" : "error",
      message: result.response_message || "Message processed",
      // Always pass back both the original and cleaned CSV (if present)
      data: {
        original_csv: result.original_csv,
        cleaned_csv: result.cleaned_csv ?? null
      },
      suggestions: result.suggestions || [],
      requires_confirmation: result.requires_approval || false,
      next_steps: result.changes_made || []
    }
    
    return conversationResponse
  } catch (error) {
    console.error("❌ Error sending CSV conversation message:", error)
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
  cleaned_data?: unknown // This will be a CSV string when response_format="csv"
  data_shape?: number[]
  error_message?: string
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

/**
 * Upload any file (CSV, image, PDF) to the dataclean service using the "process-file-complete"
 * endpoint. This performs end-to-end processing including OCR for images/PDFs.
 *
 * @param file - The file to upload
 * @param experimentId - The experiment ID
 * @param responseFormat - The format to get back (csv for CSV string)
 * @returns Promise resolving to the processing response
 */
export async function uploadFile(
  file: File, 
  experimentId: string = "demo-experiment",
  responseFormat: string = "csv"
): Promise<ProcessFileCompleteResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('experiment_id', experimentId)
  formData.append('response_format', responseFormat)
  formData.append('auto_apply_suggestions', 'true')
  formData.append('confidence_threshold', '0.7')

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

/**
 * Header Generation API
 */

export interface GenerateHeadersRequest {
  plan: string
  experiment_id?: string
}

export interface GenerateHeadersResponse {
  success: boolean
  headers: string[]
  csv_data: string
  error_message?: string
}

/**
 * Generate CSV headers from experimental plan using AI
 * 
 * @param plan - The experimental plan text
 * @param experimentId - Optional experiment ID to immediately persist the CSV
 * @returns Promise resolving to the generated headers response
 * @throws Error if the request fails
 */
export async function generateHeadersFromPlan(plan: string, experimentId?: string): Promise<GenerateHeadersResponse> {
  try {
    const response = await fetch(`${BASE_URL}/generate-headers-from-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        plan,
        experiment_id: experimentId,
      }),
    })

    if (!response.ok) {
      const errorData: DataCleanError = await response.json()
      throw new Error(`Failed to generate headers: ${errorData.message}`)
    }

    const result: GenerateHeadersResponse = await response.json()
    return result
  } catch (error) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Unknown error occurred while generating headers')
  }
} 