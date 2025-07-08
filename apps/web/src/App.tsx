import { Title } from "@/components/title"
import { TextEditor } from "@/components/text-editor"
import { DataTableViewer } from "@/components/data-table-viewer"
import { GraphViewer } from "@/components/graph-viewer"
import { AiChat } from "@/components/ai-chat"

export default function Home() {
  return (
    <div className="h-screen bg-background dark overflow-hidden flex flex-col">
      <Title />
      <div className="flex-1 grid gap-4 px-4 pb-4" style={{ gridTemplateColumns: "1.7fr 2fr 1fr" }}>
        {/* Left Column */}
        <div className="h-full">
          <TextEditor />
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
          <AiChat />
        </div>
      </div>
    </div>
  )
}
