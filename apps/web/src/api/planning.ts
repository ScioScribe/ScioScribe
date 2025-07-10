/**
 * Planning API
 * 
 * This module handles communication with the planning backend using WebSocket
 * connections and session management utilities.
 */

import { websocketManager } from "@/utils/streaming-connection-manager"
import type { WebSocketConnectionHandlers, WebSocketMessage } from "@/types/chat-types"

/**
 * Interface for planning session creation
 */
export interface PlanningSessionCreationPayload {
  research_query: string
  experiment_id?: string
  user_id?: string
}

/**
 * Interface for planning session response
 */
export interface PlanningSessionResponse {
  session_id: string
  experiment_id: string
  current_stage: string
  is_waiting_for_approval: boolean
  pending_approval?: Record<string, unknown>
  streaming_enabled: boolean
  checkpoint_available: boolean
}

/**
 * Interface for planning session status
 */
export interface PlanningSessionStatus {
  session_id: string
  is_active: boolean
  is_waiting_for_approval: boolean
  pending_approval?: Record<string, unknown>
  current_stage?: string | null
  last_activity?: string
}

/**
 * Creates a new planning session and returns session information
 * @param payload Session creation payload
 * @returns Session information including session ID
 */
export async function createPlanningSession(payload: PlanningSessionCreationPayload): Promise<PlanningSessionResponse> {
  console.log("🚀 createPlanningSession - payload:", payload)
  
  const url = "http://localhost:8000/api/planning/start"
  console.log("🚀 createPlanningSession - url:", url)
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
    
    console.log("📥 createPlanningSession - response status:", response.status)
    
    if (!response.ok) {
      console.error("❌ createPlanningSession - HTTP error:", response.status, response.statusText)
      throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
    }
    
    const data = await response.json() as PlanningSessionResponse
    console.log("📥 createPlanningSession - response data:", data)
    
    return data
    
  } catch (error) {
    console.error("❌ createPlanningSession - Error:", error)
    throw new Error(`Failed to create planning session: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Establishes a WebSocket connection for a planning session
 * @param sessionId Session ID to connect to
 * @param handlers WebSocket event handlers
 * @returns WebSocket connection or null if failed
 */
export function connectPlanningSession(
  sessionId: string,
  handlers: WebSocketConnectionHandlers
): WebSocket | null {
  console.log("🔗 connectPlanningSession - sessionId:", sessionId)
  
  const wsUrl = `ws://localhost:8000/api/planning/ws/${sessionId}`
  console.log("🔗 connectPlanningSession - wsUrl:", wsUrl)
  
  try {
    const connection = websocketManager.createConnection(
      sessionId,
      wsUrl,
      handlers,
      {
        maxReconnectAttempts: 3,
        reconnectDelay: 2000
      }
    )
    
    if (connection) {
      console.log("✅ Planning WebSocket connection established for session:", sessionId)
    } else {
      console.error("❌ Failed to establish planning WebSocket connection for session:", sessionId)
    }
    
    return connection
    
  } catch (error) {
    console.error("❌ connectPlanningSession - Error:", error)
    return null
  }
}

/**
 * Sends a user message through the WebSocket connection
 * @param sessionId Session ID
 * @param message Message content
 * @returns Success status
 */
export function sendPlanningMessage(sessionId: string, message: string): boolean {
  console.log("📤 sendPlanningMessage - sessionId:", sessionId)
  console.log("📤 sendPlanningMessage - message:", message)
  
  const userMessage: WebSocketMessage = {
    type: "user_message",
    data: {
      content: message
    },
    session_id: sessionId
  }
  
  return websocketManager.sendMessage(sessionId, userMessage)
}

/**
 * Sends an approval response through the WebSocket connection
 * @param sessionId Session ID
 * @param approved Whether the user approved
 * @param feedback Optional feedback message
 * @returns Success status
 */
export function sendApprovalResponse(
  sessionId: string,
  approved: boolean,
  feedback?: string
): boolean {
  console.log("📤 sendApprovalResponse - sessionId:", sessionId)
  console.log("📤 sendApprovalResponse - approved:", approved)
  console.log("📤 sendApprovalResponse - feedback:", feedback)
  
  const approvalMessage: WebSocketMessage = {
    type: "approval_response",
    data: {
      approved,
      feedback: feedback || ""
    },
    session_id: sessionId
  }
  
  return websocketManager.sendMessage(sessionId, approvalMessage)
}

/**
 * Checks if a planning session has an active WebSocket connection
 * @param sessionId Session ID to check
 * @returns Connection status
 */
export function isPlanningSessionConnected(sessionId: string): boolean {
  return websocketManager.isConnected(sessionId)
}

/**
 * Gets detailed connection status for a planning session
 * @param sessionId Session ID
 * @returns Connection status details or null if not found
 */
export function getPlanningConnectionStatus(sessionId: string) {
  return websocketManager.getConnectionStatus(sessionId)
}

/**
 * Closes a planning session WebSocket connection
 * @param sessionId Session ID to close
 */
export function closePlanningSession(sessionId: string): void {
  console.log("🔒 closePlanningSession - sessionId:", sessionId)
  websocketManager.closeConnection(sessionId)
}

/**
 * Gets the WebSocket connection for a planning session
 * @param sessionId Session ID
 * @returns WebSocket connection or null if not found
 */
export function getPlanningConnection(sessionId: string): WebSocket | null {
  return websocketManager.getConnection(sessionId)
}

/**
 * Deletes a planning session on the backend
 * @param sessionId Session ID to delete
 * @returns Success status
 */
export async function deletePlanningSession(sessionId: string): Promise<boolean> {
  console.log("🗑️ deletePlanningSession - sessionId:", sessionId)
  
  const url = `http://localhost:8000/api/planning/session/${sessionId}`
  console.log("🗑️ deletePlanningSession - url:", url)
  
  try {
    const response = await fetch(url, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    })
    
    console.log("📥 deletePlanningSession - response status:", response.status)
    
    if (!response.ok) {
      console.error("❌ deletePlanningSession - HTTP error:", response.status, response.statusText)
      return false
    }
    
    const data = await response.json()
    console.log("📥 deletePlanningSession - response data:", data)
    
    return true
    
  } catch (error) {
    console.error("❌ deletePlanningSession - Error:", error)
    return false
  }
}

