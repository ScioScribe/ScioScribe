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
      throw new Error("Session not initialized. Please refresh the page.")
    }
    
    // Check if WebSocket is connected
    if (!websocketManager.isConnected(planningSession.session_id)) {
      console.error("❌ WebSocket not connected for session:", planningSession.session_id)
      throw new Error("Connection lost. Please wait for reconnection.")
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
          content: approvalResponse.approved ? "✅ Moving forward..." : "❌ Let's revise this section.",
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
      content: `❌ ${error instanceof Error ? error.message : 'Something went wrong. Please try again.'}`,
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
  
  // Strong approval keywords - these clearly indicate approval
  const strongApprovalKeywords = ["approve", "approved", "yes", "proceed", "continue", "accept", "go ahead", "looks good", "perfect", "ready"]
  
  // Strong rejection keywords - these clearly indicate rejection
  const strongRejectionKeywords = ["reject", "rejected", "no", "stop", "cancel", "decline", "refuse", "deny"]
  
  // Edit/change keywords - these indicate user wants to make changes
  const editKeywords = ["instead", "change", "modify", "update", "revise", "make it", "could we", "can we", "rather than", "but", "however", "actually"]
  
  // Check for strong approval indicators
  const hasStrongApproval = strongApprovalKeywords.some(keyword => lowerMessage.includes(keyword))
  const hasStrongRejection = strongRejectionKeywords.some(keyword => lowerMessage.includes(keyword))
  const hasEditIntent = editKeywords.some(keyword => lowerMessage.includes(keyword))
  
  // Clear approval (no conflicting signals)
  if (hasStrongApproval && !hasStrongRejection && !hasEditIntent) {
    return {
      isApprovalResponse: true,
      approved: true,
      feedback: message.length > 20 ? message : undefined
    }
  }
  
  // Clear rejection (no conflicting signals)
  if (hasStrongRejection && !hasStrongApproval && !hasEditIntent) {
    return {
      isApprovalResponse: true,
      approved: false,
      feedback: message
    }
  }
  
  // Edit intent detected - this is NOT an approval response
  if (hasEditIntent) {
    return {
      isApprovalResponse: false,
      approved: false
    }
  }
  
  // Short responses that might be approvals
  if (lowerMessage.length <= 10) {
    const shortApprovals = ["ok", "okay", "sure", "fine", "good", "great", "yep", "yeah"]
    const shortRejections = ["no", "nope", "nah", "stop"]
    
    if (shortApprovals.some(word => lowerMessage === word)) {
      return {
        isApprovalResponse: true,
        approved: true,
        feedback: undefined
      }
    }
    
    if (shortRejections.some(word => lowerMessage === word)) {
      return {
        isApprovalResponse: true,
        approved: false,
        feedback: message
      }
    }
  }
  
  // 🚨 REMOVED THE BROKEN FALLBACK LOGIC 🚨
  // Previously: any message > 3 chars was treated as implicit approval
  // Now: when in doubt, don't assume it's an approval response
  
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
    
    // Extract only the most relevant part of the message for better readability
    const cleanedContent = extractRelevantContent(messageContent, currentStage)
    
    // Check if this message has already been displayed to prevent duplicates
    setMessages((prev) => {
      // Check if a message with similar content already exists in recent messages
      const recentMessages = prev.slice(-5) // Check last 5 messages
      const isDuplicate = recentMessages.some(msg => 
        msg.sender === "ai" && 
        msg.content === cleanedContent &&
        msg.mode === "plan"
      )
      
      if (isDuplicate) {
        console.log("⏭️ Skipping duplicate message - already displayed")
        return prev
      }
      
      // Create clean chat message with ONLY the relevant agent response
      const updateMessage: Message = {
        id: (Date.now() + Math.random()).toString(),
        content: cleanedContent,
        sender: "ai",
        timestamp: new Date(),
        mode: "plan",
        response_type: "text"
      }
      
      console.log("➕ Adding clean agent message to chat")
      return [...prev, updateMessage]
    })
  }
  
  // Update session state with current stage (preserve session continuity)
  safeUpdateSession(setPlanningSession, {
    current_stage: currentStage,
    last_activity: new Date()
  }, "planning_update")
}

/**
 * Extracts the most relevant content from agent messages for better readability
 * @param content Original message content
 * @param stage Current planning stage
 * @returns Cleaned and condensed message content
 */
function extractRelevantContent(content: string, stage: string): string {
  // Remove excessive formatting and focus on key information
  const cleaned = content
    .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove bold formatting
    .replace(/\n{3,}/g, '\n\n') // Reduce multiple newlines
    .trim()
  
  // Stage-specific content extraction
  switch (stage) {
    case 'objective_setting':
      return extractObjectiveContent(cleaned)
    case 'variable_identification':
      return extractVariableContent(cleaned)
    case 'experimental_design':
      return extractDesignContent(cleaned)
    case 'methodology_protocol':
      return extractMethodologyContent(cleaned)
    case 'data_planning':
      return extractDataPlanningContent(cleaned)
    case 'final_review':
      return extractFinalReviewContent(cleaned)
    default:
      return getStageUpdateSummary(stage, cleaned.substring(0, 150))
  }
}

