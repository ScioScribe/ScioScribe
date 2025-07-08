"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { generateChart } from "@/api/analysis"

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
}

export function AiChat({ plan = "", csv = "", editorText = "", onPlanChange }: AiChatProps) {
  const [messages, setMessages] = useState<Message[]>([])

  const [inputValue, setInputValue] = useState("")
  const [selectedMode, setSelectedMode] = useState("plan")
  const [isLoading, setIsLoading] = useState(false)
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

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsLoading(true)

    if (selectedMode === "analysis") {
      // Call generateChart API for analysis mode
      try {
        const requestBody = {
          prompt: inputValue,
          plan: plan,
          csv: csv,
        }
        
        // Debug: Print request body
        console.log("🔍 generateChart Request Body:", requestBody)
        
        const response = await generateChart(requestBody)

        // Add the HTML chart response
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.html,
          sender: "ai",
          timestamp: new Date(),
          isHtml: true,
        }
        setMessages((prev) => [...prev, aiMessage])
      } catch (error) {
        // Enhanced error logging
        console.error("🚨 Chart generation error:", error)
        console.log("📍 Error details:", {
          errorMessage: error instanceof Error ? error.message : 'Unknown error',
          errorType: typeof error,
          errorObject: error
        })
        
        // Handle error
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `Error generating chart: ${error instanceof Error ? error.message : 'Unknown error'}`,
          sender: "ai",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMessage])
      }
    } else {
      // For plan and execute modes, show a message that functionality is not implemented yet
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `${selectedMode} mode functionality is not implemented yet. Please use analysis mode for chart generation.`,
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
                    message.content
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="mb-4">
              <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
                Generating chart...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mode Selector and Input Bar */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-transparent">
        {/* Mode Dropdown */}
        <div className="px-6 py-2 border-b border-gray-200 dark:border-gray-700">
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
        </div>

        {/* Input */}
        <div className="px-6 py-3">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything..."
            className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-2 focus-visible:ring-0 focus-visible:outline-none text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
            style={{
              fontFamily:
                '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: "14px",
              lineHeight: "20px",
            }}
            disabled={isLoading}
          />
        </div>
      </div>
    </Card>
  )
}
