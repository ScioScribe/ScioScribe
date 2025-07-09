/**
 * Analysis Message Handler
 * 
 * This module handles message processing for the analysis mode.
 * It generates visualizations and handles analysis requests using the analysis API.
 */

import { generateVisualization } from "@/api/analysis"
import type { Message, MessageHandlerContext } from "@/types/chat-types"

/**
 * Handles incoming messages for the analysis mode
 * @param message User message to process
 * @param context Context containing state and handlers
 */
export async function handleAnalysisMessage(message: string, context: MessageHandlerContext): Promise<void> {
  const { setMessages, onVisualizationGenerated, plan, csv } = context
  
  console.log("📊 Handling analysis message:", message)
  
  try {
    const requestBody = {
      prompt: message,
      plan: plan,
      csv: csv,
    }
    
    console.log("📤 GENERATE VISUALIZATION REQUEST:", requestBody)
    
    const response = await generateVisualization(requestBody)
    console.log("📥 GENERATE VISUALIZATION RESPONSE:", JSON.stringify(response, null, 2))
    console.log("📊 HTML Content Length:", response.html?.length || 0)
    console.log("💬 Message Content:", response.message)

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
    console.error("🚨 Visualization generation error:", error)
    console.log("📍 Error details:", {
      errorMessage: error instanceof Error ? error.message : 'Unknown error',
      errorType: typeof error,
      errorObject: error
    })
    
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