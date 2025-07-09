/**
 * Planning Message Handler
 * 
 * This module handles message processing for the planning mode, including
 * streaming connection management, approval handling, and event processing.
 */

import { sendPlanningMessage, parseStreamEvent } from "@/api/planning"
import { streamingManager } from "@/utils/streaming-connection-manager"
import type { Message, MessageHandlerContext, ApprovalResponse, PlanningStreamEvent } from "@/types/chat-types"

/**
 * Handles incoming messages for the planning mode
 * @param message User message to process
 * @param context Context containing state and handlers
 */
export async function handlePlanningMessage(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, planningSession, setPlanningSession } = context
  
  console.log("🎯 Handling planning message:", message)
  console.log("📊 Current planning session state:", planningSession)
  
  try {
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
        
        // Clear pending approval state but keep session active
        console.log("🔄 Clearing approval state but keeping session active")
        setPlanningSession({
          is_active: true,
          is_waiting_for_approval: false,
          pending_approval: null
        })
      }
    }
    
    console.log("📤 Sending planning stream message to session:", planningSession.session_id)
    
    // Double-check session is still valid before sending message
    if (!planningSession.session_id) {
      console.error("❌ Session ID is null/undefined when trying to send message")
      throw new Error("Session ID is null - session may have been reset unexpectedly")
    }
    
    await sendPlanningStreamMessage(planningSession.session_id, message, context)
    
  } catch (error) {
    console.error("❌ Planning message error:", error)
    
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: `❌ **Planning Session Error**\n\nFailed to continue planning session.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\n**Troubleshooting:**\n• Check that the backend server is running on localhost:8000\n• Verify the planning API endpoint is accessible\n• Try refreshing the page and starting a new session\n\nPlease try again or contact support if the problem persists.`,
      sender: "ai",
      timestamp: new Date(),
      mode: "plan",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Sets up streaming connection for planning session
 * @param sessionId Session ID to connect to
 * @param context Message handler context
 */
export async function setupPlanningStream(sessionId: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, setPlanningSession } = context
  
  try {
    console.log("🔄 Setting up planning stream for session:", sessionId)
    
    const url = `http://localhost:8000/api/planning/stream/chat/${sessionId}`
    
    const eventSource = streamingManager.createConnection(
      sessionId,
      url,
      {
        onMessage: (event) => {
          console.log("📥 RAW STREAM EVENT RECEIVED:", event.data)
          console.log("📥 Event timestamp:", new Date().toISOString())
          
          try {
            const streamEvent = parseStreamEvent(event.data)
            console.log("🔍 PARSED STREAM EVENT:", JSON.stringify(streamEvent, null, 2))
            
            if (streamEvent) {
              console.log("✅ Processing stream event of type:", streamEvent.event_type)
              handlePlanningStreamEvent(streamEvent, context)
            } else {
              console.warn("⚠️ Failed to parse stream event, trying manual JSON parse")
              
              try {
                const manualParsed = JSON.parse(event.data)
                console.log("🔧 MANUAL JSON PARSE RESULT:", JSON.stringify(manualParsed, null, 2))
                
                if (manualParsed.event_type || manualParsed.data) {
                  console.log("✅ Manual parse successful, processing event")
                  handlePlanningStreamEvent(manualParsed, context)
                }
              } catch (manualError) {
                console.error("❌ Manual JSON parse also failed:", manualError)
              }
            }
          } catch (error) {
            console.error("❌ Error parsing stream event:", error)
          }
        },
        onError: (error) => {
          console.error("❌ Planning stream error:", error)
          
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `🔌 **Stream Connection Error**\n\nLost connection to planning stream.\n\nAttempting to reconnect...\n\nIf the problem persists, please refresh the page.`,
            sender: "ai",
            timestamp: new Date(),
            mode: "plan",
            response_type: "error"
          }
          setMessages((prev) => [...prev, errorMessage])
        },
        onOpen: () => {
          console.log("✅ Planning stream connection established")
          
          // Update session with connection info
          setPlanningSession({
            stream_connection: eventSource
          })
        }
      },
      {
        maxReconnectAttempts: 5,
        reconnectDelay: 3000
      }
    )
    
    if (!eventSource) {
      throw new Error("Failed to create planning stream connection")
    }
    
  } catch (error) {
    console.error("❌ Failed to setup planning stream:", error)
    throw error
  }
}

