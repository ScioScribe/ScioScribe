/**
 * Analysis Message Handler
 * 
 * This module handles message processing for the analysis mode.
 * It generates visualizations and handles analysis requests using the analysis API.
 */

import { generateVisualization, connectAnalysisWebSocket, sendAnalysisRequest, type AnalysisWebSocketMessage, type NodeUpdateData } from "@/api/analysis"
import type { Message, MessageHandlerContext } from "@/types/chat-types"

// Global WebSocket connection for analysis
let analysisWebSocket: WebSocket | null = null
let currentSessionId: string | null = null

/**
 * Handles incoming messages for the analysis mode with WebSocket streaming
 * @param message User message to process
 * @param context Context containing state and handlers
 */
export async function handleAnalysisMessage(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, onVisualizationGenerated, plan, csv } = context
  
  console.log("📊 Handling analysis message:", message)
  
  try {
    // Generate session ID if not exists
    if (!currentSessionId) {
      currentSessionId = `analysis-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }
    
    // Connect WebSocket if not connected
    if (!analysisWebSocket || analysisWebSocket.readyState !== WebSocket.OPEN) {
      console.log("🔌 Establishing WebSocket connection for analysis streaming")
      
      // Add connection status message
      const connectingMessage: Message = {
        id: (Date.now()).toString(),
        content: "🔌 **Connecting to Analysis Stream**\n\nEstablishing real-time connection for visualization generation...\n\nYou'll see live updates as the analysis progresses through each processing stage.",
        sender: "ai",
        timestamp: new Date(),
        mode: "analysis",
        response_type: "text"
      }
      setMessages((prev) => [...prev, connectingMessage])
      
      analysisWebSocket = connectAnalysisWebSocket(
        currentSessionId,
        (wsMessage: AnalysisWebSocketMessage) => handleAnalysisWebSocketMessage(wsMessage, context),
        () => {
          console.log("✅ Analysis WebSocket connected")
          
          // Add connection success message
          const connectedMessage: Message = {
            id: (Date.now()).toString(),
            content: "✅ **Analysis Stream Connected**\n\nReal-time connection established. Starting analysis with live node updates...",
            sender: "ai",
            timestamp: new Date(),
            mode: "analysis",
            response_type: "text"
          }
          setMessages((prev) => [...prev, connectedMessage])
          
          // Send the analysis request now that we're connected
          if (analysisWebSocket && currentSessionId) {
            try {
              console.log("📤 Sending analysis request via WebSocket")
              sendAnalysisRequest(analysisWebSocket, currentSessionId, {
                prompt: message,
                plan: plan,
                csv: csv
              })
            } catch (error) {
              console.error("❌ Failed to send analysis request:", error)
              // Fallback to regular API
              handleAnalysisMessageFallback(message, context)
            }
          }
        },
        (error) => {
          console.error("❌ Analysis WebSocket error:", error)
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ **WebSocket Connection Error**\n\nFailed to establish real-time connection for analysis streaming.\n\nFalling back to standard API request...`,
            sender: "ai",
            timestamp: new Date(),
            mode: "analysis",
            response_type: "error"
          }
          setMessages((prev) => [...prev, errorMessage])
          
          // Fallback to regular API
          handleAnalysisMessageFallback(message, context)
        },
        (event) => {
          console.log("🔒 Analysis WebSocket closed:", event)
          analysisWebSocket = null
        }
      )
      
      // Check if connection was successful
      if (!analysisWebSocket) {
        console.error("❌ Failed to create WebSocket connection")
        await handleAnalysisMessageFallback(message, context)
        return
      }
    } else {
      // WebSocket is already connected, send the request immediately
      try {
        sendAnalysisRequest(analysisWebSocket, currentSessionId, {
          prompt: message,
          plan: plan,
          csv: csv
        })
      } catch (error) {
        console.error("❌ Failed to send request via existing WebSocket:", error)
        await handleAnalysisMessageFallback(message, context)
      }
    }
    
  } catch (error) {
    console.error("🚨 Analysis WebSocket setup error:", error)
    // Fallback to regular API
    await handleAnalysisMessageFallback(message, context)
  }
}

/**
 * Handles WebSocket messages from the analysis backend
 */
