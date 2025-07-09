"use client"

import { PlanningDashboard } from "@/components/planning-dashboard"
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Info } from "lucide-react"

export default function PlanningDemoPage() {
  return (
    <div className="container mx-auto p-4 h-screen flex flex-col">
      <div className="flex-shrink-0 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Planning State Editor Demo</h1>
            <p className="text-gray-600 mt-1">
              Interact with the planning agent and view the session state in real-time
            </p>
          </div>
          <Badge variant="outline" className="bg-blue-100 text-blue-800">
            Demo Mode
          </Badge>
        </div>
        
        <Alert className="mt-4">
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>How to use:</strong> Start by switching to "plan" mode in the chat and asking a research question. 
            The planning agent will begin a session, and you can view the live session state in the "State Editor" tab.
          </AlertDescription>
        </Alert>
      </div>
      
      <div className="flex-1 min-h-0">
        <PlanningDashboard
          onPlanChange={(text) => console.log("Plan changed:", text)}
          onVisualizationGenerated={(html) => console.log("Visualization generated:", html)}
        />
      </div>
    </div>
  )
} 