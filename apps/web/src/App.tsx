import { useState } from 'react'
import { Title } from "@/components/title"
import { TextEditor } from "@/components/text-editor"
import { DataTableViewer } from "@/components/data-table-viewer"
import { GraphViewer } from "@/components/graph-viewer"
import { AiChat } from "@/components/ai-chat"

export default function Home() {
  const [editorText, setEditorText] = useState(`# Research Plan

## Objective
Define your research objective here...

## Data Sources
- List your data sources
- Include any constraints or limitations

## Analysis Steps
1. Data cleaning and preparation
2. Exploratory data analysis
3. Statistical analysis
4. Visualization and reporting

## Expected Outcomes
- Key metrics to track
- Insights to discover
- Decisions to inform`)

  return (
    <div className="h-screen bg-background dark overflow-hidden flex flex-col">
      <Title />
      <div className="flex-1 grid gap-4 px-4 pb-4" style={{ gridTemplateColumns: "1.7fr 2fr 1fr" }}>
        {/* Left Column */}
        <div className="h-full">
          <TextEditor value={editorText} onChange={setEditorText} />
        </div>

        {/* Middle Section - Upper and Lower Boxes */}
        <div className="flex flex-col gap-4 h-full">
          <div className="flex-1 min-h-0">
            <DataTableViewer />
          </div>
          <div className="flex-1 min-h-0">
            <GraphViewer />
          </div>
        </div>

        {/* AI Chat */}
        <div className="h-full">
          <AiChat 
            plan={editorText}
            editorText={editorText} 
            onPlanChange={setEditorText}
          />
        </div>
      </div>
    </div>
  )
}