/**
 * Sends a message to the planning stream
 * @param sessionId Session ID to send message to
 * @param message Message content
 * @param context Message handler context
 */
export async function sendPlanningStreamMessage(sessionId: string, message: string, context: MessageHandlerContext): Promise<void> {
  const { setPlanningSession } = context
  
  try {
    console.log("📤 Sending planning stream message:", message)
    
    const requestPayload = { user_input: message }
    console.log("📤 SEND PLANNING MESSAGE REQUEST:", requestPayload)
    
    const response = await sendPlanningMessage(sessionId, requestPayload)
    console.log("📥 SEND PLANNING MESSAGE RESPONSE:", JSON.stringify(response, null, 2))
    
    // Update session activity
    setPlanningSession({
      last_activity: new Date()
    })
    
    console.log("✅ Planning stream message sent successfully")
    
  } catch (error) {
    console.error("❌ Failed to send planning stream message:", error)
    throw error
  }
}

/**
 * Handles planning stream events
 * @param streamEvent The stream event to process
 * @param context Message handler context
 */
export function handlePlanningStreamEvent(streamEvent: PlanningStreamEvent, context: MessageHandlerContext): void {
  console.log("🎯 Processing planning stream event:", streamEvent)
  
  try {
    switch (streamEvent.event_type) {
      case "update":
        console.log("🔄 Handling planning update event")
        handlePlanningUpdate(streamEvent.data, context)
        break
      case "approval_request":
        console.log("⚠️ Handling approval request event")
        handlePlanningApprovalRequest(streamEvent.data, context)
        break
      case "error":
        console.log("❌ Handling error event")
        handlePlanningStreamError(streamEvent.data, context)
        break
      case "heartbeat":
        console.log("💓 Received heartbeat event")
        break
      default:
        console.warn("⚠️ Unknown planning stream event type:", streamEvent.event_type)
        
        // Try to handle unknown events as updates if they have state data
        if (streamEvent.data && streamEvent.data.state) {
          console.log("🔄 Treating unknown event as update since it has state data")
          handlePlanningUpdate(streamEvent.data, context)
        }
    }
  } catch (error) {
    console.error("❌ Error handling planning stream event:", error)
  }
}

/**
 * Handles planning update events
 * @param data Update data from the stream
 * @param context Message handler context
 */
function handlePlanningUpdate(data: any, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession, updatePlanFromPlanningState, updatePlanFromPlanningMessage } = context
  
  console.log("📊 Planning update received:", data)
  
  const state = data.state || {}
  const currentStage = state.current_stage || "unknown"
  const reasoning = state.reasoning || ""
  const chatHistory = state.chat_history || []
  
  const latestAiMessage = chatHistory
    .filter((msg: any) => msg.sender === "ai")
    .pop()
  
  if (latestAiMessage) {
    const updateMessage: Message = {
      id: (Date.now() + Math.random()).toString(),
      content: `🤖 **Agent Reasoning** (${currentStage})\n\n${latestAiMessage.content}\n\n${reasoning ? `**Reasoning Process:**\n${reasoning}\n\n` : ""}*This is a real-time update from the planning agent.*`,
      sender: "ai",
      timestamp: new Date(),
      mode: "plan",
      response_type: "text"
    }
    
    setMessages((prev) => [...prev, updateMessage])
    
    // Update planning state
    updatePlanFromPlanningState(state)
      .then(result => {
        console.log("📥 UPDATE PLAN FROM PLANNING STATE RESPONSE:", JSON.stringify(result, null, 2))
      })
      .catch(error => {
        console.error("❌ Failed to update plan from planning state:", error)
      })
    
    updatePlanFromPlanningMessage(latestAiMessage.content, currentStage)
      .then(result => {
        console.log("📥 UPDATE PLAN FROM PLANNING MESSAGE RESPONSE:", JSON.stringify(result, null, 2))
      })
      .catch(error => {
        console.error("❌ Failed to update plan from planning message:", error)
      })
  }
  
  // Update session state
  setPlanningSession({
    is_active: true,
    is_waiting_for_approval: state.is_waiting_for_approval || false,
    pending_approval: state.pending_approval || null,
    last_activity: new Date()
  })
}

