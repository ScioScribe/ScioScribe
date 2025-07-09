"use client"

import type React from "react"
import { useState, useEffect, useCallback } from "react"
import { TextEditor } from "@/components/text-editor"
import { getPlanningSessionStatus } from "@/api/planning"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { RefreshCw, Download, Eye, EyeOff } from "lucide-react"

interface PlanningStateEditorProps {
  sessionId: string | null
  onStateChange?: (state: any) => void
  autoRefresh?: boolean
  refreshInterval?: number
}

export function PlanningStateEditor({
  sessionId,
  onStateChange,
  autoRefresh = true,
  refreshInterval = 5000
}: PlanningStateEditorProps) {
  const [stateJson, setStateJson] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [sessionStatus, setSessionStatus] = useState<any>(null)
  const [isExpanded, setIsExpanded] = useState(true)

  const fetchPlanningState = useCallback(async () => {
    if (!sessionId) {
      setStateJson("")
      setError("No active planning session")
      return
    }

    setLoading(true)
    setError(null)

    try {
      console.log("🔄 Fetching planning session status for:", sessionId)
      const status = await getPlanningSessionStatus(sessionId)
      
      // Store the session status
      setSessionStatus(status)
      
      // Format the state as JSON with proper indentation
      const formattedJson = JSON.stringify(status, null, 2)
      setStateJson(formattedJson)
      setLastUpdated(new Date())
      
      // Call the callback if provided
      if (onStateChange) {
        onStateChange(status)
      }
      
      console.log("✅ Planning state fetched successfully")
    } catch (err) {
      console.error("❌ Failed to fetch planning state:", err)
      setError(err instanceof Error ? err.message : "Failed to fetch planning state")
      setStateJson("")
    } finally {
      setLoading(false)
    }
  }, [sessionId]) // Remove onStateChange dependency

  // Initial fetch
  useEffect(() => {
    fetchPlanningState()
  }, [fetchPlanningState])

  // Auto-refresh functionality
  useEffect(() => {
    if (!autoRefresh || !sessionId) return

    const interval = setInterval(fetchPlanningState, refreshInterval)
    return () => clearInterval(interval)
  }, [autoRefresh, sessionId, refreshInterval, fetchPlanningState])

  const handleManualRefresh = () => {
    fetchPlanningState()
  }

  const handleStateChange = (newState: string) => {
    setStateJson(newState)
    try {
      const parsedState = JSON.parse(newState)
      if (onStateChange) {
        onStateChange(parsedState)
      }
    } catch (err) {
      console.warn("Invalid JSON in editor:", err)
    }
  }

  const handleDownload = () => {
    if (!stateJson) return
    
    const blob = new Blob([stateJson], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `planning-state-${sessionId}-${new Date().toISOString()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getStatusBadge = () => {
    if (!sessionStatus) return null

    const { current_stage, is_waiting_for_approval, completed_stages } = sessionStatus
    
    if (is_waiting_for_approval) {
      return <Badge variant="outline" className="bg-yellow-100 text-yellow-800">⏳ Waiting for Approval</Badge>
    }
    
    if (completed_stages && completed_stages.length > 0) {
      return <Badge variant="outline" className="bg-green-100 text-green-800">✅ {completed_stages.length} Stages Complete</Badge>
    }
    
    return <Badge variant="outline" className="bg-blue-100 text-blue-800">🔄 {current_stage || "Active"}</Badge>
  }

  const getSessionInfo = () => {
    if (!sessionStatus) return null

    return (
      <div className="flex flex-wrap gap-2 text-sm text-gray-600 dark:text-gray-400">
        <span>Session: {sessionId?.substring(0, 8)}...</span>
        <span>Stage: {sessionStatus.current_stage || "Unknown"}</span>
        <span>Experiment: {sessionStatus.experiment_id?.substring(0, 8)}...</span>
        {lastUpdated && (
          <span>Updated: {lastUpdated.toLocaleTimeString()}</span>
        )}
      </div>
    )
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <div className="flex items-center gap-2">
              <span>Planning Session State</span>
              {getStatusBadge()}
            </div>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 w-8 p-0"
            >
              {isExpanded ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={loading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={!stateJson}
              className="h-8 w-8 p-0"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {getSessionInfo()}
      </CardHeader>

      {isExpanded && (
        <CardContent className="flex-1 flex flex-col min-h-0 p-0">
          {!sessionId ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p className="text-lg mb-2">No Planning Session Active</p>
                <p className="text-sm">Start a planning session to view the state</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center text-red-500">
              <div className="text-center">
                <p className="text-lg mb-2">Error Loading State</p>
                <p className="text-sm">{error}</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleManualRefresh}
                  className="mt-2"
                >
                  Try Again
                </Button>
              </div>
            </div>
          ) : loading && !stateJson ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                <p>Loading planning state...</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 min-h-0">
              <TextEditor
                value={stateJson}
                onChange={handleStateChange}
              />
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
} 