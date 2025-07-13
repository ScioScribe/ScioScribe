/**
 * Execute Message Handler
 * 
 * This module handles message processing for the execute (data cleaning) mode.
 * It manages conversation sessions, processes responses, and handles various
 * response types from the data cleaning API using WebSocket streaming.
 */

import { toast } from 'sonner';
import { 
  connectDatacleanSession, 
  sendDatacleanWebSocketMessage,
  isDatacleanSessionConnected,
  closeDatacleanSession
} from '@/api/dataclean';
import { useExperimentStore } from '@/stores/experiment-store';
import type { Message, MessageHandlerContext, WebSocketMessage } from "@/types/chat-types"
import { extractCsvFromDatacleanResponse } from "@/utils/dataclean-response"

/**
 * Handles incoming messages for the execute (data cleaning) mode
 * @param message User message to process
 * @param context Context containing state and handlers
 */
export async function handleExecuteMessage(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, getDatacleanSession, setDatacleanSession } = context
  
  console.log("🧹 Handling execute message:", message)
  
  try {
    const datacleanSession = getDatacleanSession()
    
    // Ensure WebSocket is connected
    if (!datacleanSession.session_id || !isDatacleanSessionConnected(datacleanSession.session_id)) {
      console.log("🔄 WebSocket not connected, establishing connection...")
      
      // Create a new session if needed
      const sessionId = datacleanSession.session_id || `dataclean-${Date.now()}`
      
      // Set up WebSocket handlers
      const handlers = {
        onMessage: (wsMessage: WebSocketMessage) => {
          handleDatacleanWebSocketMessage(wsMessage, context)
        },
        onError: (error: Event) => {
          console.error("❌ Dataclean WebSocket error:", error)
          const errorMessage: Message = {
            id: Date.now().toString(),
            content: "❌ Connection error. Please try again.",
            sender: "ai",
            timestamp: new Date(),
            mode: "execute",
            response_type: "error"
          }
          setMessages((prev) => [...prev, errorMessage])
        },
        onOpen: () => {
          console.log("✅ Dataclean WebSocket connected")
          setDatacleanSession({
            session_id: sessionId,
            is_active: true,
            last_activity: new Date()
          })
        },
        onClose: (event: CloseEvent) => {
          console.log("🔌 Dataclean WebSocket closed:", event.reason)
          setDatacleanSession({
            is_active: false
          })
        }
      }
      
      // Connect WebSocket
      const connection = connectDatacleanSession(sessionId, handlers)
      if (!connection) {
        throw new Error("Failed to establish WebSocket connection")
      }
      
      // Update session
      setDatacleanSession({
        session_id: sessionId,
        websocket_connection: connection
      })
      
      // Wait a bit for connection to establish
      await new Promise(resolve => setTimeout(resolve, 500))
    }
    
    // Send message via WebSocket
    await sendDatacleanMessage(datacleanSession.session_id!, message, context)
    
  } catch (error) {
    console.error("❌ Execute message error:", error)
    
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: `❌ **Data Cleaning Session Error**\n\nFailed to process your request.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\n**Troubleshooting:**\n• Check that the backend server is running on localhost:8000\n• Verify the dataclean API endpoint is accessible\n• Try refreshing the page and starting a new session\n\nPlease try again or contact support if the problem persists.`,
      sender: "ai",
      timestamp: new Date(),
      mode: "execute",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Sends a message to the dataclean WebSocket
 * @param sessionId Session ID to send message to
 * @param message Message content
 * @param context Message handler context
 */
async function sendDatacleanMessage(sessionId: string, message: string, context: MessageHandlerContext): Promise<void> {
  const { setDatacleanSession, setMessages } = context
  
  try {
    console.log("📤 Sending dataclean message:", message)
    
    // Get CSV data and experiment ID from experiment store
    const { csvData, experimentId } = await getCsvDataFromExperimentStore(context)
    
    if (!csvData) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: "No data available to process. Please upload a CSV file first.",
        sender: "ai",
        timestamp: new Date(),
        mode: "execute",
        response_type: "error"
      }
      setMessages((prev) => [...prev, errorMessage])
      return
    }
    
    // Send message through WebSocket
    const success = sendDatacleanWebSocketMessage(sessionId, message, csvData)
    
    if (!success) {
      throw new Error("Failed to send message through WebSocket")
    }
    
    // Update session activity
    setDatacleanSession({
      last_activity: new Date()
    })
    
    console.log("✅ Dataclean message sent successfully")
    
  } catch (error) {
    console.error("❌ Failed to send dataclean message:", error)
    
    const errorMessage: Message = {
      id: Date.now().toString(),
      content: `Failed to send message: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
      sender: "ai",
      timestamp: new Date(),
      mode: "execute",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Handles WebSocket messages from dataclean service
 */
async function handleDatacleanWebSocketMessage(
  wsMessage: WebSocketMessage,
  context: MessageHandlerContext
): Promise<void> {
  const { setMessages, updateCsvFromDatacleanResponse } = context
  
  console.log("📥 Received dataclean WebSocket message:", wsMessage.type)
  
  try {
    switch (wsMessage.type) {
      case 'connection':
        // Connection established
        console.log("✅ Dataclean service connected:", wsMessage.data)
        break
        
      case 'thinking':
        // Show thinking message
        const thinkingMessage: Message = {
          id: Date.now().toString(),
          content: (wsMessage.data as any).message || "Processing...",
          sender: "ai",
          timestamp: new Date(),
          mode: "execute",
          response_type: "text"
        }
        setMessages((prev) => [...prev, thinkingMessage])
        break
        
      case 'response':
        // Process the response
        const responseData = wsMessage.data as any
        
        // Update CSV if changed
        if (responseData.csv_data && responseData.success) {
          await updateCsvFromDatacleanResponse({ csv_data: responseData.csv_data })
          toast.success(`Data ${responseData.action === 'clean' ? 'cleaned' : 'updated'} successfully!`)
        }
        
        // Format response message
        let content: string = responseData.ai_message || "Operation completed"
        
        // Analysis details are already included in the ai_message from the backend
        
        // Add sample data for describe
        if (responseData.action === 'describe' && responseData.description?.sample_data) {
          content += "\n\n**Sample Data (first 3 rows):**"
          content += "\n```json"
          content += JSON.stringify(responseData.description.sample_data.slice(0, 3), null, 2)
          content += "\n```"
        }
        
        const responseMessage: Message = {
          id: Date.now().toString(),
          content,
          sender: "ai",
          timestamp: new Date(),
          mode: "execute",
          response_type: "text"
        }
        setMessages((prev) => [...prev, responseMessage])
        break
        
      case 'error':
        // Show error message
        const errorMessage: Message = {
          id: Date.now().toString(),
          content: `❌ ${wsMessage.data.message || 'An error occurred'}`,
          sender: "ai",
          timestamp: new Date(),
          mode: "execute",
          response_type: "error"
        }
        setMessages((prev) => [...prev, errorMessage])
        break
        
      case 'pong':
        // Heartbeat response
        console.log("💓 Received pong from dataclean service")
        break
        
      default:
        console.warn("⚠️ Unknown WebSocket message type:", wsMessage.type)
    }
  } catch (error) {
    console.error("❌ Error handling dataclean WebSocket message:", error)
  }
}