/**
 * Gets planning session status via REST API (fallback for when WebSocket is not available)
 * @param sessionId Session ID to check
 * @returns Session status information
 */
export async function getPlanningSessionStatus(sessionId: string): Promise<PlanningSessionStatus> {
  console.log("📊 getPlanningSessionStatus - sessionId:", sessionId)
  
  const url = `http://localhost:8000/api/planning/session/${sessionId}`
  console.log("📊 getPlanningSessionStatus - url:", url)
  
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })
    
    console.log("📥 getPlanningSessionStatus - response status:", response.status)
    
    if (!response.ok) {
      console.error("❌ getPlanningSessionStatus - HTTP error:", response.status, response.statusText)
      throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
    }
    
    const data = await response.json() as PlanningSessionStatus
    console.log("📥 getPlanningSessionStatus - response data:", data)
    
    return data
    
  } catch (error) {
    console.error("❌ getPlanningSessionStatus - Error:", error)
    throw new Error(`Failed to get planning session status: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Utility function to create WebSocket handlers for planning sessions
 * @param onMessage Message handler function
 * @param onError Error handler function
 * @param onOpen Open handler function
 * @param onClose Close handler function
 * @returns WebSocket handlers object
 */
export function createPlanningHandlers(
  onMessage: (message: WebSocketMessage) => void,
  onError: (error: Event) => void,
  onOpen: () => void,
  onClose: (event: CloseEvent) => void
): WebSocketConnectionHandlers {
  return {
    onMessage,
    onError,
    onOpen,
    onClose
  }
}

/**
 * Manually retry a failed WebSocket connection
 * @param sessionId Session ID to retry
 * @returns Success status
 */
export function retryPlanningConnection(sessionId: string): boolean {
  console.log("🔄 retryPlanningConnection - sessionId:", sessionId)
  return websocketManager.manualRetryConnection(sessionId)
}

/**
 * Get detailed connection health information
 * @param sessionId Session ID to check
 * @returns Connection health details or null if not found
 */
export function getPlanningConnectionHealth(sessionId: string) {
  return websocketManager.getConnectionStatus(sessionId)
}

/**
 * Utility function to get WebSocket URL for a planning session
 * @param sessionId Session ID
 * @returns WebSocket URL
 */
export function getPlanningWebSocketUrl(sessionId: string): string {
  return `ws://localhost:8000/api/planning/ws/${sessionId}`
} 