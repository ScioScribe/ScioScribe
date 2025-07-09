import { useState } from 'react'
import { Title } from "@/components/title"
import { TextEditor } from "@/components/text-editor"
import { DataTableViewer } from "@/components/data-table-viewer"
import { GraphViewer } from "@/components/graph-viewer"
import { AiChat } from "@/components/ai-chat"
import { IRIS_CSV_DATA, IRIS_EXPERIMENT_PLAN } from "@/data/placeholder"

export default function Home() {
  const [editorText, setEditorText] = useState(IRIS_EXPERIMENT_PLAN)
  const [visualizationHtml, setVisualizationHtml] = useState<string>("")

  const handleVisualizationGenerated = (html: string) => {
    setVisualizationHtml(html)
  }

  const handleRefreshVisualization = () => {
    // Optionally clear or regenerate visualization
    setVisualizationHtml("")
  }

  return (
    <div className="h-screen bg-background dark overflow-hidden flex flex-col">
      <Title />
      <div className="flex-1 grid gap-4 px-4 pb-4" style={{ gridTemplateColumns: "1.7fr 2fr 1fr" }}>
        {/* Left Column */}
        <div className="h-[95vh]">
          <TextEditor value={editorText} onChange={setEditorText} />
        </div>

        {/* Middle Section - Upper and Lower Boxes */}
        <div className="flex flex-col gap-4 h-full">
          <div className="h-[47vh] min-h-0">
            <DataTableViewer csvData={IRIS_CSV_DATA} />
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
            csv={IRIS_CSV_DATA}
            editorText={editorText} 
            onPlanChange={setEditorText}
            onVisualizationGenerated={handleVisualizationGenerated}
          />
        </div>
      </div>
    </div>
  )
}
