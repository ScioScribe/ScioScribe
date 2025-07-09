/**
 * Chat Sessions Hook
 * 
 * This hook manages the lifecycle of chat sessions for both planning and data cleaning modes.
 * It handles session initialization, state management, cleanup, and timeout handling.
 */

import { useState, useEffect, useCallback } from "react"
import { usePlanningSession } from "@/hooks/use-planning-session"
import { startPlanningSession, type StartPlanningSessionRequest } from "@/api/planning"
import { startConversation, type StartConversationRequest } from "@/api/dataclean"
import { streamingManager } from "@/utils/streaming-connection-manager"
import type { SessionState } from "@/types/chat-types"

export interface ChatSessionsHookReturn {
  planningSession: SessionState
  datacleanSession: SessionState
  initializePlanningSession: (researchQuery: string) => Promise<{ session_id: string; experiment_id: string }>
  initializeDatacleanSession: (userId?: string) => Promise<{ session_id: string; response: any }>
  cleanupPlanningSession: () => void
  cleanupDatacleanSession: () => void
  updatePlanningSession: (updates: Partial<SessionState>) => void
  updateDatacleanSession: (updates: Partial<SessionState>) => void
  isPlanningSessionActive: boolean
  isDatacleanSessionActive: boolean
}

export function useChatSessions(): ChatSessionsHookReturn {
  // Debug: Add render tracking
  console.log("🔄 useChatSessions render")
  
  // Initialize session states
  const [planningSession, setPlanningSession] = useState<SessionState>({
    session_id: null,
    experiment_id: null,
    is_active: false,
    is_waiting_for_approval: false,
    stream_connection: null,
    last_activity: new Date()
  })

  const [datacleanSession, setDatacleanSession] = useState<SessionState>({
    session_id: null,
    experiment_id: null,
    is_active: false,
    is_waiting_for_approval: false,
    stream_connection: null,
    last_activity: new Date()
  })

  // Use the planning session hook
  const planningSessionHook = usePlanningSession({ autoRefresh: false })

  /**
   * Initialize a new planning session
   * @param researchQuery The research query to start the session with
   * @returns Session and experiment IDs
   */
  const initializePlanningSession = useCallback(async (researchQuery: string) => {
    try {
      console.log("🎯 Initializing planning session with query:", researchQuery)
      
      const requestBody: StartPlanningSessionRequest = {
        research_query: researchQuery,
      }
      console.log("📤 START PLANNING SESSION REQUEST:", requestBody)
      
      const response = await startPlanningSession(requestBody)
      console.log("📥 START PLANNING SESSION RESPONSE BODY:", JSON.stringify(response, null, 2))

      console.log("🔄 Setting up new planning session state")
      const newSessionState = {
        session_id: response.session_id,
        experiment_id: response.experiment_id,
        is_active: true,
        is_waiting_for_approval: false,
        stream_connection: null,
        last_activity: new Date()
      }
      
      console.log("📊 New planning session state:", newSessionState)
      setPlanningSession(newSessionState)

      // Update the planning session hook
      planningSessionHook.startSession(response.session_id, response.experiment_id)

      console.log("✅ Planning session initialized:", response.session_id)
      return { session_id: response.session_id, experiment_id: response.experiment_id }
    } catch (error) {
      console.error("❌ Failed to initialize planning session:", error)
      throw error
    }
  }, [planningSessionHook])

  /**
   * Initialize a new dataclean session
   * @param userId User ID for the session (defaults to "demo-user")
   * @returns Session ID and response data
   */
  const initializeDatacleanSession = useCallback(async (userId: string = "demo-user") => {
    try {
      console.log("🧹 Initializing dataclean session for user:", userId)
      
      const requestBody: StartConversationRequest = {
        user_id: userId,
      }
      console.log("📤 START CONVERSATION REQUEST:", requestBody)
      
      const response = await startConversation(requestBody)
      console.log("📥 START CONVERSATION RESPONSE BODY:", JSON.stringify(response, null, 2))

      setDatacleanSession({
        session_id: response.session_id,
        experiment_id: null,
        is_active: true,
        is_waiting_for_approval: false,
        stream_connection: null,
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
        streamingManager.closeConnection(currentState.session_id)
      }
      
      const cleanedState = {
        session_id: null,
        experiment_id: null,
        is_active: false,
        is_waiting_for_approval: false,
        stream_connection: null,
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
    
    if (datacleanSession.session_id) {
      streamingManager.closeConnection(datacleanSession.session_id)
    }
    
    setDatacleanSession({
      session_id: null,
      experiment_id: null,
      is_active: false,
      is_waiting_for_approval: false,
      stream_connection: null,
      last_activity: new Date()
    })
  }, [datacleanSession.session_id])

  /**
   * Update planning session state
   * @param updates Partial updates to apply to the session
   */
  const updatePlanningSession = useCallback((updates: Partial<SessionState>) => {
    console.log("🔄 updatePlanningSession called with:", updates)
    setPlanningSession(prev => ({
      ...prev,
      ...updates
    }))
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

  // Session timeout and health check handling
  useEffect(() => {
    const checkSessionTimeout = () => {
      const now = new Date()
      const timeoutMs = 30 * 60 * 1000 // 30 minutes

      if (planningSession.is_active && 
          now.getTime() - planningSession.last_activity.getTime() > timeoutMs) {
        console.log("⏰ Planning session timed out")
        cleanupPlanningSession()
      }

      if (datacleanSession.is_active && 
          now.getTime() - datacleanSession.last_activity.getTime() > timeoutMs) {
        console.log("⏰ Dataclean session timed out")
        cleanupDatacleanSession()
      }
      
      // Perform streaming health check
      streamingManager.performHealthCheck()
    }

    const timeoutInterval = setInterval(checkSessionTimeout, 60000) // Check every minute
    return () => clearInterval(timeoutInterval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planningSession.is_active, planningSession.last_activity, datacleanSession.is_active, datacleanSession.last_activity])

  // Cleanup sessions on unmount
  useEffect(() => {
    return () => {
      cleanupPlanningSession()
      cleanupDatacleanSession()
      streamingManager.closeAllConnections()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty dependency array - only run on mount/unmount

  return {
    planningSession,
    datacleanSession,
    initializePlanningSession,
    initializeDatacleanSession,
    cleanupPlanningSession,
    cleanupDatacleanSession,
    updatePlanningSession,
    updateDatacleanSession,
    isPlanningSessionActive: planningSession.is_active,
    isDatacleanSessionActive: datacleanSession.is_active
  }
} 