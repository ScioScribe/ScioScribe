"use client"

import { useState } from "react"
import { FileText, Save, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ExperimentsDropdown } from "@/components/experiments-dropdown"
import { ExperimentTitle } from "@/components/experiment-title"
import { useExperimentStore } from "@/stores"
import { updateExperimentPlan, updateExperimentCsv, updateExperimentHtml } from "@/api/database"
import type { Experiment } from "@/api/database"

interface TitleProps {
  experiments?: Experiment[]
  selectedExperiment?: Experiment | null
  onExperimentSelect?: (experiment: Experiment) => void
  onExperimentCreated?: () => void
  onExperimentDelete?: (experimentId: string) => Promise<void>
  experimentTitle?: string
  onTitleChange?: (title: string) => void
}

export function Title({ experiments = [], selectedExperiment, onExperimentSelect, onExperimentCreated, onExperimentDelete, experimentTitle, onTitleChange }: TitleProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  
  // Get current experiment data from the store
  const { currentExperiment, editorText, csvData, visualizationHtml, setCurrentExperiment } = useExperimentStore()

  const handleScioScribeClick = () => {
    // Clear current experiment to show home page
    setCurrentExperiment(null)
  }

  const handleSave = async () => {
    if (!currentExperiment) {
      console.warn("No experiment selected to save")
      return
    }

    setIsSaving(true)

    try {
      // Save all experiment data in parallel
      const savePromises = []
      
      // Save experimental plan
      if (editorText) {
        savePromises.push(updateExperimentPlan(currentExperiment.id, editorText))
      }
      
      // Save CSV data
      if (csvData) {
        savePromises.push(updateExperimentCsv(currentExperiment.id, csvData))
      }
      
      // Save visualization HTML
      if (visualizationHtml) {
        savePromises.push(updateExperimentHtml(currentExperiment.id, visualizationHtml))
      }

      // Execute all save operations
      await Promise.all(savePromises)

      setIsSaved(true)
      console.log("✅ Experiment saved successfully!")

      // Reset saved state after 2 seconds
      setTimeout(() => setIsSaved(false), 2000)
    } catch (error) {
      console.error("❌ Failed to save experiment:", error)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex items-center justify-between px-4 py-2">
      {/* Left side - Logo, title, and save button */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-500" />
          <h1
            className="text-lg font-bold text-gray-900 dark:text-white cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            }}
            onClick={handleScioScribeClick}
          >
            ScioScribe
          </h1>
        </div>

        <Button
          onClick={handleSave}
          disabled={isSaving || !currentExperiment}
          variant="ghost"
          size="sm"
          className="h-8 px-3 text-xs dark:text-gray-300 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          }}
        >
          {isSaving ? (
            <>
              <div className="animate-spin h-3 w-3 mr-2 border border-gray-400 border-t-transparent rounded-full" />
              saving...
            </>
          ) : isSaved ? (
            <>
              <Check className="h-3 w-3 mr-2 text-green-500" />
              saved
            </>
          ) : (
            <>
              <Save className="h-3 w-3 mr-2" />
              save
            </>
          )}
        </Button>
      </div>

      {/* Center - Experiment title */}
      <div className="flex-1 flex justify-center">
        <ExperimentTitle 
          initialTitle={experimentTitle}
          onTitleChange={onTitleChange}
        />
      </div>

      {/* Right side - Experiments dropdown */}
      <div>
        <ExperimentsDropdown 
          experiments={experiments}
          selectedExperiment={selectedExperiment || null}
          onExperimentSelect={onExperimentSelect}
          onExperimentCreated={onExperimentCreated}
          onExperimentDelete={onExperimentDelete}
        />
      </div>
    </div>
  )
}
