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
  const { setMessages, getPlanningSession } = context
  
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
      throw new Error("Session not initialized. Please refresh the page.")
    }
    
    // Check if WebSocket is connected
    if (!websocketManager.isConnected(planningSession.session_id)) {
      console.error("❌ WebSocket not connected for session:", planningSession.session_id)
      throw new Error("Connection lost. Please wait for reconnection.")
    }
    
    // When waiting for approval, send all messages as regular user messages
    // Let the backend's sophisticated LLM-based intent detection handle everything
    if (planningSession.is_waiting_for_approval && planningSession.pending_approval) {
      console.log("🔍 Sending message during approval state - let backend handle intent:", message)
      
      // Don't process as approval here - send as regular user message
      // The backend will determine if it's approval, edit request, or unclear
      // This bypasses frontend logic and lets backend LLM handle intent detection
    }
    
    console.log("📤 Sending user message via WebSocket to session:", planningSession.session_id)
    
    // Send user message via WebSocket
    await sendUserMessage(planningSession.session_id, message)
    
    console.log("✅ User message sent successfully via WebSocket")
    
  } catch (error) {
    console.error("❌ Planning message error:", error)
    
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: error instanceof Error ? error.message : JSON.stringify(error),
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
 * Handles planning update events from WebSocket
 * @param data Update data from the WebSocket message
 * @param context Message handler context
 */
function handlePlanningUpdate(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession, updatePlanFromPlanningState } = context
  
  console.log("📊 Planning update received from WebSocket:", data)
  
  const state = (data.state as Record<string, unknown>) || {}
  const currentStage = (state.current_stage as string) || "unknown"
  const chatHistory = (state.chat_history as Array<unknown>) || []
  
  // Update planning state for text editor (this handles the state variable)
  updatePlanFromPlanningState(state)
    .then(() => {
      console.log("📥 UPDATE PLAN FROM PLANNING STATE: Success")
    })
    .catch(error => {
      console.error("❌ Failed to update plan from planning state:", error)
    })
  
  // Extract and render ONLY the clean agent response message for chat
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
    console.log("💬 Checking if message should be added to chat:", messageContent.substring(0, 100))
    
    // Use raw message content from backend
    const cleanedContent = messageContent
    
    // Create message with raw backend content
    const updateMessage: Message = {
      id: (Date.now() + Math.random()).toString(),
      content: cleanedContent,
      sender: "ai",
      timestamp: new Date(),
      mode: "plan",
      response_type: "text"
    }
    
    console.log("➕ Adding agent message to chat")
    setMessages((prev) => {
      // Simple deduplication: avoid exact duplicates within recent messages
      // This preserves raw content while preventing backend agent re-execution spam
      const recentMessages = prev.slice(-3) // Check last 3 messages
      const isDuplicate = recentMessages.some(msg => 
        msg.sender === "ai" && 
        msg.content === cleanedContent &&
        msg.mode === "plan" &&
        (Date.now() - new Date(msg.timestamp).getTime()) < 30000 // Within 30 seconds
      )
      
      if (isDuplicate) {
        console.log("⏭️ Skipping recent duplicate message from backend")
        return prev
      }
      
      return [...prev, updateMessage]
    })
  }
  
  // Update session state with current stage (preserve session continuity)
  safeUpdateSession(setPlanningSession, {
    current_stage: currentStage,
    last_activity: new Date()
  }, "planning_update")
}


// Global pending approval messages queue
let pendingApprovalMessages: Message[] = []

/**
 * Handles approval request events from WebSocket
 * @param data Approval request data
 * @param context Message handler context
 */
