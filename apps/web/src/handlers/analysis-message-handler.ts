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
  const { setMessages, plan, csv } = context
  
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
        id: "analysis-connection-status",
        content: "🔌 **Connecting to Analysis Stream**\n\nEstablishing real-time connection for visualization generation...\n\nYou'll see live updates as the analysis progresses through each processing stage.",
        sender: "ai",
        timestamp: new Date(),
        mode: "analysis",
        response_type: "text",
        tool_id: "connection-status",
        tool_status: "running"
      }
      setMessages((prev) => [...prev, connectingMessage])
      
      analysisWebSocket = connectAnalysisWebSocket(
        currentSessionId,
        (wsMessage: AnalysisWebSocketMessage) => handleAnalysisWebSocketMessage(wsMessage, context),
        () => {
          console.log("✅ Analysis WebSocket connected")
          
          // Update connection status message
          setMessages((prev) => prev.map(msg => 
            msg.tool_id === "connection-status" 
              ? {
                  ...msg,
                  content: "✅ **Analysis Stream Connected**\n\nReal-time connection established. Starting analysis with live node updates...",
                  tool_status: "completed" as const,
                  timestamp: new Date()
                }
              : msg
          ))
          
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
          
          // Update connection status message to show error
          setMessages((prev) => prev.map(msg => 
            msg.tool_id === "connection-status" 
              ? {
                  ...msg,
                  content: `❌ **WebSocket Connection Error**\n\nFailed to establish real-time connection for analysis streaming.\n\nFalling back to standard API request...`,
                  tool_status: "error" as const,
                  timestamp: new Date()
                }
              : msg
          ))
          
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
  const { setMessages } = context
  
  console.log("📊 Analysis WebSocket message received:", wsMessage)
  
  try {
    switch (wsMessage.type) {
      case 'session_status':
        console.log("📊 Session status update:", wsMessage.data)
        break
        
      case "node_update": {
        const updateData = wsMessage.data as unknown as NodeUpdateData
        const toolId = `tool-${updateData.node_name}`
        const status = updateData.node_data.status.toLowerCase().includes('complete') ? 'completed' : 'running'
        
        // Check if this tool message already exists
        setMessages((prev) => {
          const existingMessageIndex = prev.findIndex(msg => msg.tool_id === toolId)
          
          if (existingMessageIndex !== -1) {
            // Update existing message
            const updatedMessages = [...prev]
            updatedMessages[existingMessageIndex] = {
              ...updatedMessages[existingMessageIndex],
              content: `🔄 **${updateData.node_name}**\n\n${updateData.node_data.description}\n\nStatus: ${updateData.node_data.status}`,
              tool_status: status,
              timestamp: new Date()
            }
            return updatedMessages
          } else {
            // Create new message
            const nodeStatusMessage: Message = {
              id: (Date.now() + Math.random()).toString(),
              content: `🔄 **${updateData.node_name}**\n\n${updateData.node_data.description}\n\nStatus: ${updateData.node_data.status}`,
              sender: "ai",
              timestamp: new Date(),
              mode: "analysis",
              response_type: "text",
              tool_id: toolId,
              tool_status: status
            }
            return [...prev, nodeStatusMessage]
          }
        })
        break
      }
      
      case 'analysis_complete': {
        const analysisData = wsMessage.data as unknown as { html?: string; message?: string }
        const html = analysisData.html
        const message = analysisData.message || "Analysis complete"
        
        if (html) {
          const htmlMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: html,
            sender: "ai",
            timestamp: new Date(),
            mode: "analysis",
            response_type: "html",
            isHtml: true
          }
          setMessages((prev) => [...prev, htmlMessage])
          
          // Call the visualization callback if provided
          if (context.onVisualizationGenerated) {
            context.onVisualizationGenerated(html)
          }
        } else {
          const textMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `📊 **Analysis Complete**\n\n${message}`,
            sender: "ai",
            timestamp: new Date(),
            mode: "analysis",
            response_type: "text"
          }
          setMessages((prev) => [...prev, textMessage])
        }
        break
      }
      
      case 'error': {
        const errorData = wsMessage.data as unknown as { message?: string }
        const errorMessage: Message = {
          id: (Date.now() + 2).toString(),
          content: `❌ **Analysis Error**\n\n${errorData.message || "An error occurred during analysis"}`,
          sender: "ai",
          timestamp: new Date(),
          mode: "analysis",
          response_type: "error"
        }
        setMessages((prev) => [...prev, errorMessage])
        break
      }
      
      default:
        console.log("📨 Unknown analysis WebSocket message type:", wsMessage.type)
    }
  } catch (error) {
    console.error("🚨 Error processing WebSocket message:", error)
  }
}

/**
 * Fallback HTTP handler for analysis messages when WebSocket fails
 * @param message User message to process
 * @param context Message handler context
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