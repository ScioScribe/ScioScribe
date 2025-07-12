/**
 * Chat Sessions Hook
 * 
 * This hook manages the lifecycle of chat sessions for both planning and data cleaning modes.
 * It handles session initialization, state management, cleanup, and WebSocket connection management.
 */

import { useState, useEffect, useCallback } from "react"
import { usePlanningSession } from "@/hooks/use-planning-session"
import { startConversation, type StartConversationRequest, type StartConversationResponse } from "@/api/dataclean"
import { websocketManager } from "@/utils/streaming-connection-manager"
import type { SessionState } from "@/types/chat-types"

export interface ChatSessionsHookReturn {
  planningSession: SessionState
  datacleanSession: SessionState
  initializeDatacleanSession: (userId?: string, initialCsv?: string, userMessage?: string) => Promise<{ session_id: string; response: StartConversationResponse }>
  cleanupPlanningSession: () => void
  cleanupDatacleanSession: () => void
  updatePlanningSession: (updates: Partial<SessionState>) => void
  updateDatacleanSession: (updates: Partial<SessionState>) => void
  isPlanningSessionActive: boolean
  isDatacleanSessionActive: boolean
  isPlanningSessionConnected: boolean
}

export function useChatSessions(): ChatSessionsHookReturn {
  
  
  // Initialize session states
  const [planningSession, setPlanningSession] = useState<SessionState>({
    session_id: null,
    experiment_id: null,
    is_active: false,
    is_waiting_for_approval: false,
    websocket_connection: null,
    last_activity: new Date()
  })

  const [datacleanSession, setDatacleanSession] = useState<SessionState>({
    session_id: null,
    experiment_id: null,
    is_active: false,
    is_waiting_for_approval: false,
    websocket_connection: null,
    last_activity: new Date()
  })

  // Use the planning session hook
  const planningSessionHook = usePlanningSession({ autoRefresh: false })

  /**
   * Initialize a new dataclean session
   * @param userId User ID for the session (defaults to "demo-user")
   * @returns Session ID and response data
   */
  const initializeDatacleanSession = useCallback(async (userId: string = "demo-user", initialCsv?: string, userMessage?: string) => {
    try {
      console.log("🧹 Initializing dataclean session for user:", userId)
      
      const requestBody: StartConversationRequest = {
        user_id: userId,
        csv_data: initialCsv,
        user_message: userMessage,
      }
      console.log("📤 START CONVERSATION REQUEST:", requestBody)
      
      const response = await startConversation(requestBody)
      console.log("📥 START CONVERSATION RESPONSE BODY:", JSON.stringify(response, null, 2))

      setDatacleanSession({
        session_id: response.session_id,
        experiment_id: null,
        is_active: true,
        is_waiting_for_approval: false,
        websocket_connection: null,
        last_activity: new Date()
      })

      console.log("✅ Dataclean session initialized:", response.session_id)
      return { session_id: response.session_id, response: response }
    } catch (error) {
      console.error("❌ Failed to initialize dataclean session:", error)
      throw error
    }
  }, [])

  /**
   * Clean up planning session resources
   */
  const cleanupPlanningSession = useCallback(() => {
    console.log("🧹 Cleaning up planning session")
    
    // Get current state via ref to avoid dependency
    setPlanningSession(currentState => {
      console.log("📊 Session state before cleanup:", currentState)
      
      if (currentState.session_id) {
        // Close WebSocket connection
        websocketManager.closeConnection(currentState.session_id)
      }
      
      const cleanedState = {
        session_id: null,
        experiment_id: null,
        is_active: false,
        is_waiting_for_approval: false,
        websocket_connection: null,
        last_activity: new Date()
      }
      
      console.log("📊 Setting cleaned session state:", cleanedState)
      return cleanedState
    })

    // Clean up the planning session hook
    planningSessionHook.endSession()
  }, [planningSessionHook])

  /**
   * Clean up dataclean session resources
   */
  const cleanupDatacleanSession = useCallback(() => {
    console.log("🧹 Cleaning up dataclean session")
    
    // Get current state via setter callback to avoid dependency
    setDatacleanSession(currentState => {
      if (currentState.session_id) {
        websocketManager.closeConnection(currentState.session_id)
      }
      
      return {
        session_id: null,
        experiment_id: null,
        is_active: false,
        is_waiting_for_approval: false,
        websocket_connection: null,
        last_activity: new Date()
      }
    })
  }, [])

  /**
   * Update planning session state
   * @param updates Partial updates to apply to the session
   */
  const updatePlanningSession = useCallback((updates: Partial<SessionState>) => {
    console.log("🔄 updatePlanningSession called with:", updates)

    setPlanningSession(prev => {
      // Safeguard: never allow critical identifiers to be cleared accidentally
      const safeUpdates: Partial<SessionState> = { ...updates }

      if ("session_id" in safeUpdates && (safeUpdates.session_id === null || safeUpdates.session_id === undefined)) {
        console.warn("⚠️ Attempt to clear session_id ignored")
        delete safeUpdates.session_id
      }

      if ("experiment_id" in safeUpdates && (safeUpdates.experiment_id === null || safeUpdates.experiment_id === undefined)) {
        console.warn("⚠️ Attempt to clear experiment_id ignored")
        delete safeUpdates.experiment_id
      }

      const updatedState: SessionState = {
        ...prev,
        ...safeUpdates
      }

      // Maintain websocket reference if connection exists for this session
      if (updatedState.session_id && websocketManager.isConnected(updatedState.session_id)) {
        updatedState.websocket_connection = websocketManager.getConnection(updatedState.session_id)
      }

      return updatedState
    })
  }, [])

  /**
   * Update dataclean session state
   * @param updates Partial updates to apply to the session
   */
  const updateDatacleanSession = useCallback((updates: Partial<SessionState>) => {
    console.log("🔄 updateDatacleanSession called with:", updates)
    setDatacleanSession(prev => ({
      ...prev,
      ...updates
    }))
  }, [])

  /**
   * Check if planning session has an active WebSocket connection
   */
  const isPlanningSessionConnected = useCallback(() => {
    return planningSession.session_id ? websocketManager.isConnected(planningSession.session_id) : false
  }, [planningSession.session_id])

  // WebSocket health monitoring and session timeout handling
  useEffect(() => {
    const checkSessionHealth = () => {
      const now = new Date()
      const timeoutMs = 30 * 60 * 1000 // 30 minutes

      // Use functional setState to avoid dependencies on session objects
      // Do not auto-cleanup planning sessions; backend controls lifecycle.
      setPlanningSession(prev => prev)

      setDatacleanSession(prev => {
        if (prev.is_active && now.getTime() - prev.last_activity.getTime() > timeoutMs) {
          console.log("⏰ Dataclean session timed out")
          cleanupDatacleanSession()
        }
        return prev
      })
      
      // Perform WebSocket health check
      websocketManager.performHealthCheck()
    }

    const healthInterval = setInterval(checkSessionHealth, 60000) // Check every minute
    return () => clearInterval(healthInterval)
  }, [cleanupPlanningSession, cleanupDatacleanSession]) // Remove session objects from dependencies

  // WebSocket connection status monitoring
  useEffect(() => {
    const monitorConnections = () => {
      // Update planning session connection status using functional setState to avoid dependencies
      setPlanningSession(prev => {
        if (prev.session_id) {
          const isConnected = websocketManager.isConnected(prev.session_id)
          // Use connection status instead of object comparison to avoid infinite loops
          const hasConnection = !!prev.websocket_connection
          
          if (isConnected && !hasConnection) {
            console.log(`🔍 Planning WebSocket connection established`)
            return {
              ...prev,
              websocket_connection: websocketManager.getConnection(prev.session_id)
            }
          } else if (!isConnected && hasConnection) {
            console.log(`🔍 Planning WebSocket connection lost`)
            return {
              ...prev,
              websocket_connection: null
            }
          }
        }
        return prev
      })
      
      // Update dataclean session connection status using functional setState
      setDatacleanSession(prev => {
        if (prev.session_id) {
          const isConnected = websocketManager.isConnected(prev.session_id)
          const hasConnection = !!prev.websocket_connection
          
          if (isConnected && !hasConnection) {
            return {
              ...prev,
              websocket_connection: websocketManager.getConnection(prev.session_id)
            }
          } else if (!isConnected && hasConnection) {
            return {
              ...prev,
              websocket_connection: null
            }
          }
        }
        return prev
      })
    }

    const connectionMonitorInterval = setInterval(monitorConnections, 5000) // Check every 5 seconds
    return () => clearInterval(connectionMonitorInterval)
  }, [])

  // Do not automatically clean up planning sessions on unmount –
  // the backend decides when the session ends. We still clean up
  // dataclean sessions and close outstanding websockets for safety.
  useEffect(() => {
    return () => {
      console.log("🔒 Component unmounted – closing non-planning connections")
      cleanupDatacleanSession()
      websocketManager.closeAllConnections()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Intentional empty dependency list

  // Debug logging for session state changes
  useEffect(() => {
    console.log("📊 Planning session state updated:", {
      session_id: planningSession.session_id,
      is_active: planningSession.is_active,
      is_waiting_for_approval: planningSession.is_waiting_for_approval,
      has_websocket: !!planningSession.websocket_connection,
      websocket_ready_state: planningSession.websocket_connection?.readyState
    })
  }, [planningSession])

  useEffect(() => {
    console.log("📊 Dataclean session state updated:", {
      session_id: datacleanSession.session_id,
      is_active: datacleanSession.is_active,
      has_websocket: !!datacleanSession.websocket_connection
    })
  }, [datacleanSession])

  return {
    planningSession,
    datacleanSession,
    initializeDatacleanSession,
    cleanupPlanningSession,
    cleanupDatacleanSession,
    updatePlanningSession,
    updateDatacleanSession,
    isPlanningSessionActive: planningSession.is_active,
    isDatacleanSessionActive: datacleanSession.is_active,
    isPlanningSessionConnected: isPlanningSessionConnected()
  }
} 