/**
 * Stage-specific content extraction functions
 */
function extractObjectiveContent(content: string): string {
  const lines = content.split('\n').filter(line => line.trim())
  const objective = lines.find(line => line.toLowerCase().includes('objective:') || line.toLowerCase().includes('research question:'))
  const hypothesis = lines.find(line => line.toLowerCase().includes('hypothesis:'))
  
  const parts = []
  if (objective) parts.push(objective.trim())
  if (hypothesis) parts.push(hypothesis.trim())
  
  return parts.length > 0 ? parts.join('\n') : '🎯 Setting research objectives...'
}

function extractVariableContent(content: string): string {
  const lines = content.split('\n').filter(line => line.trim())
  const variables = lines.filter(line => 
    line.includes('Independent:') || 
    line.includes('Dependent:') || 
    line.includes('Control:') ||
    line.includes('variable')
  ).slice(0, 3)
  
  return variables.length > 0 ? variables.join('\n') : '🔍 Identifying experimental variables...'
}

function extractDesignContent(content: string): string {
  const lines = content.split('\n').filter(line => line.trim())
  const design = lines.filter(line => 
    line.includes('group') || 
    line.includes('sample size') || 
    line.includes('replicate') ||
    line.includes('control')
  ).slice(0, 3)
  
  return design.length > 0 ? design.join('\n') : '⚗️ Designing experimental groups...'
}

function extractMethodologyContent(content: string): string {
  const lines = content.split('\n').filter(line => line.trim())
  const methodology = lines.filter(line => 
    line.includes('Step') || 
    line.includes('protocol') || 
    line.includes('procedure') ||
    line.includes('equipment')
  ).slice(0, 3)
  
  return methodology.length > 0 ? methodology.join('\n') : '📋 Developing methodology...'
}

function extractDataPlanningContent(content: string): string {
  const lines = content.split('\n').filter(line => line.trim())
  const dataPlan = lines.filter(line => 
    line.includes('data collection') || 
    line.includes('analysis') || 
    line.includes('statistical') ||
    line.includes('visualization')
  ).slice(0, 3)
  
  return dataPlan.length > 0 ? dataPlan.join('\n') : '📊 Planning data collection and analysis...'
}

function extractFinalReviewContent(content: string): string {
  const lines = content.split('\n').filter(line => line.trim())
  const review = lines.filter(line => 
    line.includes('complete') || 
    line.includes('review') || 
    line.includes('ready') ||
    line.includes('final')
  ).slice(0, 2)
  
  return review.length > 0 ? review.join('\n') : '✅ Finalizing experiment plan...'
}

/**
 * Generates a concise stage-based summary for planning updates
 * @param stage Current planning stage
 * @param originalContent Original message snippet
 * @returns Concise stage summary
 */
function getStageUpdateSummary(stage: string, originalContent: string): string {
  const stageNames: Record<string, string> = {
    'objective_setting': '🎯 Defining research objectives',
    'variable_identification': '🔍 Identifying variables',
    'experimental_design': '⚗️ Designing experiment structure',
    'methodology_protocol': '📋 Creating methodology',
    'data_planning': '📊 Planning data collection',
    'final_review': '✅ Final review'
  }
  
  const stageName = stageNames[stage] || `📝 ${stage.replace('_', ' ')}`
  
  // Extract first meaningful sentence
  const firstSentence = originalContent.split('.')[0]?.trim()
  
  if (firstSentence && firstSentence.length > 10) {
    return `${stageName}: ${firstSentence}.`
  }
  
  return stageName
}

/**
 * Handles approval request events from WebSocket
 * @param data Approval request data
 * @param context Message handler context
 */
function handlePlanningApprovalRequest(data: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages, setPlanningSession } = context
  
  console.log("⚠️ Planning approval request from WebSocket:", data)
  
  const stageNames: Record<string, string> = {
    'objective_setting': 'Research Objectives',
    'variable_identification': 'Variables',
    'experimental_design': 'Experimental Design',
    'methodology_protocol': 'Methodology',
    'data_planning': 'Data Collection Plan',
    'final_review': 'Final Plan'
  }
  
  const stage = data.stage as string || "Unknown"
  const stageName = stageNames[stage] || stage.replace('_', ' ')
  
  const approvalMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `Ready to proceed with ${stageName}?\n\nType "approve" to continue or provide feedback.`,
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
  
  const errorMsg = data.message as string || "Unknown error occurred"
  // Simplify technical error messages
  const simplifiedError = errorMsg
    .replace(/WebSocket/gi, 'connection')
    .replace(/session_id/gi, 'session')
    .replace(/null|undefined/gi, 'missing')
    .replace(/connection not established/gi, 'Unable to connect')
    .replace(/failed to/gi, 'Could not')
  
  const errorMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `⚠️ ${simplifiedError}`,
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