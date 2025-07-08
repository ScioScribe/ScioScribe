import { FileText } from "lucide-react"

export function Title() {
  return (
    <div className="flex items-center gap-2 px-4 py-2">
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
  )
}
