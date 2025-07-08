"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface Message {
  id: string
  content: string
  sender: "user" | "ai"
  timestamp: Date
}

export function AiChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm your AI assistant. How can I help you today?",
      sender: "ai",
      timestamp: new Date(Date.now() - 300000),
    },
    {
      id: "2",
      content: "Can you help me analyze the dashboard metrics?",
      sender: "user",
      timestamp: new Date(Date.now() - 240000),
    },
    {
      id: "3",
      content:
        "Of course! Your revenue is up 20.1% and user growth is strong at 180.1%. The monthly goal progress at 68% suggests you're on track for meeting your targets.",
      sender: "ai",
      timestamp: new Date(Date.now() - 180000),
    },
  ])

  const [inputValue, setInputValue] = useState("")
  const [selectedMode, setSelectedMode] = useState("plan")
  const [isTyping, setIsTyping] = useState(false)
  const [typingContent, setTypingContent] = useState("")
  const [showCursor, setShowCursor] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, typingContent])

  // Cursor blinking effect
  useEffect(() => {
    if (isTyping) {
      const interval = setInterval(() => {
        setShowCursor((prev) => !prev)
      }, 530)
      return () => clearInterval(interval)
    } else {
      setShowCursor(false)
    }
  }, [isTyping])

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
    setIsTyping(true)
    setTypingContent("")

    // Simulate streaming response
    const response = generateAiResponse(inputValue, selectedMode)
    let currentIndex = 0

    const typeResponse = () => {
      if (currentIndex < response.length) {
        setTypingContent(response.substring(0, currentIndex + 1))
        currentIndex++
        setTimeout(typeResponse, 20 + Math.random() * 30) // Variable typing speed
      } else {
        // Finished typing
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response,
          sender: "ai",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, aiMessage])
        setIsTyping(false)
        setTypingContent("")
      }
    }

    setTimeout(typeResponse, 500) // Initial delay
  }

  const generateAiResponse = (userInput: string, mode: string): string => {
    const responses = {
      plan: [
        "Let me help you create a plan for that. I'll break this down into actionable steps and timeline considerations.",
        "I can help you structure a comprehensive plan. Let's start by identifying the key objectives and milestones.",
        "Planning mode activated. I'll help you organize this into a clear, executable roadmap with priorities.",
      ],
      execute: [
        "Ready to execute! I'll provide specific implementation steps and code examples to get this done.",
        "Execution mode: Let me give you the exact commands, code, and actions needed to implement this.",
        "Time to build! I'll walk you through the implementation with concrete steps and best practices.",
      ],
      analysis: [
        "Let me analyze this data for you. I'll look for patterns, insights, and key metrics that matter.",
        "Analysis mode: I'll examine the trends, correlations, and provide data-driven insights.",
        "Analyzing your data now. I'll identify the key findings and actionable recommendations.",
      ],
    }

    const modeResponses = responses[mode as keyof typeof responses] || responses.plan
    return modeResponses[Math.floor(Math.random() * modeResponses.length)]
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
                <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">{message.content}</div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <div className="mb-4">
              <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
                {typingContent}
                {showCursor && <span className="bg-gray-700 dark:bg-gray-300 text-transparent select-none">█</span>}
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
            disabled={isTyping}
          />
        </div>
      </div>
    </Card>
  )
}