function handleAnalysisWebSocketMessage(wsMessage: AnalysisWebSocketMessage, context: MessageHandlerContext): void {
  const { setMessages, onVisualizationGenerated } = context
  
  console.log("📨 Processing analysis WebSocket message:", wsMessage)
  
  switch (wsMessage.type) {
    case 'session_status':
      const statusMessage: Message = {
        id: (Date.now()).toString(),
        content: `✅ **Analysis Session Connected**\n\nSession ID: ${wsMessage.session_id}\n\n${wsMessage.data.message}\n\nReady to process your visualization request with real-time updates.`,
        sender: "ai",
        timestamp: new Date(),
        mode: "analysis",
        response_type: "text"
      }
      setMessages((prev) => [...prev, statusMessage])
      break
      
    case 'node_update':
      const nodeData = wsMessage.data as NodeUpdateData
      console.log(`🔄 Node update received: ${nodeData.node_name} - ${nodeData.node_data.status}`)
      
      const nodeMessage: Message = {
        id: (Date.now()).toString(),
        content: `🔄 **${nodeData.node_name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}**\n\n${getNodeStatusEmoji(nodeData.node_data.status)} ${nodeData.node_data.description}`,
        sender: "ai",
        timestamp: new Date(),
        mode: "analysis",
        response_type: "text"
      }
      setMessages((prev) => [...prev, nodeMessage])
      console.log(`✅ Node update message added to chat: ${nodeData.node_name}`)
      break
      
    case 'analysis_complete':
      const result = wsMessage.data.result
      
      // Add the explanatory message first
      const textMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: result.explanation,
        sender: "ai",
        timestamp: new Date(),
        mode: "analysis",
        response_type: "text"
      }
      
      // Add the HTML visualization response
      const visualizationMessage: Message = {
        id: (Date.now() + 2).toString(),
        content: result.html_content,
        sender: "ai",
        timestamp: new Date(),
        isHtml: true,
        mode: "analysis",
        response_type: "html"
      }
      
      setMessages((prev) => [...prev, textMessage, visualizationMessage])
      
      // Notify parent component about the visualization
      if (onVisualizationGenerated) {
        onVisualizationGenerated(result.html_content)
      }
      break
      
    case 'error':
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ **Analysis Error**\n\n${wsMessage.data.message}\n\nPlease try again or check your input data.`,
        sender: "ai",
        timestamp: new Date(),
        mode: "analysis",
        response_type: "error"
      }
      setMessages((prev) => [...prev, errorMessage])
      break
      
    default:
      console.log("📨 Unknown analysis WebSocket message type:", wsMessage.type)
  }
}

/**
 * Fallback to regular API when WebSocket fails
 */
async function handleAnalysisMessageFallback(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, onVisualizationGenerated, plan, csv } = context
  
  try {
    const requestBody = {
      prompt: message,
      plan: plan,
      csv: csv,
    }
    
    console.log("📤 FALLBACK GENERATE VISUALIZATION REQUEST:", requestBody)
    
    const response = await generateVisualization(requestBody)
    console.log("📥 FALLBACK GENERATE VISUALIZATION RESPONSE:", JSON.stringify(response, null, 2))

    // Add the explanatory message first
    const textMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: response.message,
      sender: "ai",
      timestamp: new Date(),
      mode: "analysis",
      response_type: "text"
    }
    
    // Add the HTML visualization response
    const visualizationMessage: Message = {
      id: (Date.now() + 2).toString(),
      content: response.html,
      sender: "ai",
      timestamp: new Date(),
      isHtml: true,
      mode: "analysis",
      response_type: "html"
    }
    
    setMessages((prev) => [...prev, textMessage, visualizationMessage])
    
    // Notify parent component about the visualization
    if (onVisualizationGenerated) {
      onVisualizationGenerated(response.html)
    }
    
  } catch (error) {
    console.error("🚨 Fallback visualization generation error:", error)
    
    // Handle error
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: `❌ **Visualization Generation Error**\n\nFailed to generate visualization.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\n**Troubleshooting:**\n• Check that the backend server is running on localhost:8000\n• Verify the analysis API endpoint is accessible\n• Ensure you have valid data in the CSV field\n• Try simplifying your request\n\nPlease try again or contact support if the problem persists.`,
      sender: "ai",
      timestamp: new Date(),
      mode: "analysis",
      response_type: "error"
    }
    setMessages((prev) => [...prev, errorMessage])
  }
}

/**
 * Get emoji for node status
 */
function getNodeStatusEmoji(status: 'starting' | 'completed'): string {
  switch (status) {
    case 'starting':
      return '⏳'
    case 'completed':
      return '✅'
    default:
      return '🔄'
  }
}

/**
 * Cleanup function to close WebSocket connection
 */
export function cleanupAnalysisWebSocket(): void {
  if (analysisWebSocket) {
    analysisWebSocket.close()
    analysisWebSocket = null
    currentSessionId = null
    console.log("🧹 Analysis WebSocket connection cleaned up")
  }
} 