/**
 * Handles approval request events
 * @param data Approval request data
 * @param context Message handler context
 */
function handlePlanningApprovalRequest(data: any, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession } = context
  
  console.log("⚠️ Planning approval request:", data)
  
  const approvalMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `⚠️ **Approval Required**\n\nStage: ${data.stage || "Unknown"}\n\nThe planning agent requires your approval to continue.\n\n**Please respond with:**\n• "approve" or "yes" to continue\n• "reject" or "no" to modify the approach\n• Provide specific feedback for adjustments\n\n*Status: ${data.status || "waiting"}*`,
    sender: "ai",
    timestamp: new Date(),
    mode: "plan",
    response_type: "approval"
  }
  
  setMessages((prev) => [...prev, approvalMessage])
  
  // Update session state
  setPlanningSession({
    is_active: true,
    is_waiting_for_approval: true,
    pending_approval: data,
    last_activity: new Date()
  })
}

/**
 * Handles planning stream error events
 * @param data Error data from the stream
 * @param context Message handler context
 */
function handlePlanningStreamError(data: any, context: MessageHandlerContext): void {
  const { setMessages } = context
  
  console.error("❌ Planning stream error data:", data)
  
  const errorMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `❌ **Planning Stream Error**\n\nError: ${data.error || "Unknown error"}\n\n${data.details ? `Details: ${data.details}\n\n` : ""}The planning process encountered an issue. Please try again or contact support if the problem persists.`,
    sender: "ai",
    timestamp: new Date(),
    mode: "plan",
    response_type: "error"
  }
  
  setMessages((prev) => [...prev, errorMessage])
}

/**
 * Parses user approval responses
 * @param message User message to parse
 * @returns Approval response object
 */
function parseApprovalResponse(message: string): ApprovalResponse {
  const lowerMessage = message.toLowerCase().trim()
  
  const approvalKeywords = [
    "approve", "approved", "yes", "y", "ok", "okay", "proceed", "continue", 
    "go ahead", "looks good", "good", "accept", "accepted", "confirm", "confirmed"
  ]
  
  const rejectionKeywords = [
    "reject", "rejected", "no", "n", "not", "stop", "wait", "pause", "cancel",
    "don't", "dont", "disagree", "wrong", "incorrect", "change", "modify"
  ]
  
  const hasApprovalKeyword = approvalKeywords.some(keyword => 
    lowerMessage.includes(keyword) || lowerMessage === keyword
  )
  
  const hasRejectionKeyword = rejectionKeywords.some(keyword => 
    lowerMessage.includes(keyword) || lowerMessage === keyword
  )
  
  const isApprovalResponse = hasApprovalKeyword || hasRejectionKeyword
  
  let approved = false
  if (hasApprovalKeyword && !hasRejectionKeyword) {
    approved = true
  } else if (hasRejectionKeyword && !hasApprovalKeyword) {
    approved = false
  } else if (hasApprovalKeyword && hasRejectionKeyword) {
    approved = false // Default to rejection for safety
  }
  
  const feedback = (lowerMessage.length > 10 && 
    !approvalKeywords.includes(lowerMessage) && 
    !rejectionKeywords.includes(lowerMessage)) ? message : undefined
  
  return {
    isApprovalResponse,
    approved,
    feedback
  }
} 