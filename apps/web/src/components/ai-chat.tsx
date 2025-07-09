"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { generateVisualization } from "@/api/analysis"
import { SAMPLE_PROMPTS } from "@/data/placeholder"
import { Lightbulb, Send } from "lucide-react"

interface Message {
  id: string
  content: string
  sender: "user" | "ai"
  timestamp: Date
  isHtml?: boolean
}

interface AiChatProps {
  plan?: string
  csv?: string
  editorText?: string
  onPlanChange?: (text: string) => void
  onVisualizationGenerated?: (html: string) => void
}

export function AiChat({ plan = "", csv = "", editorText = "", onPlanChange, onVisualizationGenerated }: AiChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Welcome to ScioScribe! I can help you analyze your iris dataset and create visualizations. Try asking me to create charts or analyze the data patterns.",
      sender: "ai",
      timestamp: new Date(),
    }
  ])

  const [inputValue, setInputValue] = useState("")
  const [selectedMode, setSelectedMode] = useState("analysis")
  const [isLoading, setIsLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const currentInput = inputValue
    setInputValue("")
    setIsLoading(true)

    if (selectedMode === "analysis") {
      // Call generateVisualization API for analysis mode
      try {
        const requestBody = {
          prompt: currentInput,
          plan: plan,
          csv: csv,
        }
        
        // Debug: Print request body
        console.log("🔍 generateVisualization Request Body:", requestBody)
        
        const response = await generateVisualization(requestBody)

        // Print response body to console for debugging
        console.log("🔍 API Response Body:", JSON.stringify(response, null, 2))
        console.log("📊 HTML Content Length:", response.html?.length || 0)
        console.log("💬 Message Content:", response.message)

        // Add the explanatory message first
        const textMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.message,
          sender: "ai",
          timestamp: new Date(),
        }
        
        // Add the HTML visualization response
        const aiMessage: Message = {
          id: (Date.now() + 2).toString(),
          content: response.html,
          sender: "ai",
          timestamp: new Date(),
          isHtml: true,
        }
        
        setMessages((prev) => [...prev, textMessage, aiMessage])
        onVisualizationGenerated?.(response.html)
      } catch (error) {
        // Enhanced error logging
        console.error("🚨 Visualization generation error:", error)
        console.log("📍 Error details:", {
          errorMessage: error instanceof Error ? error.message : 'Unknown error',
          errorType: typeof error,
          errorObject: error
        })
        
        // Handle error
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `Error generating visualization: ${error instanceof Error ? error.message : 'Unknown error'}\n\nTip: Make sure the backend server is running on localhost:8000`,
          sender: "ai",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMessage])
      }
    } else {
      // For plan and execute modes, show a message that functionality is not implemented yet
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `${selectedMode} mode functionality is not implemented yet. Please use analysis mode for visualization generation.\n\nTry asking me to:\n• Create scatter plots or box plots\n• Show correlations between features\n• Analyze species differences\n• Generate statistical summaries`,
        sender: "ai",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, aiMessage])
    }
    
    setIsLoading(false)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const getSuggestionsForMode = () => {
    switch (selectedMode) {
      case "analysis":
        return SAMPLE_PROMPTS.visualization.concat(SAMPLE_PROMPTS.insights)
      case "plan":
        return SAMPLE_PROMPTS.analysis
      default:
        return SAMPLE_PROMPTS.visualization
    }
  }

  return (
    <Card className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800">
      {/* Chat History */}
      <div
        ref={scrollAreaRef}
        className="flex-1 overflow-y-auto px-6 py-4"
        style={{
          fontFamily:
            '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          fontSize: "16px",
          lineHeight: "24px",
        }}
      >
        <div className="space-y-0">
          {messages.map((message) => (
            <div key={message.id} className="mb-4">
              {message.sender === "user" && (
                <div className="text-gray-900 dark:text-gray-100 font-bold">
                  <span className="text-blue-500 mr-2">→</span>
                  {message.content}
                </div>
              )}
              {message.sender === "ai" && (
                <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
                  {message.isHtml ? (
                    <div dangerouslySetInnerHTML={{ __html: message.content }} />
                  ) : (
                    <pre className="whitespace-pre-wrap font-inherit">
                      {message.content}
                    </pre>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="mb-4">
              <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
                Generating visualization...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Suggestions Panel */}
      {showSuggestions && (
        <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 p-3">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1">
            <Lightbulb className="h-3 w-3" />
            Try these suggestions:
          </div>
          <div className="space-y-1">
            {getSuggestionsForMode().slice(0, 3).map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                className="block w-full text-left text-xs p-2 rounded bg-white dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Mode Selector and Input Bar */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-transparent">
        {/* Mode Dropdown */}
        <div className="px-6 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <Select value={selectedMode} onValueChange={setSelectedMode}>
            <SelectTrigger className="w-32 h-6 text-xs bg-transparent border-0 focus:ring-0 dark:text-gray-300">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="dark:bg-gray-800 dark:border-gray-700">
              <SelectItem value="plan" className="text-xs dark:text-gray-300 dark:focus:bg-gray-700">
                plan
              </SelectItem>
              <SelectItem value="execute" className="text-xs dark:text-gray-300 dark:focus:bg-gray-700">
                execute
              </SelectItem>
              <SelectItem value="analysis" className="text-xs dark:text-gray-300 dark:focus:bg-gray-700">
                analysis
              </SelectItem>
            </SelectContent>
          </Select>
          
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => setShowSuggestions(!showSuggestions)}
          >
            <Lightbulb className="h-3 w-3" />
          </Button>
        </div>

        {/* Input */}
        <div className="px-6 py-3 flex items-center gap-2">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedMode === "analysis" ? "Ask me to create charts or analyze the iris data..." : "Ask me anything..."}
            className="flex-1 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-2 focus-visible:ring-0 focus-visible:outline-none text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
            style={{
              fontFamily:
                '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: "14px",
              lineHeight: "20px",
            }}
            disabled={isLoading}
          />
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            size="sm"
            className="h-8 px-3"
          >
            <Send className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </Card>
  )
}
