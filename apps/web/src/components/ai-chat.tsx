"use client"

/**
 * AI Chat Component
 * 
 * This is the main chat interface component that orchestrates different modes
 * (plan, execute, analysis) and manages the overall chat experience.
 * It uses WebSocket connections for real-time bidirectional communication.
 */

import type React from "react"
import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { Card } from "@/components/ui/card"
import { useExperimentStore } from "@/stores"
import { useChatSessions } from "@/hooks/use-chat-sessions"
import { handlePlanningWebSocketMessage, onTypewriterComplete } from "@/handlers/planning-message-handler"
import { handlePlanningMessage } from "@/handlers/planning-message-handler"
import { handleExecuteMessage, createDatacleanWelcomeMessage } from "@/handlers/execute-message-handler"
import { handleAnalysisMessage } from "@/handlers/analysis-message-handler"
import { 
  createPlanningSession, 
  connectPlanningSession, 
  sendPlanningMessage, 
  createPlanningHandlers
} from "@/api/planning"
import { websocketManager } from "@/utils/streaming-connection-manager"
import { ChatMessages } from "@/components/chat-messages"
import { ChatInput } from "@/components/chat-input"
import { ChatSuggestions } from "@/components/chat-suggestions"
import type { Message, MessageHandlerContext, AiChatProps, WebSocketMessage } from "@/types/chat-types"

