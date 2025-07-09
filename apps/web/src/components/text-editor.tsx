import type React from "react"

import { useState, useRef, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { FileText } from "lucide-react"

interface TextEditorProps {
  value: string
  onChange: (content: string) => void
}

export function TextEditor({ value, onChange }: TextEditorProps) {
  const [content, setContent] = useState(value)

  const [lineCount, setLineCount] = useState(1)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lineNumbersRef = useRef<HTMLDivElement>(null)

  // Sync internal state with prop changes
  useEffect(() => {
    setContent(value)
  }, [value])

  const updateLineNumbers = useCallback(() => {
    const lines = content.split("\n").length
    setLineCount(lines)
  }, [content])

  useEffect(() => {
    updateLineNumbers()
  }, [content, updateLineNumbers])

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value
    setContent(newContent)
    updateLineNumbers()
    
    // Notify parent component of content change
    onChange(newContent)
  }

  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = e.currentTarget.scrollTop
    }
  }

  const generateLineNumbers = () => {
    return Array.from({ length: lineCount }, (_, i) => i + 1)
  }

  return (
    <Card className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800">
      <CardHeader className="flex-shrink-0 pb-2">
        <CardTitle className="text-base flex items-center gap-2 dark:text-white">
          <FileText className="h-4 w-4" />
          Plan
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex min-h-0 p-0">
        {/* Line Numbers */}
        <div
          ref={lineNumbersRef}
          className="flex-shrink-0 w-12 bg-gray-50 dark:bg-gray-800 border-r dark:border-gray-700 overflow-hidden"
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            fontSize: "12px",
            lineHeight: "18px",
          }}
        >
          <div className="py-2 px-2 text-right">
            {generateLineNumbers().map((lineNum) => (
              <div
                key={lineNum}
                className="text-gray-400 dark:text-gray-500 select-none"
                style={{ height: "18px", lineHeight: "18px" }}
              >
                {lineNum}
              </div>
            ))}
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 min-h-0 relative">
          <Textarea
            ref={textareaRef}
            value={content}
            onChange={handleContentChange}
            onScroll={handleScroll}
            placeholder="Start coding..."
            className="h-full w-full resize-none border-0 focus-visible:ring-0 rounded-none bg-transparent dark:bg-gray-900 dark:text-gray-100 p-2"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: "12px",
              lineHeight: "18px",
              minHeight: "100%",
              outline: "none",
              whiteSpace: "pre",
              wordWrap: "break-word",
              tabSize: 2,
            }}
            spellCheck={false}
          />
        </div>
      </CardContent>
    </Card>
  )
}
