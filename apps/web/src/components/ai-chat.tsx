"use client"

/**
 * AI Chat Component
 * 
 * This is the main chat interface component that orchestrates different modes
 * (plan, execute, analysis) and manages the overall chat experience.
 * It has been refactored to use modular components and handlers.
 */

import type React from "react"
import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { useExperimentStore } from "@/stores"
import { useChatSessions } from "@/hooks/use-chat-sessions"
import { handlePlanningMessage, setupPlanningStream } from "@/handlers/planning-message-handler"
import { handleExecuteMessage, createDatacleanWelcomeMessage } from "@/handlers/execute-message-handler"
import { handleAnalysisMessage } from "@/handlers/analysis-message-handler"
import { ChatMessages } from "@/components/chat-messages"
import { ChatInput } from "@/components/chat-input"
import { ChatSuggestions } from "@/components/chat-suggestions"
import type { Message, MessageHandlerContext, AiChatProps } from "@/types/chat-types"

export function AiChat({ plan = "", csv = "", onVisualizationGenerated }: AiChatProps) {
  // Debug: Add render tracking
  console.log("🔄 AiChat render")
  
  // State management
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Welcome to ScioScribe! I can help you analyze your iris dataset and create visualizations. Try asking me to create charts or analyze the data patterns.",
      sender: "ai",
      timestamp: new Date(),
      mode: "analysis",
      response_type: "text"
    }
  ])

  const [inputValue, setInputValue] = useState("")
  const [selectedMode, setSelectedMode] = useState("analysis")
  const [isLoading, setIsLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Get experiment store actions
  const { updatePlanFromPlanningState, updatePlanFromPlanningMessage, updateCsvFromDatacleanResponse } = useExperimentStore()

  // Use the chat sessions hook
  const {
    planningSession,
    datacleanSession,
    initializePlanningSession,
    initializeDatacleanSession,
    updatePlanningSession,
    updateDatacleanSession
  } = useChatSessions()

  // Create message handler context (memoized to prevent infinite re-renders)
  const messageHandlerContext: MessageHandlerContext = useMemo(() => ({
    setMessages,
    setIsLoading,
    planningSession,
    setPlanningSession: updatePlanningSession,
    datacleanSession,
    setDatacleanSession: updateDatacleanSession,
    updatePlanFromPlanningState,
    updatePlanFromPlanningMessage,
    updateCsvFromDatacleanResponse,
    onVisualizationGenerated,
    plan,
    csv
  }), [
    setMessages,
    setIsLoading,
    planningSession,
    updatePlanningSession,
    datacleanSession,
    updateDatacleanSession,
    updatePlanFromPlanningState,
    updatePlanFromPlanningMessage,
    updateCsvFromDatacleanResponse,
    onVisualizationGenerated,
    plan,
    csv
  ])

  // Mode-specific message handlers (memoized to prevent recreation)
  const handlePlanningMessageWithSession = useCallback(async (message: string) => {
    try {
      // Initialize session if not active
      if (!planningSession.is_active || !planningSession.session_id) {
        console.log("🆕 Starting new planning session")
        const sessionResponse = await initializePlanningSession(message)
        
        // Add initial response message
        const initialMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `🎯 **Planning Session Started**\n\nSession ID: ${sessionResponse.session_id}\nExperiment ID: ${sessionResponse.experiment_id}\n\nI'm analyzing your research query: "${message}"\n\nI'll help you create a comprehensive experiment plan. The planning process will guide you through:\n\n• **Objective Definition** - Clarifying your research goals\n• **Methodology Selection** - Choosing appropriate methods\n• **Variable Identification** - Defining key variables\n• **Data Requirements** - Specifying data needs\n• **Design Validation** - Reviewing the complete plan\n\nPlease wait while I prepare the initial planning steps...`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "text"
        }
        setMessages((prev) => [...prev, initialMessage])
        
        // Set up streaming connection
        await setupPlanningStream(sessionResponse.session_id, messageHandlerContext)
      } else {
        // Continue with existing session
        await handlePlanningMessage(message, messageHandlerContext)
      }
    } catch (error) {
      console.error("❌ Planning message error:", error)
    }
  }, [planningSession.is_active, planningSession.session_id, initializePlanningSession, messageHandlerContext])

  const handleExecuteMessageWithSession = useCallback(async (message: string) => {
    try {
      // Initialize session if not active
      if (!datacleanSession.is_active) {
        const sessionResponse = await initializeDatacleanSession()
        
        // Add welcome message
        createDatacleanWelcomeMessage(sessionResponse.session_id, sessionResponse.response, messageHandlerContext)
        
        // Update session activity
        updateDatacleanSession({ last_activity: new Date() })
      } else {
        // Continue with existing session
        await handleExecuteMessage(message, messageHandlerContext)
      }
    } catch (error) {
      console.error("❌ Execute message error:", error)
    }
  }, [datacleanSession.is_active, initializeDatacleanSession, updateDatacleanSession, messageHandlerContext])

  // Mode switching handler
  const handleModeSwitch = useCallback((newMode: string) => {
    const previousMode = selectedMode
    setSelectedMode(newMode)
    
    // Add mode switch notification if switching to a different mode
    if (previousMode !== newMode) {
      const modeSwitchMessage: Message = {
        id: `mode-switch-${Date.now()}`,
        content: `🔄 Switched from ${previousMode} mode to ${newMode} mode.\n\nPrevious messages are preserved. New messages will be routed to the ${newMode} system.`,
        sender: "ai",
        timestamp: new Date(),
        mode: newMode as "plan" | "execute" | "analysis",
            response_type: "text"
          }
      
      setMessages((prev) => [...prev, modeSwitchMessage])
      console.log(`🔄 Mode switched from ${previousMode} to ${newMode}`)
    }
  }, [selectedMode, setMessages])

  // Send message handler
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date(),
      mode: selectedMode as "plan" | "execute" | "analysis",
            response_type: "text"
          }

    setMessages((prev) => [...prev, userMessage])
    const currentInput = inputValue
    setInputValue("")
    setIsLoading(true)

    try {
      // Route to appropriate handler based on selectedMode
      switch (selectedMode) {
        case "plan":
          await handlePlanningMessageWithSession(currentInput)
          break
        case "execute":
          await handleExecuteMessageWithSession(currentInput)
          break
        case "analysis":
          await handleAnalysisMessage(currentInput, messageHandlerContext)
          break
        default:
          console.error("❌ Unknown mode:", selectedMode)
          }
    } catch (error) {
      console.error("❌ Message handling error:", error)
      const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
        content: `Error processing message: ${error instanceof Error ? error.message : 'Unknown error'}`,
          sender: "ai",
          timestamp: new Date(),
        mode: selectedMode as "plan" | "execute" | "analysis",
        response_type: "error"
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }, [inputValue, selectedMode, setMessages, setInputValue, setIsLoading, handlePlanningMessageWithSession, handleExecuteMessageWithSession, messageHandlerContext])

  // Input handlers (memoized)
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }, [handleSendMessage])

  const handleSuggestionClick = useCallback((suggestion: string) => {
    setInputValue(suggestion)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }, [setInputValue, setShowSuggestions])

  // Debug function setup
  useEffect(() => {
  const logCurrentState = () => {
    console.log("🔍 === CURRENT CHAT STATE DEBUG ===")
    console.log("📊 Planning session:", planningSession)
      console.log("🧹 Dataclean session:", datacleanSession)
    console.log("📋 Total messages:", messages.length)
    console.log("📋 Last 5 messages:", messages.slice(-5).map(m => ({
      id: m.id,
      sender: m.sender,
      response_type: m.response_type,
      contentPreview: m.content.substring(0, 50) + "..."
    })))
    console.log("🔍 === END DEBUG ===")
  }

    // Expose debug function globally
    ;(window as any).logChatState = logCurrentState
    
    // Add global fetch interception for debugging (skip EventSource requests)
    const originalFetch = window.fetch
    window.fetch = async (...args) => {
      const url = args[0] as string
      const isEventSourceRequest = url.includes('/stream/chat/') && 
        (!args[1] || !(args[1] as RequestInit).method || (args[1] as RequestInit).method === 'GET')
      
      if (isEventSourceRequest) {
        console.log("🔄 SKIPPING fetch interception for EventSource request:", url)
        return originalFetch(...args)
      }
      
      console.log("🌐 FETCH REQUEST:", args[0], args[1])
              const response = await originalFetch(...args)
        
        // Clone response for logging
        const responseClone = response.clone()
        
        try {
          const responseBody = await responseClone.text()
          console.log("🌐 FETCH RESPONSE from", args[0], ":")
          console.log("📥 FETCH RESPONSE BODY:", responseBody)
          
          try {
            const jsonBody = JSON.parse(responseBody)
            console.log("📥 FETCH RESPONSE JSON:", JSON.stringify(jsonBody, null, 2))
          } catch {
            // Not JSON, already logged as text
          }
        } catch {
          console.log("🌐 FETCH RESPONSE (stream/binary):", response.status, response.statusText)
        }
      
      return response
    }
    
    // Cleanup function
    return () => {
      window.fetch = originalFetch
    }
  }, [planningSession, datacleanSession, messages])

  return (
    <Card className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800">
      {/* Chat Messages */}
      <ChatMessages
        messages={messages}
        isLoading={isLoading}
        selectedMode={selectedMode}
      />

      {/* Suggestions Panel */}
      {showSuggestions && (
        <ChatSuggestions
          selectedMode={selectedMode}
          onSuggestionClick={handleSuggestionClick}
        />
      )}

      {/* Input Area */}
      <ChatInput
        inputValue={inputValue}
        setInputValue={setInputValue}
        selectedMode={selectedMode}
        onModeChange={handleModeSwitch}
        onSendMessage={handleSendMessage}
        onToggleSuggestions={useCallback(() => setShowSuggestions(prev => !prev), [setShowSuggestions])}
            onKeyPress={handleKeyPress}
        isLoading={isLoading}
        planningSession={planningSession}
        datacleanSession={datacleanSession}
        inputRef={inputRef}
      />
    </Card>
  )
}