/**
 * Gets CSV data using the same source as DataTableViewer
 * @param context Message handler context
 * @returns CSV data as string or empty string if not available
 */
async function getCsvDataFromExperimentStore(context: MessageHandlerContext): Promise<{ csvData: string; experimentId: string | null }> {
  try {
    // Use the new CSV utility functions for consistent data access
    const { getCsvDataWithFallbacks, getCurrentExperimentId } = await import('../utils/csv-utils')
    
    console.log("🔍 DEBUG: Looking for CSV data...")
    console.log("🔍 Context CSV length:", context.csv?.length || 0)
    console.log("🔍 Context CSV preview:", context.csv?.substring(0, 100) || "empty")
    
    // Get CSV data with fallbacks (context -> experiment store)
    const csvData = getCsvDataWithFallbacks(context.csv)
    
    // Get current experiment ID
    const experimentId = getCurrentExperimentId()
    
    if (csvData && csvData.trim()) {
      console.log("✅ Retrieved CSV data successfully, length:", csvData.length)
      console.log("✅ Retrieved experiment ID:", experimentId)
      return { csvData, experimentId }
    } else {
      // Try directly from experiment store as last resort
      const { useExperimentStore } = await import('../stores/experiment-store')
      const store = useExperimentStore.getState()
      
      if (store.csvData && store.csvData.trim()) {
        console.log("✅ Retrieved CSV data from experiment store directly")
        return { 
          csvData: store.csvData, 
          experimentId: store.currentExperiment?.id || null 
        }
      }
      
      console.warn("⚠️ No CSV data available in any source")
      return { csvData: "", experimentId: null }
    }
  } catch (error) {
    console.error("❌ Error getting CSV data:", error)
    return { csvData: "", experimentId: null }
  }
}

/**
 * Creates a welcome message for a new dataclean session
 * @param sessionId Session ID
 * @param response Initial response data
 * @param context Message handler context
 */
export function createDatacleanWelcomeMessage(sessionId: string, response: Record<string, unknown>, context: MessageHandlerContext): void {
  const { setMessages } = context
  
  const welcomeMessage: Message = {
    id: (Date.now() + Math.random()).toString(),
    content: `🧹 **Data Cleaning Session Started**\n\nSession ID: \`${sessionId}\`\n\nI'm ready to help you clean and analyze your data. You can:\n• **Analyze** data quality issues\n• **Clean** your data automatically\n• **Describe** your dataset\n• **Add** new rows\n• **Delete** specific rows\n\nJust tell me what you'd like to do!`,
    sender: "ai",
    timestamp: new Date(),
    mode: "execute",
    response_type: "text"
  }
  
  setMessages((prev) => [...prev, welcomeMessage])
}