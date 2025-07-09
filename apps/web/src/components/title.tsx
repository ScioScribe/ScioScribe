import { FileText } from "lucide-react"
import { ExperimentsDropdown } from "@/components/experiments-dropdown"
import { ExperimentTitle } from "@/components/experiment-title"
import type { Experiment } from "@/api/database"

interface TitleProps {
  experiments?: Experiment[]
  selectedExperiment?: Experiment | null
  onExperimentSelect?: (experiment: Experiment) => void
  onExperimentCreated?: () => void
  experimentTitle?: string
  onTitleChange?: (title: string) => void
}

export function Title({ experiments = [], selectedExperiment, onExperimentSelect, onExperimentCreated, experimentTitle, onTitleChange }: TitleProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2">
      {/* Left side - Logo and title */}
      <div className="flex items-center gap-2">
        <FileText className="h-5 w-5 text-blue-500" />
        <h1
          className="text-lg font-bold text-gray-900 dark:text-white"
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          }}
        >
          ScioScribe
        </h1>
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
        />
      </div>
    </div>
  )
}
