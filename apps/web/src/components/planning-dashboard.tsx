"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { AiChat } from "@/components/ai-chat"
import { PlanningStateEditor } from "@/components/planning-state-editor"
import { usePlanningSession } from "@/hooks/use-planning-session"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MessageSquare, FileText, Activity } from "lucide-react"

interface PlanningDashboardProps {
  initialPlan?: string
  csv?: string
  editorText?: string
  onPlanChange?: (text: string) => void
  onVisualizationGenerated?: (html: string) => void
}

export function PlanningDashboard({
  initialPlan = "",
  csv = "",
  editorText = "",
  onPlanChange,
  onVisualizationGenerated
}: PlanningDashboardProps) {
  const planningSession = usePlanningSession({ autoRefresh: true, refreshInterval: 3000 })
  const [activeTab, setActiveTab] = useState("chat")
  const [plan, setPlan] = useState(initialPlan)

  // Handle plan changes
  const handlePlanChange = (text: string) => {
    setPlan(text)
    onPlanChange?.(text)
  }

  // Handle state changes from the planning state editor
  const handleStateChange = (state: Record<string, unknown>) => {
    console.log("Planning state updated:", state)
    
    // You can add logic here to sync the state with other components
    // For example, update the plan text based on the state
    if (state && state.experiment_objective) {
      // Update plan with new objective information
      const updatedPlan = `${plan}\n\n// Updated from planning session\n// Objective: ${state.experiment_objective}\n// Current Stage: ${state.current_stage}`
      handlePlanChange(updatedPlan)
    }
  }

  // Monitor session state for UI updates
  useEffect(() => {
    if (planningSession.sessionState.sessionId) {
      console.log("Planning session active:", planningSession.sessionState)
    }
  }, [planningSession.sessionState])

  const getSessionStatusInfo = () => {
    const { sessionState } = planningSession
    
    if (!sessionState.isActive) {
      return (
        <div className="flex items-center gap-2 text-gray-500">
          <div className="w-2 h-2 bg-gray-400 rounded-full" />
          <span>No active session</span>
        </div>
      )
    }

    return (
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        <span className="text-sm">Active Session</span>
        <Badge variant="outline" className="text-xs">
          {sessionState.currentStage || "Unknown"}
        </Badge>
        {sessionState.isWaitingForApproval && (
          <Badge variant="outline" className="text-xs bg-yellow-100 text-yellow-800">
            Waiting for Approval
          </Badge>
        )}
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Planning Dashboard</h2>
            <p className="text-sm text-gray-600">
              Interact with the planning agent and monitor session state
            </p>
          </div>
          <div className="flex items-center gap-4">
            {getSessionStatusInfo()}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveTab("state")}
              className="flex items-center gap-2"
            >
              <Activity className="h-4 w-4" />
              View State
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-h-0">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="chat" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Chat
            </TabsTrigger>
            <TabsTrigger value="state" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              State Editor
            </TabsTrigger>
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Overview
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="flex-1 min-h-0">
            <div className="h-full p-4">
              <AiChat
                plan={plan}
                csv={csv}
                editorText={editorText}
                onPlanChange={handlePlanChange}
                onVisualizationGenerated={onVisualizationGenerated}
              />
            </div>
          </TabsContent>

          <TabsContent value="state" className="flex-1 min-h-0">
            <div className="h-full p-4">
              <PlanningStateEditor
                sessionId={planningSession.sessionState.sessionId}
                onStateChange={handleStateChange}
                autoRefresh={true}
                refreshInterval={3000}
              />
            </div>
          </TabsContent>

          <TabsContent value="overview" className="flex-1 min-h-0">
            <div className="h-full p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Session Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Session ID:</span>
                      <span className="text-sm font-mono">
                        {planningSession.sessionState.sessionId?.substring(0, 8) || "None"}...
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Experiment ID:</span>
                      <span className="text-sm font-mono">
                        {planningSession.sessionState.experimentId?.substring(0, 8) || "None"}...
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Current Stage:</span>
                      <span className="text-sm">
                        {planningSession.sessionState.currentStage || "None"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Status:</span>
                      <span className="text-sm">
                        {planningSession.sessionState.isWaitingForApproval ? "Waiting for Approval" : "Active"}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Progress</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Completed Stages:</span>
                        <span>{planningSession.sessionState.completedStages.length}</span>
                      </div>
                      <div className="space-y-1">
                        {planningSession.sessionState.completedStages.map((stage, index) => (
                          <div key={index} className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full" />
                            <span className="text-sm">{stage}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => planningSession.fetchSessionStatus(planningSession.sessionState.sessionId!)}
                      disabled={!planningSession.sessionState.sessionId}
                    >
                      Refresh Status
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => planningSession.endSession()}
                      disabled={!planningSession.sessionState.sessionId}
                    >
                      End Session
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
} 