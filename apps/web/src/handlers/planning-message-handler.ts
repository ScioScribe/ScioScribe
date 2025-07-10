/**
 * Planning Message Handler
 * 
 * This module handles message processing for the planning mode using
 * WebSocket bidirectional communication instead of POST endpoints.
 */

import { websocketManager } from "@/utils/streaming-connection-manager"
import type { 
  Message, 
  MessageHandlerContext, 
  ApprovalResponse, 
  WebSocketMessage 
} from "@/types/chat-types"

/**
 * Helper function to safely update planning session state while preserving session continuity
 * @param setPlanningSession Session setter function
 * @param updates Partial session updates
 * @param context Description of the update for logging
 */
function safeUpdateSession(
  setPlanningSession: MessageHandlerContext['setPlanningSession'], 
  updates: Partial<Parameters<MessageHandlerContext['setPlanningSession']>[0]>, 
  context: string
) {
  console.log(`🔄 Safe session update - ${context}:`, updates)
  
  // Ensure we never accidentally clear critical session data
  const safeUpdates = { ...updates }
  if ('session_id' in safeUpdates && !safeUpdates.session_id) {
    console.warn("⚠️ Attempted to clear session_id - removing from updates")
    delete safeUpdates.session_id
  }
  if ('experiment_id' in safeUpdates && !safeUpdates.experiment_id) {
    console.warn("⚠️ Attempted to clear experiment_id - removing from updates")
    delete safeUpdates.experiment_id
  }
  
  setPlanningSession(safeUpdates)
}

/**
 * Handles incoming messages for the planning mode using WebSocket
 * @param message User message to process
 * @param context Context containing state and handlers
 */
