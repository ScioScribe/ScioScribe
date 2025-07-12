import type React from "react"

import { useState, useRef, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { FileText, CornerDownRight } from "lucide-react"

interface TextEditorProps {
  value: string
  onChange: (content: string) => void
}

export function TextEditor({ value, onChange }: TextEditorProps) {
  const [content, setContent] = useState(value)
  const [lineCount, setLineCount] = useState(1)
  const [wrappedLines, setWrappedLines] = useState<number[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lineNumbersRef = useRef<HTMLDivElement>(null)

  // Sync internal state with prop changes
  useEffect(() => {
    setContent(value)
  }, [value])

  const updateLineNumbers = useCallback(() => {
    const lines = content.split("\n").length
    setLineCount(lines)
    
    // Calculate wrapped lines
    if (textareaRef.current) {
      const textarea = textareaRef.current
      const wrappedLineIndices: number[] = []
      
      // Get the computed line height
      const computedStyle = window.getComputedStyle(textarea)
      const lineHeight = parseInt(computedStyle.lineHeight || "18")
      
      // Calculate which lines are wrapped based on scroll height
      for (let i = 0; i < lines; i++) {
        const lineContent = content.split("\n")[i] || ""
        const tempDiv = document.createElement("div")
        tempDiv.style.width = `${textarea.clientWidth}px`
        tempDiv.style.font = computedStyle.font
        tempDiv.style.whiteSpace = "pre-wrap"
        tempDiv.style.wordWrap = "break-word"
        tempDiv.textContent = lineContent
        
        document.body.appendChild(tempDiv)
        const height = tempDiv.offsetHeight
        document.body.removeChild(tempDiv)
        
        if (height > lineHeight) {
          wrappedLineIndices.push(i + 1) // 1-based line numbers
        }
      }
      
      setWrappedLines(wrappedLineIndices)
    }
  }, [content])

  useEffect(() => {
    updateLineNumbers()
    // Add resize listener to recalculate wrapped lines on container resize
    const resizeObserver = new ResizeObserver(() => {
      updateLineNumbers()
    })
    
    if (textareaRef.current) {
      resizeObserver.observe(textareaRef.current)
    }
    
    return () => {
      resizeObserver.disconnect()
    }
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
    <Card className="h-full flex flex-col shadow-lg border-0 bg-card/95 backdrop-blur-sm">
      <CardHeader className="flex-shrink-0 pb-3 px-4 pt-4 border-b border-border/50">
        <CardTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
          <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          Plan
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex min-h-0 p-0 bg-gradient-to-b from-card to-muted/20">
        {/* Line Numbers */}
        <div
          ref={lineNumbersRef}
          className="flex-shrink-0 w-12 bg-muted/40 border-r border-border/50 overflow-hidden backdrop-blur-sm"
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            fontSize: "12px",
            lineHeight: "18px",
          }}
        >
          <div className="py-3 px-2 text-right">
            {generateLineNumbers().map((lineNum) => {
              // Skip rendering line numbers for wrapped lines
              if (wrappedLines.includes(lineNum)) {
                return (
                  <div
                    key={lineNum}
                    className="flex items-center justify-end gap-1 text-muted-foreground/40 select-none"
                    style={{ height: "18px", lineHeight: "18px" }}
                  >
                    <CornerDownRight className="h-3 w-3 opacity-50" />
                  </div>
                );
              }
              
              return (
                <div
                  key={lineNum}
                  className="flex items-center justify-end gap-1 text-muted-foreground/60 select-none hover:text-muted-foreground transition-colors"
                  style={{ height: "18px", lineHeight: "18px" }}
                >
                  {lineNum}
                </div>
              );
            })}
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 min-h-0 relative">
          <Textarea
            ref={textareaRef}
            value={content}
            onChange={handleContentChange}
            onScroll={handleScroll}
            placeholder="Start writing your experiment plan..."
            className="h-full w-full resize-none border-0 focus-visible:ring-0 rounded-none bg-transparent text-foreground placeholder:text-muted-foreground/50 p-3 transition-all duration-200 focus:bg-background/50"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: "12px",
              lineHeight: "18px",
              minHeight: "100%",
              outline: "none",
              whiteSpace: "pre-wrap",
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
