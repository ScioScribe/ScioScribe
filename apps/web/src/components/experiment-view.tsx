"use client"

/**
 * Experiment View Component
 * 
 * Main experiment interface with text editor, data table, graph viewer, and AI chat.
 * This is the core working environment for conducting experiments.
 */

import { useEffect } from 'react'
import { Title } from "@/components/title"
import { TextEditor } from "@/components/text-editor"
import { DataTableViewer } from "@/components/data-table-viewer"
import { GraphViewer } from "@/components/graph-viewer"
import { AiChat } from "@/components/ai-chat"
import { HomePage } from "@/components/home-page"
import { useExperimentStore } from "@/stores"

export function ExperimentView() {
  // Get state and actions from Zustand store
  const {
    currentExperiment,
    experiments,
    isLoading,
    experimentTitle,
    editorText,
    csvData,
    visualizationHtml,
    loadExperiments,
    createExperiment,
    selectExperiment,
    updateEditorTextWithSave,
    updateVisualizationHtmlWithSave,
    updateExperimentTitleWithSave,
    refreshVisualization,
    removeExperiment,
  } = useExperimentStore()

  // Load experiments on component mount
  useEffect(() => {
    loadExperiments()
  }, [loadExperiments])

  // Handle experiment creation from dropdown
  const handleExperimentCreated = async () => {
    try {
      const newExperiment = await createExperiment()
      selectExperiment(newExperiment)
    } catch (error) {
      console.error("Failed to create experiment:", error)
    }
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-screen bg-background dark overflow-hidden flex items-center justify-center">
        <div className="text-lg text-gray-500 dark:text-gray-400">Loading...</div>
      </div>
    )
  }

  // Show home page when no experiments exist or no current experiment selected
  if (experiments.length === 0 || !currentExperiment) {
    return <HomePage 
      onNavigateToExperiment={() => {
        // No need to call createFirstExperiment here - HomePage already handles it
        // Component will re-render when the experiment is created
      }}
      onExperimentSelect={(experiment) => {
        selectExperiment(experiment)
        // Component will re-render with the selected experiment
      }}
    />
  }

  // Show normal app view when experiments exist
  return (
    <div className="h-screen bg-background dark overflow-hidden flex flex-col">
      <Title 
        experiments={experiments}
        selectedExperiment={currentExperiment}
        onExperimentSelect={selectExperiment}
        onExperimentCreated={handleExperimentCreated}
        onExperimentDelete={removeExperiment}
        experimentTitle={experimentTitle}
        onTitleChange={updateExperimentTitleWithSave}
      />
      
      {/* Enhanced main layout with better spacing and flexible ratios */}
      <div className="flex-1 grid gap-6 px-8 pb-8 pt-4 min-h-0 overflow-visible" style={{ 
        gridTemplateColumns: "1.6fr 2.2fr 1.2fr",
        gridTemplateRows: "1fr",
        minHeight: "0"
      }}>
        {/* Left Column - Plan Editor */}
        <div className="flex flex-col min-h-0 rounded-xl bg-gradient-to-b from-blue-50/80 to-blue-100/60 dark:from-blue-950/40 dark:to-blue-900/30 p-1 hover:shadow-lg transition-all duration-300 hover:scale-[1.01] overflow-hidden border border-blue-200/50 dark:border-blue-800/50">
          <div className="flex-1 min-h-0">
            <TextEditor value={editorText} onChange={updateEditorTextWithSave} />
          </div>
        </div>

        {/* Middle Column - Data Table and Visualization */}
        <div className="flex flex-col gap-8 min-h-0 overflow-visible py-2">
          <div className="flex-1 min-h-0 rounded-xl bg-gradient-to-br from-emerald-50/80 to-emerald-100/60 dark:from-emerald-950/40 dark:to-emerald-900/30 p-1 hover:shadow-lg transition-all duration-300 hover:scale-[1.01] overflow-hidden border border-emerald-200/50 dark:border-emerald-800/50">
            <DataTableViewer csvData={csvData} />
          </div>
          <div className="flex-1 min-h-0 rounded-xl bg-gradient-to-br from-purple-50/80 to-purple-100/60 dark:from-purple-950/40 dark:to-purple-900/30 p-1 hover:shadow-lg transition-all duration-300 hover:scale-[1.01] overflow-hidden border border-purple-200/50 dark:border-purple-800/50">
            <GraphViewer 
              htmlContent={visualizationHtml}
              onRefresh={refreshVisualization}
            />
          </div>
        </div>

        {/* Right Column - AI Chat */}
        <div className="flex flex-col min-h-0 rounded-xl bg-gradient-to-b from-indigo-50/80 to-indigo-100/60 dark:from-indigo-950/40 dark:to-indigo-900/30 p-1 hover:shadow-lg transition-all duration-300 hover:scale-[1.01] overflow-hidden border border-indigo-200/50 dark:border-indigo-800/50">
          <div className="flex-1 min-h-0">
            <AiChat 
              plan={editorText}
              csv={csvData}
              editorText={editorText} 
              onPlanChange={updateEditorTextWithSave}
              onVisualizationGenerated={updateVisualizationHtmlWithSave}
            />
          </div>
        </div>
      </div>
    </div>
  )
} 