export function AiChat({ plan = "", csv = "", onVisualizationGenerated }: AiChatProps) {
  
  
  // State management
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Welcome to ScioScribe! I'm your planning agent and I'll help you design comprehensive research experiments. Tell me about your research question or what you'd like to investigate.",
      sender: "ai",
      timestamp: new Date(),
      mode: "plan",
      response_type: "text"
    }
  ])

  const [inputValue, setInputValue] = useState("")
  const [selectedMode, setSelectedMode] = useState("plan")
  const [isLoading, setIsLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)

  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Get experiment store actions
  const { updatePlanFromPlanningState, updatePlanFromPlanningMessage, updateCsvFromDatacleanResponse } = useExperimentStore()

  // Use the chat sessions hook
  const {
    planningSession,
    datacleanSession,
    initializeDatacleanSession,
    updatePlanningSession,
    updateDatacleanSession
  } = useChatSessions()

  // Mutable refs that always hold the latest session objects. This prevents
  // stale closures inside message handlers (e.g. during approval flows).
  const planningSessionRef = useRef(planningSession)
  const datacleanSessionRef = useRef(datacleanSession)

  // Keep refs in sync with state on every render
  useEffect(() => {
    planningSessionRef.current = planningSession
  }, [planningSession])

  useEffect(() => {
    datacleanSessionRef.current = datacleanSession
  }, [datacleanSession])

  // Create updateMessage function
  const updateMessage = useCallback((messageId: string, updates: Partial<Message>) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, ...updates } : msg
    ))
  }, [])

  // Create message handler context (memoized to prevent infinite re-renders)
   
  const messageHandlerContext: MessageHandlerContext = useMemo(() => ({
    setMessages,
    updateMessage,
    setIsLoading,
    getPlanningSession: () => planningSessionRef.current,
    setPlanningSession: updatePlanningSession,
    getDatacleanSession: () => datacleanSessionRef.current,
    setDatacleanSession: updateDatacleanSession,
    updatePlanFromPlanningState,
    updatePlanFromPlanningMessage,
    updateCsvFromDatacleanResponse,
    onVisualizationGenerated,
    plan,
    csv
  }), [
    // Remove session objects from dependencies to prevent constant re-creation
    updateMessage,
    updatePlanningSession,
    updateDatacleanSession,
    updatePlanFromPlanningState,
    updatePlanFromPlanningMessage,
    updateCsvFromDatacleanResponse,
    onVisualizationGenerated,
    plan,
    csv
     
  ])

  // WebSocket message handler for planning
  const handlePlanningWebSocketMessageWrapper = useCallback((message: WebSocketMessage) => {
    console.log("🎯 Planning WebSocket message received in AiChat:", message)
    
    // Handle real-time updates
    if (message.type === "planning_update") {
      // Planning update received, no additional processing needed
      console.log("📊 Planning update received")
    }
    
    handlePlanningWebSocketMessage(message, messageHandlerContext)
  }, [messageHandlerContext])

  // WebSocket handlers
   
  const planningHandlers = useMemo(() => createPlanningHandlers(
    handlePlanningWebSocketMessageWrapper,
    (error) => {
      console.error("❌ Planning WebSocket error:", error)
      
      // Handle different error types
      if (error.type === "max_reconnect_attempts") {
        const maxAttemptsMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `❌ **Connection Lost**\n\nUnable to reconnect. Please refresh the page to continue.`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "error"
        }
        setMessages((prev) => [...prev, maxAttemptsMessage])
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `⚠️ Connection interrupted. Attempting to reconnect...`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "error"
        }
        setMessages((prev) => [...prev, errorMessage])
      }
    },
    () => {
      console.log("✅ Planning WebSocket connection opened")
      // Connection message removed - no need to show status in chat
    },
    (event) => {
      console.log("🔒 Planning WebSocket connection closed:", event)
      
      if (!event.wasClean) {
        const disconnectMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `🔒 Connection lost. Attempting to reconnect...`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "error"
        }
        setMessages((prev) => [...prev, disconnectMessage])
      }
    }
  ), [handlePlanningWebSocketMessageWrapper
     
  ])

  // Mode-specific message handlers
   
  const handlePlanningMessageWithWebSocket = useCallback(async (message: string) => {
    try {
      // Get current session state to avoid dependency issues
      const currentSession = messageHandlerContext.getPlanningSession()
      
      console.log("🎯 Planning message - current session:", {
        session_id: currentSession.session_id,
        is_active: currentSession.is_active,
        experiment_id: currentSession.experiment_id
      })
      
      // Only initialize a new session if there's no existing session_id
      // Note: is_active can be false during WebSocket events but we should preserve the session
      if (!currentSession.session_id) {
        console.log("🆕 No session ID found - starting new planning session")
        
        // Create planning session
        const sessionResponse = await createPlanningSession({
          research_query: message,
          user_id: "demo-user"
        })
        
        console.log("✅ New planning session created:", sessionResponse.session_id)
        
        // Update session state
        updatePlanningSession({
          session_id: sessionResponse.session_id,
          experiment_id: sessionResponse.experiment_id,
          is_active: true,
          current_stage: sessionResponse.current_stage,
          is_waiting_for_approval: sessionResponse.is_waiting_for_approval,
          pending_approval: sessionResponse.pending_approval,
          last_activity: new Date()
        })
        
        // Initial response message removed - let the agent respond directly
        
        // Connect WebSocket
        const connection = connectPlanningSession(sessionResponse.session_id, planningHandlers)
        
        if (!connection) {
          throw new Error("Failed to establish WebSocket connection")
        }
        
        // Wait for connection to open before sending message
        if (connection.readyState === WebSocket.OPEN) {
          // Send initial message
          sendPlanningMessage(sessionResponse.session_id, message)
        } else {
          // Queue message for when connection opens
          console.log("⏳ Queuing message until WebSocket connection opens")
        }
        
      } else {
        // Continue with existing session regardless of is_active status
        console.log("♻️ Continuing with existing planning session:", currentSession.session_id)
        
        // Ensure session is marked as active since user is interacting
        if (!currentSession.is_active) {
          console.log("🔄 Reactivating session due to user interaction")
          updatePlanningSession({
            is_active: true,
            last_activity: new Date()
          })
        }
        
        // Send message to existing session
        // Use unified planning message handler to properly process
        // user messages and approval responses. This ensures that
        // approval responses are sent with the correct "approval_response"
        // message type instead of being mis-classified as a standard
        // user message, preventing the backend from restarting the
        // planning graph at the objective stage.
        await handlePlanningMessage(message, messageHandlerContext)

        // The handler will queue the message via the WebSocket manager.
        // If it fails we throw to surface the error.
      }
    } catch (error) {
      console.error("❌ Planning message error:", error)
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ **Planning Session Error**\n\nFailed to start or continue planning session.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease try again or refresh the page.`,
        sender: "ai",
        timestamp: new Date(),
        mode: "plan",
        response_type: "error"
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }, [updatePlanningSession, planningHandlers, setMessages, messageHandlerContext])

  const handleExecuteMessageWithSession = useCallback(async (message: string) => {
    try {
      // Initialize session if not active, with automatic CSV integration
      if (!datacleanSession.is_active) {
        console.log("🧹 Initializing dataclean session with CSV integration")
        
        const sessionResponse = await initializeDatacleanSession("demo-user", csv, message)
        
        // Create a temporary context with the new session information
        const tempContext = {
          ...messageHandlerContext,
          getDatacleanSession: () => ({
            session_id: sessionResponse.session_id,
            experiment_id: null,
            is_active: true,
            is_waiting_for_approval: false,
            websocket_connection: null,
            last_activity: new Date()
          })
        }
        
        // Enhanced welcome message that mentions CSV data if available
        if (csv && csv.trim()) {
          const csvWelcomeMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `Hello! Your dataset is ready.\n\n**Tell me to:**\n• "analyze data quality" \n• "clean the data" \n• "describe columns"\n• "add/delete rows" \n• "fix missing values"\n\nWhat first?`,
            sender: "ai",
            timestamp: new Date(),
            mode: "execute",
            response_type: "text"
          }
          setMessages((prev) => [...prev, csvWelcomeMessage])
        } else {
          // Standard welcome without CSV
          createDatacleanWelcomeMessage(sessionResponse.session_id, sessionResponse.response as unknown as Record<string, unknown>, tempContext)
        }
        
        // Session initialization already sent the user's message, so process the response
        const response = sessionResponse.response
        if (response && response.message) {
          const responseMessage: Message = {
            id: (Date.now() + 2).toString(),
            content: response.message,
            sender: "ai",
            timestamp: new Date(),
            mode: "execute",
            response_type: "text"
          }
          setMessages((prev) => [...prev, responseMessage])
        }
        
        // Update session activity
        updateDatacleanSession({ last_activity: new Date() })
      } else {
        // Continue with existing session
        await handleExecuteMessage(message, messageHandlerContext)
      }
    } catch (error) {
      console.error("❌ Execute message error:", error)
    }
  }, [datacleanSession.is_active, initializeDatacleanSession, updateDatacleanSession, messageHandlerContext, csv, setMessages])



  // Mode switching handler
  const handleModeSwitch = useCallback(async (newMode: string) => {
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
      
      // (Disabled) Auto-initialization of CSV conversation on mode switch.
      // Dataclean session will be created lazily when the user sends the first message.
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
          await handlePlanningMessageWithWebSocket(currentInput)
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
  }, [inputValue, selectedMode, setMessages, setInputValue, setIsLoading, handlePlanningMessageWithWebSocket, handleExecuteMessageWithSession, messageHandlerContext])

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

  // Handle typewriter completion for approval message timing
  const handleTypewriterComplete = useCallback((messageId: string) => {
    onTypewriterComplete(messageId, setMessages)
  }, [setMessages])



  // We no longer forcibly close the planning WebSocket when the component
  // unmounts. The backend is responsible for terminating the session when
  // the agent has completed its workflow. This avoids premature session
  // termination triggered by client-side navigation or tab switches.
  useEffect(() => {
    return () => {
      // Intentionally left blank – let the backend handle session lifecycle.
    }
  }, [])

  // Removed auto-initialization when CSV data becomes available. Session will start on first user message.

  // Debug function setup (run once on mount)
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

    // Expose debug functions globally
    ;(window as unknown as Record<string, unknown>).logChatState = logCurrentState
    ;(window as unknown as Record<string, unknown>).logWebSocketDebug = () => websocketManager.logDebugInfo()
    
    // Add global fetch interception for debugging (skip WebSocket upgrade requests)
    const originalFetch = window.fetch
    window.fetch = async (...args) => {
      const url = args[0] as string
      const isWebSocketRequest = url.includes('/ws/') || 
        (args[1] && (args[1] as RequestInit).headers && 
         Object.values((args[1] as RequestInit).headers as Record<string, string>).some(v => 
           v.toLowerCase().includes('websocket')))
      
      if (isWebSocketRequest) {
        console.log("🔄 SKIPPING fetch interception for WebSocket request:", url)
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Remove all dependencies to prevent recreation

  return (
    <Card className="h-full flex flex-col shadow-lg border-0 bg-card/95 backdrop-blur-sm">
      {/* Chat Messages */}
      <ChatMessages
        messages={messages}
        isLoading={isLoading}
        selectedMode={selectedMode}
        onTypewriterComplete={handleTypewriterComplete}
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
