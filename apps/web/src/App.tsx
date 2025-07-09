import { useState, useEffect } from 'react'
import { Title } from "@/components/title"
import { TextEditor } from "@/components/text-editor"
import { DataTableViewer } from "@/components/data-table-viewer"
import { GraphViewer } from "@/components/graph-viewer"
import { AiChat } from "@/components/ai-chat"
import { Button } from "@/components/ui/button"
import { IRIS_CSV_DATA, IRIS_EXPERIMENT_PLAN } from "@/data/placeholder"
import type { Experiment } from "@/api/database"
import { getExperiments, createExperiment, updateExperimentPlan, updateExperimentHtml, updateExperimentCsv, updateExperimentTitle } from "@/api/database"

export default function Home() {
  const [currentExperiment, setCurrentExperiment] = useState<Experiment | null>(null)
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [experimentTitle, setExperimentTitle] = useState("Untitled Experiment")
  const [editorText, setEditorText] = useState(IRIS_EXPERIMENT_PLAN)
  const [csvData, setCsvData] = useState(IRIS_CSV_DATA)
  const [visualizationHtml, setVisualizationHtml] = useState<string>("")

  // Load experiments on component mount
  useEffect(() => {
    loadExperiments()
  }, [])

  const loadExperiments = async () => {
    setIsLoading(true)
    try {
      const data = await getExperiments()
      setExperiments(data)
      
      // If experiments exist, load the first one
      if (data.length > 0) {
        handleExperimentSelect(data[0])
      }
    } catch (error) {
      console.error("Failed to load experiments:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateFirstExperiment = async () => {
    try {
      const newExperiment = await createExperiment({
        title: "Untitled Experiment",
        experimental_plan: IRIS_EXPERIMENT_PLAN,
        csv_data: IRIS_CSV_DATA,
        visualization_html: ""
      })
      
      // Reload experiments and select the new one
      await loadExperiments()
      handleExperimentSelect(newExperiment)
    } catch (error) {
      console.error("Failed to create experiment:", error)
    }
  }

  const handleExperimentSelect = (experiment: Experiment) => {
    console.log("Selected experiment:", experiment)
    setCurrentExperiment(experiment)
    
    // Update the application state with experiment data
    setExperimentTitle(experiment.title || "Untitled Experiment")
    
    if (experiment.experimental_plan) {
      setEditorText(experiment.experimental_plan)
    }
    if (experiment.csv_data) {
      setCsvData(experiment.csv_data)
    }
    if (experiment.visualization_html) {
      setVisualizationHtml(experiment.visualization_html)
    }
  }

  const handleEditorTextChange = async (text: string) => {
    setEditorText(text)
    
    // Auto-save to database if experiment is selected
    if (currentExperiment) {
      try {
        await updateExperimentPlan(currentExperiment.id, text)
        console.log("Plan updated in database")
      } catch (error) {
        console.error("Failed to update plan:", error)
      }
    }
  }

  const handleVisualizationGenerated = async (html: string) => {
    setVisualizationHtml(html)
    
    // Auto-save to database if experiment is selected
    if (currentExperiment) {
      try {
        await updateExperimentHtml(currentExperiment.id, html)
        console.log("Visualization updated in database")
      } catch (error) {
        console.error("Failed to update visualization:", error)
      }
    }
  }

  const handleTitleChange = async (title: string) => {
    setExperimentTitle(title)
    
    // Auto-save to database if experiment is selected
    if (currentExperiment) {
      try {
        const updatedExperiment = await updateExperimentTitle(currentExperiment.id, title)
        
        // Update the current experiment with the new title
        setCurrentExperiment(updatedExperiment)
        
        // Update the experiments array to reflect the new title
        setExperiments(prevExperiments => 
          prevExperiments.map(exp => 
            exp.id === currentExperiment.id 
              ? { ...exp, title: title, updated_at: updatedExperiment.updated_at }
              : exp
          )
        )
        
        console.log("Title updated in database")
      } catch (error) {
        console.error("Failed to update title:", error)
      }
    }
  }

  const handleRefreshVisualization = () => {
    // Optionally clear or regenerate visualization
    setVisualizationHtml("")
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-screen bg-background dark overflow-hidden flex flex-col">
        <Title 
          experiments={[]}
          selectedExperiment={null}
          onExperimentSelect={handleExperimentSelect}
          onExperimentCreated={loadExperiments}
          experimentTitle="Untitled Experiment"
          onTitleChange={handleTitleChange}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-lg text-gray-500 dark:text-gray-400">Loading...</div>
        </div>
      </div>
    )
  }

  // Show empty state when no experiments exist
  if (experiments.length === 0) {
    return (
      <div className="h-screen bg-background dark overflow-hidden flex flex-col">
        <Title 
          experiments={[]}
          selectedExperiment={null}
          onExperimentSelect={handleExperimentSelect}
          onExperimentCreated={loadExperiments}
          experimentTitle="Untitled Experiment"
          onTitleChange={handleTitleChange}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Button
              onClick={handleCreateFirstExperiment}
              className="px-8 py-3 text-lg"
              style={{
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              }}
            >
              Create Experiment
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Show normal app view when experiments exist
  return (
    <div className="h-screen bg-background dark overflow-hidden flex flex-col">
      <Title 
        experiments={experiments}
        selectedExperiment={currentExperiment}
        onExperimentSelect={handleExperimentSelect}
        onExperimentCreated={loadExperiments}
        experimentTitle={experimentTitle}
        onTitleChange={handleTitleChange}
      />
      <div className="flex-1 grid gap-4 px-4 pb-4" style={{ gridTemplateColumns: "1.7fr 2fr 1fr" }}>
        {/* Left Column */}
        <div className="h-[95vh]">
          <TextEditor value={editorText} onChange={handleEditorTextChange} />
        </div>

        {/* Middle Section - Upper and Lower Boxes */}
        <div className="flex flex-col gap-4 h-full">
          <div className="h-[47vh] min-h-0">
            <DataTableViewer csvData={csvData} />
          </div>
          <div className="h-[47vh] min-h-0">
            <GraphViewer 
              htmlContent={visualizationHtml}
              onRefresh={handleRefreshVisualization}
            />
          </div>
        </div>

        {/* AI Chat */}
        <div className="h-[95vh]">
          <AiChat 
            plan={editorText}
            csv={csvData}
            editorText={editorText} 
            onPlanChange={handleEditorTextChange}
            onVisualizationGenerated={handleVisualizationGenerated}
          />
        </div>
      </div>
    </div>
  )
}