function handlePlanningApprovalRequest(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession } = context
  
  console.log("⚠️ Planning approval request from WebSocket:", data)
  
  const rawMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: (data.display_message as string) || "Review completed work",
    sender: "ai",
    timestamp: new Date(),
    mode: "plan",
    response_type: "approval"
  }
  
  // Check if there's a recent AI message that might still be typing
  setMessages((prevMessages) => {
    const recentAiMessage = prevMessages
      .filter(msg => msg.sender === "ai" && msg.mode === "plan" && msg.response_type === "text")
      .pop()
    
    // If there's a recent AI message (within last 5 seconds), queue the approval
    const isRecentMessage = recentAiMessage && 
      (Date.now() - new Date(recentAiMessage.timestamp).getTime()) < 5000
    
    if (isRecentMessage) {
      console.log("⏳ Queuing approval message - recent AI message detected, likely still typing")
      
      // Store in pending queue with a flag to identify which message it follows
      pendingApprovalMessages.push({
        ...rawMessage,
        followsMessageId: recentAiMessage.id
      } as any)
      
      // Set up a fallback timeout in case typewriter callback doesn't fire
      setTimeout(() => {
        console.log("⏰ Fallback: Adding approval message after timeout")
        showPendingApprovalIfExists(setMessages, recentAiMessage.id)
      }, 3000) // 3 second fallback
      
      return prevMessages // Don't add message yet
    } else {
      console.log("➕ Adding approval message immediately - no recent AI message")
      
      // Check for duplicates even in immediate case
      const isDuplicate = prevMessages.some(msg => 
        msg.response_type === "approval" && 
        msg.content === rawMessage.content &&
        (Date.now() - new Date(msg.timestamp).getTime()) < 10000 // Within 10 seconds
      )
      
      if (isDuplicate) {
        console.log("⏭️ Skipping duplicate immediate approval message")
        return prevMessages
      }
      
      return [...prevMessages, rawMessage]
    }
  })
  
  // Update session state (preserve session continuity)
  safeUpdateSession(setPlanningSession, {
    is_waiting_for_approval: true,
    pending_approval: data,
    last_activity: new Date()
  }, "approval_request")
}

/**
 * Shows pending approval message if it exists for the given message ID
 */
function showPendingApprovalIfExists(setMessages: (updater: (prev: Message[]) => Message[]) => void, messageId: string): void {
  const pendingIndex = pendingApprovalMessages.findIndex(msg => 
    (msg as any).followsMessageId === messageId
  )
  
  if (pendingIndex !== -1) {
    const pendingMessage = pendingApprovalMessages[pendingIndex]
    
    // Remove from pending queue FIRST to prevent double-processing
    pendingApprovalMessages.splice(pendingIndex, 1)
    
    // Remove the followsMessageId property before adding to messages
    const { followsMessageId, ...cleanMessage } = pendingMessage as any
    
    console.log("➕ Adding queued approval message after typewriter completion")
    setMessages((prev) => {
      // Double-check for duplicates before adding
      const isDuplicate = prev.some(msg => 
        msg.response_type === "approval" && 
        msg.content === cleanMessage.content &&
        (Date.now() - new Date(msg.timestamp).getTime()) < 10000 // Within 10 seconds
      )
      
      if (isDuplicate) {
        console.log("⏭️ Skipping duplicate approval message")
        return prev
      }
      
      return [...prev, cleanMessage]
    })
  }
}

/**
 * Export function to be called when typewriter completes
 */
export function onTypewriterComplete(messageId: string, setMessages: (updater: (prev: Message[]) => Message[]) => void): void {
  showPendingApprovalIfExists(setMessages, messageId)
}

/**
 * Handles error events from WebSocket
 * @param data Error data
 * @param context Message handler context
 */
function handlePlanningError(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages } = context
  
  console.log("❌ Planning error from WebSocket:", data)
  
  const rawMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: data.message as string || JSON.stringify(data),
    sender: "ai",
    timestamp: new Date(),
    mode: "plan",
    response_type: "error"
  }
  
  console.log("➕ Adding raw error message to chat from WebSocket")
  setMessages((prev) => [...prev, rawMessage])
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