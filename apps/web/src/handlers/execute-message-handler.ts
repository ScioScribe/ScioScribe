/**
 * Execute Message Handler
 * 
 * This module handles message processing for the execute (data cleaning) mode.
 * It manages conversation sessions, processes responses, and handles various
 * response types from the data cleaning API.
 */

import { sendConversationMessage } from "@/api/dataclean"
import type { Message, MessageHandlerContext, DatacleanResponse } from "@/types/chat-types"
import { extractCsvFromDatacleanResponse } from "@/utils/dataclean-response"

/**
 * Handles incoming messages for the execute (data cleaning) mode
 * @param message User message to process
 * @param context Context containing state and handlers
 */
export async function handleExecuteMessage(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, getDatacleanSession } = context
  
  console.log("🧹 Handling execute message:", message)
  
  try {
    const datacleanSession = getDatacleanSession()
    // Send message to dataclean conversation endpoint
    if (datacleanSession.session_id) {
      await sendDatacleanMessage(datacleanSession.session_id, message, context)
    } else {
      throw new Error("No active dataclean session found")
    }
  } catch (error) {
    console.error("❌ Execute message error:", error)
    
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: `❌ **Data Cleaning Session Error**\n\nFailed to continue data cleaning session.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\n**Troubleshooting:**\n• Check that the backend server is running on localhost:8000\n• Verify the dataclean API endpoint is accessible\n• Try refreshing the page and starting a new session\n\nPlease try again or contact support if the problem persists.`,
      sender: "ai",
      timestamp: new Date(),
      mode: "execute",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Sends a message to the dataclean conversation API
 * @param sessionId Session ID to send message to
 * @param message Message content
 * @param context Message handler context
 */
async function sendDatacleanMessage(sessionId: string, message: string, context: MessageHandlerContext): Promise<void> {
  const { setDatacleanSession } = context
  
  try {
    console.log("📤 Sending dataclean message:", message)
    
    // Get CSV data from experiment store for the CSV conversation endpoint
    const csvData = await getCsvDataFromExperimentStore(context)
    
    const requestPayload = {
      user_message: message,
      session_id: sessionId,
      user_id: "demo-user",
      csv_data: csvData || ""  // Required field for CSV endpoint
    } as const
    console.log("📤 SEND CONVERSATION MESSAGE REQUEST:", requestPayload)
    
    // Send message to dataclean conversation endpoint
    const response = await sendConversationMessage(requestPayload)
    console.log("📥 SEND CONVERSATION MESSAGE RESPONSE:", JSON.stringify(response, null, 2))
    
    // Process the response based on type
    await processDatacleanResponse(response as DatacleanResponse, context)
    
    // Update session activity
    setDatacleanSession({
      last_activity: new Date()
    })
    
    console.log("✅ Dataclean message processed successfully")
    
  } catch (error) {
    console.error("❌ Failed to send dataclean message:", error)
    throw error
  }
}

/**
 * Gets CSV data using the same source as DataTableViewer
 * @param context Message handler context
 * @returns CSV data as string or empty string if not available
 */
async function getCsvDataFromExperimentStore(context: MessageHandlerContext): Promise<string> {
  try {
    // Use the new CSV utility function for consistent data access
    const { getCsvDataWithFallbacks } = await import('../utils/csv-utils')
    
    console.log("🔍 DEBUG: Looking for CSV data...")
    console.log("🔍 Context CSV length:", context.csv?.length || 0)
    console.log("🔍 Context CSV preview:", context.csv?.substring(0, 100) || "empty")
    
    // Get CSV data with fallbacks (context -> experiment store)
    const csvData = getCsvDataWithFallbacks(context.csv)
    
    if (csvData && csvData.trim()) {
      console.log("✅ Retrieved CSV data successfully, length:", csvData.length)
      return csvData
    }
    
    // Log detailed debug info
    console.warn("⚠️ No CSV data available from any source")
    console.warn("🔍 Available context keys:", Object.keys(context))
    console.warn("🔍 Context csv field exists:", 'csv' in context)
    console.warn("🔍 Context csv value type:", typeof context.csv)
    
    return ""
    
  } catch (error) {
    console.error("❌ Error getting CSV data:", error)
    return ""
  }
}

/**
 * Processes responses from the dataclean API
 * @param response The API response to process
 * @param context Message handler context
 */
async function processDatacleanResponse(response: DatacleanResponse, context: MessageHandlerContext): Promise<void> {
  const { setMessages, setDatacleanSession, updateCsvFromDatacleanResponse } = context
  
  console.log("🔄 PROCESSING DATACLEAN RESPONSE:", JSON.stringify(response, null, 2))
  
  try {
    // Extract CSV data using standardized utility
    const cleanedCsv = extractCsvFromDatacleanResponse(response, 'conversation-message')

    if (cleanedCsv) {
      // Use the proper dataclean response handler from the store
      try {
        await updateCsvFromDatacleanResponse(response as unknown as Record<string, unknown>)
        console.log("💾 Synced cleaned CSV to experiment store (length:", cleanedCsv.length, ")")
      } catch (csvSyncErr) {
        console.warn("⚠️ Failed to sync cleaned CSV:", csvSyncErr)
      }
    }
    
    // Create base message structure
    const baseMessage = {
      id: (Date.now() + Math.random()).toString(),
      sender: "ai" as const,
      timestamp: new Date(),
      mode: "execute" as const,
    }
    
    // Process based on response type
    switch (response.response_type) {
      case "text": {
        const textMessage: Message = {
          ...baseMessage,
          content: response.message,
          response_type: "text"
        }
        setMessages((prev) => [...prev, textMessage])
        break
      }
        
      case "data_preview": {
        const dataPreviewMessage: Message = {
          ...baseMessage,
          content: `📊 **Data Preview**\n\n${response.message}\n\n${response.data ? `**Data Sample:**\n\`\`\`\n${JSON.stringify(response.data, null, 2)}\n\`\`\`` : ""}`,
          response_type: "text"
        }
        setMessages((prev) => [...prev, dataPreviewMessage])
        
        // Note: CSV data is already processed at the top level of this function
        // No need for duplicate processing here
        break
      }
        
      case "suggestion": {
        const suggestionText = response.suggestions?.map((s, i) => 
          `${i + 1}. **${s.type}** (${Math.round(s.confidence * 100)}% confidence)\n   ${s.description}`
        ).join('\n\n') || "No specific suggestions available"
        
        const suggestionMessage: Message = {
          ...baseMessage,
          content: `💡 **Data Cleaning Suggestions**\n\n${response.message}\n\n**Recommendations:**\n${suggestionText}\n\n${response.next_steps?.length ? `**Next Steps:**\n• ${response.next_steps.join('\n• ')}` : ""}`,
          response_type: "text"
        }
        setMessages((prev) => [...prev, suggestionMessage])
        break
      }
        
      case "confirmation": {
        const confirmationMessage: Message = {
          ...baseMessage,
          content: `❓ **Confirmation Required**\n\n${response.message}\n\n**Please respond with:**\n• "yes" or "confirm" to proceed\n• "no" or "cancel" to abort\n• Provide specific instructions for modifications`,
          response_type: "confirmation"
        }
        setMessages((prev) => [...prev, confirmationMessage])
        
        // Update session state to indicate we're waiting for confirmation
        setDatacleanSession({
          is_waiting_for_approval: true
        })
        break
      }
        
      case "error": {
        const errorMessage: Message = {
          ...baseMessage,
          content: `❌ **Data Cleaning Error**\n\n${response.message}\n\nPlease try rephrasing your request or contact support if the problem persists.`,
          response_type: "error"
        }
        setMessages((prev) => [...prev, errorMessage])
        break
      }
        
      default: {
        const defaultMessage: Message = {
          ...baseMessage,
          content: `🤖 **Response**\n\n${response.message || "Processing complete"}`,
          response_type: "text"
        }
        setMessages((prev) => [...prev, defaultMessage])
      }
    }
    
  } catch (error) {
    console.error("❌ Error processing dataclean response:", error)
    
    const errorMessage: Message = {
      id: (Date.now() + Math.random()).toString(),
      content: `❌ **Response Processing Error**\n\nFailed to process the data cleaning response.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}`,
      sender: "ai",
      timestamp: new Date(),
      mode: "execute",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Creates a welcome message for a new dataclean session
 * @param sessionId Session ID for the new session
 * @param response Initial response from session creation
 * @param context Message handler context
 */
export function createDatacleanWelcomeMessage(sessionId: string, response: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages } = context
  
  // Add welcome message with capabilities
  const capabilitiesRaw = response.capabilities as unknown
  let capabilitiesText = "Data cleaning operations"
  if (Array.isArray(capabilitiesRaw)) {
    capabilitiesText = capabilitiesRaw.join('\n• ')
  } else if (capabilitiesRaw && typeof capabilitiesRaw === 'object') {
    const keys = Object.keys(capabilitiesRaw)
    capabilitiesText = keys.map(k => k.replace(/_/g, ' ')).join('\n• ')
  }
 
  const welcomeContent = [
    "🧹 **Data Cleaning Assistant Started**",
    `Session ID: ${sessionId}`,
    response.message,
    "\n**Available Capabilities:**",
    `• ${capabilitiesText}`,
    "\n**How I can help:**",
    "• Clean and preprocess your data",
    "• Handle missing values and outliers",
    "• Apply transformations and filters",
    "• Validate data quality",
    "• Generate cleaned datasets",
    "• Provide data cleaning suggestions",
    "• Guide you through the cleaning process",
    "\nWhat would you like to do with your data?"
  ].join("\n\n")

  const welcomeMessage: Message = {
    id: (Date.now() + 1).toString(),
    content: welcomeContent,
    sender: "ai",
    timestamp: new Date(),
    mode: "execute",
    response_type: "text"
  }

  setMessages((prev) => [...prev, welcomeMessage])
}