import { useState, useEffect, useCallback } from "react"
import { getPlanningSessionStatus, type PlanningSessionStatus } from "@/api/planning"

interface PlanningSessionState {
  sessionId: string | null
  experimentId: string | null
  isActive: boolean
  isWaitingForApproval: boolean
  currentStage: string | null
  completedStages: string[]
  lastUpdated: Date | null
}

interface UsePlanningSessionOptions {
  autoRefresh?: boolean
  refreshInterval?: number
}

export function usePlanningSession(options: UsePlanningSessionOptions = {}) {
  const { autoRefresh = false, refreshInterval = 5000 } = options
  
  const [sessionState, setSessionState] = useState<PlanningSessionState>({
    sessionId: null,
    experimentId: null,
    isActive: false,
    isWaitingForApproval: false,
    currentStage: null,
    completedStages: [],
    lastUpdated: null
  })
  
    const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSessionStatus = useCallback(async (sessionId: string) => {
    if (!sessionId) return null
    
    setLoading(true)
    setError(null)
    
    try {
      const status = await getPlanningSessionStatus(sessionId)
      
      // Update state directly to avoid callback dependency issues
      setSessionState(prev => ({
        ...prev,
        sessionId: status.session_id,
        experimentId: status.experiment_id,
        isActive: true,
        isWaitingForApproval: status.is_waiting_for_approval,
        currentStage: status.current_stage,
        lastUpdated: new Date()
      }))
      
      return status
    } catch (err) {
      console.error("Failed to fetch planning session status:", err)
      setError(err instanceof Error ? err.message : "Failed to fetch session status")
      return null
    } finally {
      setLoading(false)
    }
  }, []) // Remove updateSessionState dependency

  const startSession = useCallback((sessionId: string, experimentId: string) => {
    setSessionState(prev => ({
      ...prev,
      sessionId,
      experimentId,
      isActive: true,
      isWaitingForApproval: false,
      currentStage: "objective_setting",
      completedStages: [],
      lastUpdated: new Date()
    }))
  }, [])

  const endSession = useCallback(() => {
    setSessionState({
      sessionId: null,
      experimentId: null,
      isActive: false,
      isWaitingForApproval: false,
      currentStage: null,
      completedStages: [],
      lastUpdated: null
    })
  }, [])

  const setApprovalState = useCallback((isWaiting: boolean, pendingApproval?: any) => {
    setSessionState(prev => ({
      ...prev,
      isWaitingForApproval: isWaiting,
      lastUpdated: new Date()
    }))
  }, [])

  const updateStage = useCallback((stage: string) => {
    setSessionState(prev => ({
      ...prev,
      currentStage: stage,
      lastUpdated: new Date()
    }))
  }, [])

  const addCompletedStage = useCallback((stage: string) => {
    setSessionState(prev => ({
      ...prev,
      completedStages: [...prev.completedStages, stage],
      lastUpdated: new Date()
    }))
  }, [])

  // Auto-refresh functionality
  useEffect(() => {
    if (!autoRefresh || !sessionState.sessionId) return

    const interval = setInterval(() => {
      if (sessionState.sessionId) {
        fetchSessionStatus(sessionState.sessionId)
      }
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, sessionState.sessionId, refreshInterval, fetchSessionStatus])

  return {
    sessionState,
    loading,
    error,
    startSession,
    endSession,
    setApprovalState,
    updateStage,
    addCompletedStage,
    fetchSessionStatus
  }
}

// Global planning session manager for sharing state across components
let globalPlanningSession: ReturnType<typeof usePlanningSession> | null = null

export function getGlobalPlanningSession() {
  if (!globalPlanningSession) {
    throw new Error("Global planning session not initialized. Use usePlanningSession in a component first.")
  }
  return globalPlanningSession
}

export function initializeGlobalPlanningSession(session: ReturnType<typeof usePlanningSession>) {
  globalPlanningSession = session
} 