export async function handlePlanningMessage(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, getPlanningSession, setPlanningSession } = context
  
  console.log("🎯 Handling planning message with WebSocket:", message)
  
  try {
    const planningSession = getPlanningSession()
    console.log("📊 Current planning session state:", {
      session_id: planningSession.session_id,
      experiment_id: planningSession.experiment_id,
      is_active: planningSession.is_active,
      is_waiting_for_approval: planningSession.is_waiting_for_approval,
      current_stage: planningSession.current_stage
    })
    
    // Ensure we have a WebSocket connection
    if (!planningSession.session_id) {
      console.error("❌ Session ID is null/undefined when trying to send message")
      throw new Error("Session ID is null - session may have been reset unexpectedly")
    }
    
    // Check if WebSocket is connected
    if (!websocketManager.isConnected(planningSession.session_id)) {
      console.error("❌ WebSocket not connected for session:", planningSession.session_id)
      throw new Error("WebSocket connection not established")
    }
    
    // Check if we're waiting for approval and parse user response
    if (planningSession.is_waiting_for_approval && planningSession.pending_approval) {
      console.log("🔍 Parsing approval response for message:", message)
      const approvalResponse = parseApprovalResponse(message)
      console.log("📋 Approval response result:", approvalResponse)
      
      if (approvalResponse.isApprovalResponse) {
        console.log("✅ Processing approval response:", approvalResponse.approved ? "APPROVED" : "REJECTED")
        
        // Add approval response indicator
        const approvalResponseMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `✅ **Approval Response Detected**\n\nAction: ${approvalResponse.approved ? "APPROVED" : "REJECTED"}\n\nStage: ${planningSession.pending_approval.stage || "Unknown"}\n\nYour response: "${message}"\n\n${approvalResponse.feedback ? `Additional feedback: ${approvalResponse.feedback}\n\n` : ""}Processing your ${approvalResponse.approved ? "approval" : "rejection"}...\n\n⏳ *Waiting for agent to continue...*`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "confirmation"
        }
        
        console.log("📝 Adding approval confirmation message")
        setMessages((prev) => [...prev, approvalResponseMessage])
        
        // Send approval response via WebSocket
        await sendApprovalResponse(planningSession.session_id, approvalResponse)
        
        // Clear approval state after sending response (preserve session continuity)
        console.log("🔄 Clearing approval state after sending WebSocket response")
        safeUpdateSession(setPlanningSession, {
          is_waiting_for_approval: false,
          pending_approval: undefined,
          last_activity: new Date()
        }, "approval_response_processed")
        
        return // Exit early for approval responses
      }
    }
    
    console.log("📤 Sending user message via WebSocket to session:", planningSession.session_id)
    
    // Send user message via WebSocket
    await sendUserMessage(planningSession.session_id, message)
    
    console.log("✅ User message sent successfully via WebSocket")
    
  } catch (error) {
    console.error("❌ Planning message error:", error)
    
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: `❌ **Planning Session Error**\n\nFailed to continue planning session.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\n**Troubleshooting:**\n• Check that the backend server is running on localhost:8000\n• Verify the WebSocket connection is established\n• Try refreshing the page and starting a new session\n\nPlease try again or contact support if the problem persists.`,
      sender: "ai",
      timestamp: new Date(),
      mode: "plan",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Sends a user message via WebSocket
 * @param sessionId Session ID to send message to
 * @param message Message content
 */
async function sendUserMessage(sessionId: string, message: string): Promise<void> {
  const userMessage: WebSocketMessage = {
    type: "user_message",
    data: {
      content: message
    },
    session_id: sessionId
  }
  
  console.log("📤 Sending user message via WebSocket:", userMessage)
  
  const sent = websocketManager.sendMessage(sessionId, userMessage)
  if (!sent) {
    throw new Error("Failed to send user message via WebSocket")
  }
}

/**
 * Sends an approval response via WebSocket
 * @param sessionId Session ID to send response to
 * @param approvalResponse Approval response data
 */
async function sendApprovalResponse(sessionId: string, approvalResponse: ApprovalResponse): Promise<void> {
  const approvalMessage: WebSocketMessage = {
    type: "approval_response",
    data: {
      approved: approvalResponse.approved,
      feedback: approvalResponse.feedback || ""
    },
    session_id: sessionId
  }
  
  console.log("📤 Sending approval response via WebSocket:", approvalMessage)
  
  const sent = websocketManager.sendMessage(sessionId, approvalMessage)
  if (!sent) {
    throw new Error("Failed to send approval response via WebSocket")
  }
}

/**
 * Handles WebSocket messages from the planning session
 * @param message WebSocket message received
 * @param context Message handler context
 */
export function handlePlanningWebSocketMessage(message: WebSocketMessage, context: MessageHandlerContext): void {
  console.log("🎯 Processing planning WebSocket message:", message)
  
  switch (message.type) {
    case "planning_update":
      console.log("📊 Processing planning update from WebSocket")
      handlePlanningUpdate(message.data, context)
      break
      
    case "approval_request":
      console.log("⚠️ Processing approval request from WebSocket")
      handlePlanningApprovalRequest(message.data, context)
      break
      
    case "error":
      console.log("❌ Processing error event from WebSocket")
      handlePlanningError(message.data, context)
      break
      
    case "session_status":
      console.log("📊 Processing session status from WebSocket")
      handleSessionStatus(message.data, context)
      break
      
    case "pong":
      console.log("🏓 Received pong from server (ignoring)")
      break
      
    default:
      console.warn("⚠️ Unknown WebSocket message type:", message.type)
  }
}

/**
 * Parses approval responses from user input
 * @param message User input message
 * @returns Parsed approval response
 */
export function parseApprovalResponse(message: string): ApprovalResponse {
  const lowerMessage = message.toLowerCase().trim()
  
  // Check for approval keywords
  const approvalKeywords = ["approve", "approved", "yes", "ok", "proceed", "continue", "accept", "go ahead"]
  const rejectionKeywords = ["reject", "rejected", "no", "stop", "cancel", "decline", "refuse", "deny"]
  
  const isApproval = approvalKeywords.some(keyword => lowerMessage.includes(keyword))
  const isRejection = rejectionKeywords.some(keyword => lowerMessage.includes(keyword))
  
  if (isApproval && !isRejection) {
    return {
      isApprovalResponse: true,
      approved: true,
      feedback: message.length > 20 ? message : undefined
    }
  } else if (isRejection && !isApproval) {
    return {
      isApprovalResponse: true,
      approved: false,
      feedback: message
    }
  } else if (lowerMessage.length > 3) {
    // If it's longer than 3 characters but not clearly approval/rejection,
    // treat as feedback with implicit approval
    return {
      isApprovalResponse: true,
      approved: true,
      feedback: message
    }
  }
  
  return {
    isApprovalResponse: false,
    approved: false
  }
}

/**
 * Handles planning update events from WebSocket
 * @param data Update data from the WebSocket message
 * @param context Message handler context
 */
function handlePlanningUpdate(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession, updatePlanFromPlanningState, updatePlanFromPlanningMessage } = context
  
  console.log("📊 Planning update received from WebSocket:", data)
  
  const state = (data.state as Record<string, unknown>) || {}
  const currentStage = (state.current_stage as string) || "unknown"
  const reasoning = (state.reasoning as string) || ""
  const chatHistory = (state.chat_history as Array<unknown>) || []
  
  // The backend stores messages using `role: "assistant"`, whereas older
  // frontend logic expected `sender: "ai"`. Support both shapes so we
  // reliably surface agent updates regardless of schema.
  const latestAiMessage = chatHistory
    .filter((msg: unknown) => {
      const m = msg as Record<string, unknown>
      return m?.sender === "ai" || m?.role === "assistant"
    })
    .pop() as Record<string, unknown> | undefined
  
  if (latestAiMessage && latestAiMessage.content) {
    const messageContent = latestAiMessage.content as string
    console.log("💬 Creating chat message from WebSocket update:", messageContent.substring(0, 100))
    
    const updateMessage: Message = {
      id: (Date.now() + Math.random()).toString(),
      content: `🤖 **Agent Response** (${currentStage})\n\n${messageContent}\n\n${reasoning ? `**Reasoning Process:**\n${reasoning}\n\n` : ""}*Data source: WebSocket real-time update*`,
      sender: "ai",
      timestamp: new Date(),
      mode: "plan",
      response_type: "text"
    }
    
    console.log("➕ Adding message to chat from WebSocket")
    setMessages((prev) => [...prev, updateMessage])
    
    // Update planning state
    updatePlanFromPlanningState(state)
      .then(() => {
        console.log("📥 UPDATE PLAN FROM PLANNING STATE: Success")
      })
      .catch(error => {
        console.error("❌ Failed to update plan from planning state:", error)
      })
    
    updatePlanFromPlanningMessage(messageContent, currentStage)
      .then(() => {
        console.log("📥 UPDATE PLAN FROM PLANNING MESSAGE: Success")
      })
      .catch(error => {
        console.error("❌ Failed to update plan from planning message:", error)
      })
  }
  
  // Update session state with current stage (preserve session continuity)
  safeUpdateSession(setPlanningSession, {
    current_stage: currentStage,
    last_activity: new Date()
  }, "planning_update")
}

