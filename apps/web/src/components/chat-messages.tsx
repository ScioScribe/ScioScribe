/**
 * Chat Messages Component
 * 
 * This component displays the list of chat messages with proper scrolling,
 * loading states, typing indicators, and real-time WebSocket connection status.
 */

import { useEffect, useRef, useState } from "react"
import { ChatMessage } from "@/components/chat-message"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Wifi, WifiOff, Loader2, Zap, Clock, RefreshCw } from "lucide-react"
import type { Message } from "@/types/chat-types"

interface ChatMessagesProps {
  messages: Message[]
  isLoading: boolean
  selectedMode: string
  isConnected?: boolean
  connectionStatus?: string
  isTyping?: boolean
  typingText?: string
  lastActivity?: Date
  onRetryConnection?: () => void
}

export function ChatMessages({ 
  messages, 
  isLoading, 
  selectedMode,
  isConnected = false,
  connectionStatus = "disconnected",
  isTyping = false,
  typingText = "",
  lastActivity,
  onRetryConnection
}: ChatMessagesProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Auto-scroll to bottom when new messages arrive (only if user hasn't scrolled up)
  useEffect(() => {
    if (scrollAreaRef.current && autoScroll) {
      const scrollElement = scrollAreaRef.current
      const isNearBottom = scrollElement.scrollHeight - scrollElement.scrollTop <= scrollElement.clientHeight + 100
      
      if (isNearBottom) {
        scrollElement.scrollTop = scrollElement.scrollHeight
      }
    }
  }, [messages, isLoading, isTyping, autoScroll])

  // Handle scroll events to detect if user has scrolled up
  const handleScroll = () => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current
      const isNearBottom = scrollElement.scrollHeight - scrollElement.scrollTop <= scrollElement.clientHeight + 100
      setAutoScroll(isNearBottom)
    }
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Connection Status Bar */}
      <ConnectionStatusBar 
        isConnected={isConnected}
        connectionStatus={connectionStatus}
        selectedMode={selectedMode}
        lastActivity={lastActivity}
        onRetryConnection={onRetryConnection}
      />
      
      {/* Messages Container */}
      <div
        ref={scrollAreaRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-6 py-4"
        style={{
          fontFamily: '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          fontSize: "16px",
          lineHeight: "24px",
        }}
      >
        <div className="space-y-0">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <TypingIndicator selectedMode={selectedMode} typingText={typingText} />
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="mb-4">
              <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
                <LoadingIndicator selectedMode={selectedMode} />
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Scroll to bottom button (when user scrolled up) */}
      {!autoScroll && (
        <div className="absolute bottom-4 right-4">
          <button
            onClick={() => {
              if (scrollAreaRef.current) {
                scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
                setAutoScroll(true)
              }
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white rounded-full p-2 shadow-lg transition-all duration-200"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * Connection Status Bar Component
 */
interface ConnectionStatusBarProps {
  isConnected: boolean
  connectionStatus: string
  selectedMode: string
  lastActivity?: Date
  onRetryConnection?: () => void
}

function ConnectionStatusBar({ isConnected, connectionStatus, selectedMode, lastActivity, onRetryConnection }: ConnectionStatusBarProps) {
  const [timeAgo, setTimeAgo] = useState("")

  // Update time ago periodically
  useEffect(() => {
    const updateTimeAgo = () => {
      if (lastActivity) {
        const now = new Date()
        const diffMs = now.getTime() - lastActivity.getTime()
        const diffSecs = Math.floor(diffMs / 1000)
        const diffMins = Math.floor(diffSecs / 60)
        
        const newTimeAgo = diffSecs < 60 
          ? `${diffSecs}s ago`
          : diffMins < 60 
            ? `${diffMins}m ago`
            : ">1h ago"
        
        // Only update state if the value actually changed
        setTimeAgo(prev => prev === newTimeAgo ? prev : newTimeAgo)
      }
    }

    updateTimeAgo()
    const interval = setInterval(updateTimeAgo, 5000) // Update every 5 seconds
    
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastActivity?.getTime()]) // Use primitive value instead of Date object

  const getStatusColor = () => {
    if (selectedMode !== "plan") return "gray" // Only show for planning mode
    
    switch (connectionStatus) {
      case "connected":
        return "green"
      case "connecting":
        return "yellow"
      case "reconnecting":
        return "orange"
      case "disconnected":
      case "error":
        return "red"
      default:
        return "gray"
    }
  }

  const getStatusIcon = () => {
    if (selectedMode !== "plan") return null
    
    switch (connectionStatus) {
      case "connected":
        return <Wifi className="h-3 w-3" />
      case "connecting":
      case "reconnecting":
        return <Loader2 className="h-3 w-3 animate-spin" />
      case "disconnected":
      case "error":
        return <WifiOff className="h-3 w-3" />
      default:
        return <Clock className="h-3 w-3" />
    }
  }

  const getStatusText = () => {
    if (selectedMode !== "plan") {
      return `${selectedMode} mode - Real-time updates available`
    }
    
    switch (connectionStatus) {
      case "connected":
        return `WebSocket connected - Real-time updates ${timeAgo ? `(${timeAgo})` : ""}`
      case "connecting":
        return "Connecting to planning server..."
      case "reconnecting":
        return "Reconnecting to planning server..."
      case "disconnected":
        return "Disconnected from planning server"
      case "error":
        return "Connection error - Retrying..."
      default:
        return `Planning mode - ${connectionStatus}`
    }
  }

  if (selectedMode !== "plan" && !isConnected) {
    return null // Don't show status bar for non-planning modes when not relevant
  }

  return (
    <div className="flex-shrink-0 px-6 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge 
            variant={getStatusColor() === "green" ? "default" : "secondary"}
            className={`text-xs flex items-center gap-1 ${
              getStatusColor() === "green" ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" :
              getStatusColor() === "yellow" ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200" :
              getStatusColor() === "orange" ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" :
              getStatusColor() === "red" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
              "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
            }`}
          >
            {getStatusIcon()}
            <span>{getStatusText()}</span>
          </Badge>
        </div>
        
        <div className="flex items-center gap-2">
          {selectedMode === "plan" && isConnected && (
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Zap className="h-3 w-3" />
              <span>Live</span>
            </div>
          )}
          
          {/* Retry button for failed connections */}
          {selectedMode === "plan" && connectionStatus === "failed" && onRetryConnection && (
            <Button
              onClick={onRetryConnection}
              size="sm"
              variant="outline"
              className="h-6 px-2 text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Typing Indicator Component
 */
interface TypingIndicatorProps {
  selectedMode: string
  typingText?: string
}

function TypingIndicator({ selectedMode, typingText }: TypingIndicatorProps) {
  const [dots, setDots] = useState(".")

  // Animate dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => {
        switch (prev) {
          case ".": return ".."
          case "..": return "..."
          case "...": return "."
          default: return "."
        }
      })
    }, 500)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="mb-4">
      <div className="text-gray-500 dark:text-gray-400 mt-1 pl-4 flex items-center gap-2">
        <div className="flex items-center gap-1">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
          </div>
        </div>
        <span className="text-sm italic">
          {typingText || `AI is ${selectedMode === "plan" ? "planning" : selectedMode === "execute" ? "processing" : "analyzing"}${dots}`}
        </span>
      </div>
    </div>
  )
}

/**
 * Loading Indicator Component
 */
interface LoadingIndicatorProps {
  selectedMode: string
}

function LoadingIndicator({ selectedMode }: LoadingIndicatorProps) {
  const loadingText = getLoadingText(selectedMode)
  
  return (
    <div className="flex items-center gap-2">
      <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500"></div>
      <span className="text-sm">{loadingText}</span>
    </div>
  )
}

/**
 * Get loading text based on selected mode
 */
function getLoadingText(selectedMode: string): string {
  switch (selectedMode) {
    case "plan":
      return "Planning your experiment..."
    case "execute":
      return "Processing your data..."
    case "analysis":
      return "Analyzing your request..."
    default:
      return "Processing..."
  }
} 