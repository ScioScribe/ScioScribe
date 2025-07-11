import { useEffect } from 'react'
import { Title } from "@/components/title"
import { TextEditor } from "@/components/text-editor"
import { DataTableViewer } from "@/components/data-table-viewer"
import { GraphViewer } from "@/components/graph-viewer"
import { AiChat } from "@/components/ai-chat"
import { Button } from "@/components/ui/button"
import { useExperimentStore } from "@/stores"

export default function Home() {
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
    createFirstExperiment,
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

  // Show loading state
  if (isLoading) {
    return (
      <div className="h-screen bg-background dark overflow-hidden flex flex-col">
        <Title 
          experiments={[]}
          selectedExperiment={null}
          onExperimentSelect={selectExperiment}
          onExperimentCreated={loadExperiments}
          onExperimentDelete={removeExperiment}
          experimentTitle="Untitled Experiment"
          onTitleChange={updateExperimentTitleWithSave}
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
          onExperimentSelect={selectExperiment}
          onExperimentCreated={loadExperiments}
          onExperimentDelete={removeExperiment}
          experimentTitle="Untitled Experiment"
          onTitleChange={updateExperimentTitleWithSave}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Button
              onClick={createFirstExperiment}
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
    <div className="h-full bg-background dark overflow-hidden flex flex-col">
      <Title 
        experiments={experiments}
        selectedExperiment={currentExperiment}
        onExperimentSelect={selectExperiment}
        onExperimentCreated={loadExperiments}
        onExperimentDelete={removeExperiment}
        experimentTitle={experimentTitle}
        onTitleChange={updateExperimentTitleWithSave}
      />
      <div className="flex-1 grid gap-4 px-4 pb-4" style={{ gridTemplateColumns: "1.7fr 2fr 1fr" }}>
        {/* Left Column */}
        <div className="h-[95vh]">
          <TextEditor value={editorText} onChange={updateEditorTextWithSave} />
        </div>

        {/* Middle Section - Upper and Lower Boxes */}
        <div className="flex flex-col gap-4 h-full">
          <div className="h-[47vh] min-h-0">
            <DataTableViewer csvData={csvData} />
          </div>
          <div className="h-[47vh] min-h-0">
            <GraphViewer 
              htmlContent={visualizationHtml}
              onRefresh={refreshVisualization}
            />
          </div>
        </div>

        {/* AI Chat */}
        <div className="h-[95vh]">
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
  )
}