/**
 * Handles approval request events from WebSocket
 * @param data Approval request data
 * @param context Message handler context
 */
function handlePlanningApprovalRequest(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession } = context
  
  console.log("⚠️ Planning approval request from WebSocket:", data)
  
  const approvalMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `⚠️ **Approval Required**\n\nStage: ${data.stage || "Unknown"}\n\nThe planning agent requires your approval to continue.\n\n**Please respond with:**\n• "approve" or "yes" to continue\n• "reject" or "no" to modify the approach\n• Provide specific feedback for adjustments\n\n*Status: ${data.status || "waiting"}*\n\n*Data source: WebSocket real-time update*`,
    sender: "ai",
    timestamp: new Date(),
    mode: "plan",
    response_type: "approval"
  }
  
  console.log("➕ Adding approval message to chat from WebSocket")
  setMessages((prev) => [...prev, approvalMessage])
  
  // Update session state (preserve session continuity)
  safeUpdateSession(setPlanningSession, {
    is_waiting_for_approval: true,
    pending_approval: data,
    last_activity: new Date()
  }, "approval_request")
}

/**
 * Handles error events from WebSocket
 * @param data Error data
 * @param context Message handler context
 */
function handlePlanningError(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages } = context
  
  console.log("❌ Planning error from WebSocket:", data)
  
  const errorMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `❌ **Planning Error**\n\n${data.message || "Unknown error occurred"}\n\n*Data source: WebSocket real-time update*`,
    sender: "ai",
    timestamp: new Date(),
    mode: "plan",
    response_type: "error"
  }
  
  console.log("➕ Adding error message to chat from WebSocket")
  setMessages((prev) => [...prev, errorMessage])
}

/**
 * Handles session status events from WebSocket
 * @param data Session status data
 * @param context Message handler context
 */
function handleSessionStatus(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setPlanningSession } = context
  
  console.log("📊 Session status update from WebSocket:", data)
  
  // Update session state based on status (only update if session is ending)
  if (!data.is_active) {
    console.log("📊 Session marked as inactive by backend - preserving session until completion")
    safeUpdateSession(setPlanningSession, {
      is_waiting_for_approval: data.is_waiting_for_approval as boolean || false,
      current_stage: data.current_stage as string || null,
      last_activity: new Date()
    }, "session_inactive")
  } else {
    // Only update non-critical fields when session is active
    safeUpdateSession(setPlanningSession, {
      is_waiting_for_approval: data.is_waiting_for_approval as boolean || false,
      current_stage: data.current_stage as string || null,
      last_activity: new Date()
    }, "session_status_update")
  }
} 