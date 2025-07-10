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
import { handlePlanningWebSocketMessage } from "@/handlers/planning-message-handler"
import { handlePlanningMessage } from "@/handlers/planning-message-handler"
import { handleExecuteMessage, createDatacleanWelcomeMessage } from "@/handlers/execute-message-handler"
import { handleAnalysisMessage } from "@/handlers/analysis-message-handler"
import { 
  createPlanningSession, 
  connectPlanningSession, 
  sendPlanningMessage, 
  createPlanningHandlers,
  retryPlanningConnection
} from "@/api/planning"
import { websocketManager } from "@/utils/streaming-connection-manager"
import { ChatMessages } from "@/components/chat-messages"
import { ChatInput } from "@/components/chat-input"
import { ChatSuggestions } from "@/components/chat-suggestions"
import type { Message, MessageHandlerContext, AiChatProps, WebSocketMessage } from "@/types/chat-types"

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
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState("disconnected")
  const inputRef = useRef<HTMLInputElement>(null)

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

  // Create message handler context (memoized to prevent infinite re-renders)
   
  const messageHandlerContext: MessageHandlerContext = useMemo(() => ({
    setMessages,
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
    updatePlanningSession,
    updateDatacleanSession,
    updatePlanFromPlanningState,
    updatePlanFromPlanningMessage,
    updateCsvFromDatacleanResponse,
    onVisualizationGenerated,
    plan,
    csv
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setIsConnected(false)
      
      // Handle different error types
      const errorWithDetails = error as Event & {
        sessionId?: string
        queuedMessages?: number
        lastError?: string
      }
      
      if (error.type === "max_reconnect_attempts") {
        setConnectionStatus("failed")
        
        const maxAttemptsMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `❌ **Connection Failed**\n\nCould not reconnect to planning server after multiple attempts.\n\nQueued messages: ${errorWithDetails.queuedMessages || 0}\n\n**Options:**\n• Click the retry button in the connection status bar\n• Refresh the page to start a new session\n• Check your internet connection\n\nYour progress has been saved and can be recovered.`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "error"
        }
        setMessages((prev) => [...prev, maxAttemptsMessage])
      } else {
        setConnectionStatus("error")
        
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `❌ **WebSocket Connection Error**\n\nLost connection to planning server.\n\nError: ${error.type || 'Connection failed'}\n\nTrying to reconnect...`,
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
      setIsConnected(true)
      setConnectionStatus("connected")
      
      // Use getter to access current session id
      const currentSession = messageHandlerContext.getPlanningSession()
      const connectionMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `✅ **WebSocket Connected**\n\nReal-time communication established with planning server.\n\nSession ID: ${currentSession.session_id}\n\nYou can now send messages and receive real-time updates.`,
        sender: "ai",
        timestamp: new Date(),
        mode: "plan",
        response_type: "text"
      }
      setMessages((prev) => [...prev, connectionMessage])
    },
    (event) => {
      console.log("🔒 Planning WebSocket connection closed:", event)
      setIsConnected(false)
      setConnectionStatus(event.wasClean ? "disconnected" : "reconnecting")
      
      if (!event.wasClean) {
        const disconnectMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `🔒 **WebSocket Disconnected**\n\nConnection to planning server was lost.\n\nCode: ${event.code}\nReason: ${event.reason || 'Unknown'}\n\nAttempting to reconnect...`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "error"
        }
        setMessages((prev) => [...prev, disconnectMessage])
      }
    }
  ), [handlePlanningWebSocketMessageWrapper
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        
        // Add initial response message
        const initialMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `🎯 **Planning Session Started**\n\nSession ID: ${sessionResponse.session_id}\nExperiment ID: ${sessionResponse.experiment_id}\n\nI'm analyzing your research query: "${message}"\n\nEstablishing WebSocket connection for real-time communication...\n\nI'll help you create a comprehensive experiment plan through:\n\n• **Objective Definition** - Clarifying your research goals\n• **Methodology Selection** - Choosing appropriate methods\n• **Variable Identification** - Defining key variables\n• **Data Requirements** - Specifying data needs\n• **Design Validation** - Reviewing the complete plan\n\nConnecting to planning agent...`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "text"
        }
        setMessages((prev) => [...prev, initialMessage])
        
        // Connect WebSocket
        setConnectionStatus("connecting")
        const connection = connectPlanningSession(sessionResponse.session_id, planningHandlers)
        
        if (!connection) {
          setConnectionStatus("error")
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
  }, [updatePlanningSession, planningHandlers, setMessages, handlePlanningMessage, messageHandlerContext])

  const handleExecuteMessageWithSession = useCallback(async (message: string) => {
    try {
      // Initialize session if not active, with automatic CSV integration
      if (!datacleanSession.is_active) {
        console.log("🧹 Initializing dataclean session with CSV integration")
        
        const sessionResponse = await initializeDatacleanSession("demo-user", csv)
        
        // Enhanced welcome message that mentions CSV data if available
        if (csv && csv.trim()) {
          const csvWelcomeMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `🧹 **Data Cleaning Session Started**\n\nSession ID: ${sessionResponse.session_id}\n\n**CSV Data Detected:** I can see you have dataset loaded!\n\nI'm ready to help you with:\n• Data quality analysis\n• Cleaning and fixing issues\n• Removing duplicates\n• Handling missing values\n• Data transformation\n\nProcessing your message: "${message}"\n\nLet me analyze your data...`,
            sender: "ai",
            timestamp: new Date(),
            mode: "execute",
            response_type: "text"
          }
          setMessages((prev) => [...prev, csvWelcomeMessage])
          
          // Send message with CSV context
          await handleExecuteMessage(`CSV Data Available. User request: ${message}`, messageHandlerContext)
        } else {
          // Standard welcome without CSV
          createDatacleanWelcomeMessage(sessionResponse.session_id, sessionResponse.response as unknown as Record<string, unknown>, messageHandlerContext)
          await handleExecuteMessage(message, messageHandlerContext)
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
  }, [datacleanSession.is_active, initializeDatacleanSession, updateDatacleanSession, messageHandlerContext, csv, setMessages, handleExecuteMessage])

  // Auto-initialize CSV conversation when CSV data is available
  const autoInitializeCsvConversation = useCallback(async () => {
    try {
      console.log("🧹 Auto-initializing CSV conversation with available data")
      
      // Initialize dataclean session with CSV data
      const sessionResponse = await initializeDatacleanSession("demo-user", csv)
      
      // Create CSV analysis message 
      const csvAnalysisMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `🧹 **CSV Data Detected**\n\nI've detected CSV data in your experiment and automatically initialized a data cleaning session.\n\n**Session ID:** ${sessionResponse.session_id}\n\n**Dataset Preview:**\n- Processing your CSV data...\n- Analyzing data quality...\n- Preparing suggestions...\n\nI'm now analyzing your dataset. Feel free to ask me to:\n• Clean and fix data issues\n• Remove duplicates or missing values\n• Transform data formats\n• Generate quality reports\n\nWhat would you like me to help you with?`,
        sender: "ai",
        timestamp: new Date(),
        mode: "execute",
        response_type: "text"
      }
      
      setMessages((prev) => [...prev, csvAnalysisMessage])
      
      // Process CSV data through the conversation system
      if (csv && csv.trim()) {
        console.log("📊 Sending CSV data for analysis")
        
        // Simulate sending CSV for analysis
        await handleExecuteMessage(`I have CSV data ready for analysis. Please analyze this dataset: ${csv.substring(0, 200)}...`, messageHandlerContext)
      }
      
      // Update session activity
      updateDatacleanSession({ last_activity: new Date() })
      
    } catch (error) {
      console.error("❌ Auto CSV initialization error:", error)
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ **Auto-Initialization Failed**\n\nFailed to automatically initialize CSV conversation.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\nYou can still manually send messages to start the conversation.`,
        sender: "ai",
        timestamp: new Date(),
        mode: "execute",
        response_type: "error"
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }, [csv, initializeDatacleanSession, updateDatacleanSession, messageHandlerContext, setMessages, handleExecuteMessage])

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
  }, [selectedMode, setMessages, csv, datacleanSession.is_active, autoInitializeCsvConversation])

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

  // Retry connection handler
  const handleRetryConnection = useCallback(() => {
    const currentSession = messageHandlerContext.getPlanningSession()
    if (currentSession.session_id) {
      console.log("🔄 Manual retry requested for session:", currentSession.session_id)
      setConnectionStatus("connecting")
      const success = retryPlanningConnection(currentSession.session_id)
      
      if (success) {
        const retryMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `🔄 **Retry Connection**\n\nAttempting to reconnect to planning server...\n\nSession ID: ${currentSession.session_id}\n\nPlease wait while we restore your connection.`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "text"
        }
        setMessages((prev) => [...prev, retryMessage])
      } else {
        setConnectionStatus("failed")
        
        const failedRetryMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `❌ **Retry Failed**\n\nCould not initiate connection retry.\n\nPlease refresh the page and start a new session.`,
          sender: "ai",
          timestamp: new Date(),
          mode: "plan",
          response_type: "error"
        }
        setMessages((prev) => [...prev, failedRetryMessage])
      }
    }
  }, [messageHandlerContext, setMessages])

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
      console.log("🔌 WebSocket connected:", isConnected)
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
    <Card className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800">
      {/* Chat Messages */}
      <ChatMessages
        messages={messages}
        isLoading={isLoading}
        selectedMode={selectedMode}
        isConnected={isConnected}
        connectionStatus={connectionStatus}
        lastActivity={planningSession.last_activity}
        onRetryConnection={handleRetryConnection}
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
