/**
 * Planning API functions
 * 
 * This module provides functions to interact with the planning agent
 * through the streaming session endpoints.
 */

const BASE_URL = 'http://localhost:8000/api/planning'

export interface StartPlanningSessionRequest {
  research_query: string
  experiment_id?: string
  user_id?: string
}

export interface StartPlanningSessionResponse {
  session_id: string
  experiment_id: string
  current_stage: string
  is_waiting_for_approval: boolean
  pending_approval?: any
  streaming_enabled: boolean
  checkpoint_available: boolean
}

export interface StreamChatRequest {
  user_input: string
}

export interface StreamEvent {
  event_type: "update" | "approval_request" | "error"
  data: any
  timestamp: string
}

export interface PlanningSessionStatus {
  session_id: string
  experiment_id: string
  current_stage: string
  is_waiting_for_approval: boolean
  pending_approval?: any
  streaming_enabled: boolean
  checkpoint_available: boolean
}

/**
 * Start a new planning session
 * 
 * @param request - The planning session request
 * @returns Promise resolving to session information
 */
export async function startPlanningSession(request: StartPlanningSessionRequest): Promise<StartPlanningSessionResponse> {
  try {
    const response = await fetch(`${BASE_URL}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(`Planning session start failed: ${errorData.detail || response.statusText}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error starting planning session:", error)
    throw error
  }
}

/**
 * Create EventSource for streaming chat
 * 
 * @param sessionId - The session ID
 * @returns EventSource for streaming
 */
export function createPlanningStream(sessionId: string): EventSource {
  const url = `${BASE_URL}/stream/chat/${sessionId}`
  
  // Create EventSource connection for receiving streaming updates
  const eventSource = new EventSource(url, {
    withCredentials: false
  })

  return eventSource
}

/**
 * Send message to planning stream
 * 
 * @param sessionId - The session ID
 * @param request - The chat request
 * @returns Promise resolving to response
 */
export async function sendPlanningMessage(sessionId: string, request: StreamChatRequest): Promise<Response> {
  try {
    const response = await fetch(`${BASE_URL}/stream/chat/${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(`Planning message failed: ${errorData.detail || response.statusText}`)
    }

    return response
  } catch (error) {
    console.error("❌ Error sending planning message:", error)
    throw error
  }
}

/**
 * Get planning session status
 * 
 * @param sessionId - The session ID
 * @returns Promise resolving to session status
 */
export async function getPlanningSessionStatus(sessionId: string): Promise<PlanningSessionStatus> {
  try {
    const response = await fetch(`${BASE_URL}/session/${sessionId}`)

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(`Get session status failed: ${errorData.detail || response.statusText}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error("❌ Error getting session status:", error)
    throw error
  }
}

/**
 * Delete planning session
 * 
 * @param sessionId - The session ID
 * @returns Promise resolving to deletion result
 */
export async function deletePlanningSession(sessionId: string): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}/session/${sessionId}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(`Delete session failed: ${errorData.detail || response.statusText}`)
    }
  } catch (error) {
    console.error("❌ Error deleting session:", error)
    throw error
  }
}

/**
 * Parse streaming event from Server-Sent Events
 * 
 * @param eventData - Raw event data
 * @returns Parsed stream event
 */
export function parseStreamEvent(eventData: string): StreamEvent | null {
  try {
    if (eventData.startsWith('data: ')) {
      const jsonData = eventData.slice(6) // Remove 'data: ' prefix
      return JSON.parse(jsonData)
    }
    return null
  } catch (error) {
    console.error("❌ Error parsing stream event:", error)
    return null
  }
} 