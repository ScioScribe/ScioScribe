/**
 * Chat Messages Component
 * 
 * This component displays the list of chat messages with enhanced auto-scroll,
 * loading states, and real-time WebSocket connection status.
 */

import { useEffect, useRef, useState, useCallback } from "react"
import { ChatMessage } from "@/components/chat-message"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Wifi, WifiOff, Loader2, Zap, Clock, RefreshCw, ChevronDown } from "lucide-react"
import type { Message } from "@/types/chat-types"

interface ChatMessagesProps {
  messages: Message[]
  isLoading: boolean
  selectedMode: string
  isConnected?: boolean
  connectionStatus?: string
  lastActivity?: Date
  onRetryConnection?: () => void
}

export function ChatMessages({ 
  messages, 
  isLoading, 
  selectedMode,
  isConnected = false,
  connectionStatus = "disconnected",
  lastActivity,
  onRetryConnection
}: ChatMessagesProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [isScrolling, setIsScrolling] = useState(false)
  const scrollTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined)
  const lastMessageCountRef = useRef(messages.length)

  // Enhanced auto-scroll to bottom with smooth behavior
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current
      // Use requestAnimationFrame for smoother scrolling during animations
      requestAnimationFrame(() => {
        scrollElement.scrollTo({
          top: scrollElement.scrollHeight,
          behavior
        })
      })
    }
  }, [])

  // Auto-scroll to bottom when new messages arrive or loading state changes
  useEffect(() => {
    if (autoScroll) {
      // Check if new messages were added
      const isNewMessage = messages.length > lastMessageCountRef.current
      lastMessageCountRef.current = messages.length
      
      // Use smooth scrolling for new messages, instant for initial load
      const behavior = isNewMessage && messages.length > 1 ? "smooth" : "auto"
      scrollToBottom(behavior)
    }
  }, [messages, isLoading, autoScroll, scrollToBottom])

  // Enhanced observer for typewriter animation and content changes
  useEffect(() => {
    const scrollElement = scrollAreaRef.current
    const contentElement = messagesContainerRef.current
    
    if (!scrollElement || !contentElement) return

    // MutationObserver to catch text content changes (typewriter animation)
    const mutationObserver = new MutationObserver(() => {
      if (autoScroll) {
        // Use instant scroll for continuous updates during typewriter animation
        requestAnimationFrame(() => {
          scrollElement.scrollTop = scrollElement.scrollHeight
        })
      }
    })

    // Observe text changes in all descendant nodes
    mutationObserver.observe(contentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      characterDataOldValue: true
    })

    // ResizeObserver for layout changes
    const resizeObserver = new ResizeObserver(() => {
      if (autoScroll) {
        requestAnimationFrame(() => {
          scrollElement.scrollTop = scrollElement.scrollHeight
        })
      }
    })

    // Observe the content container, not the scroll container
    resizeObserver.observe(contentElement)

    return () => {
      mutationObserver.disconnect()
      resizeObserver.disconnect()
    }
  }, [autoScroll])

  // Handle scroll events with debouncing to detect if user has scrolled up
  const handleScroll = useCallback(() => {
    if (!scrollAreaRef.current) return
    
    const scrollElement = scrollAreaRef.current
    const { scrollTop, scrollHeight, clientHeight } = scrollElement
    
    // Check if user is near the bottom (within 100px threshold for better UX)
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
    
    // Update auto-scroll state
    setAutoScroll(isNearBottom)
    
    // Show/hide scroll button based on scroll position
    const shouldShowButton = scrollHeight - scrollTop - clientHeight > 200
    setShowScrollButton(shouldShowButton)
    
    // Set scrolling state for visual feedback
    setIsScrolling(true)
    
    // Clear previous timeout
    if (scrollTimeoutRef.current !== undefined) {
      clearTimeout(scrollTimeoutRef.current)
    }
    
    // Reset scrolling state after a delay
    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrolling(false)
    }, 150)
  }, [])

  // Cleanup scroll timeout on unmount
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current !== undefined) {
        clearTimeout(scrollTimeoutRef.current)
      }
    }
  }, [])

  // Handle scroll to bottom button click
  const handleScrollToBottom = useCallback(() => {
    scrollToBottom("smooth")
    setAutoScroll(true)
  }, [scrollToBottom])

  return (
    <div className="flex-1 flex flex-col min-h-0 relative">
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
        className="flex-1 overflow-y-auto px-4 py-3 transition-all duration-200"
        style={{
          fontFamily: '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          fontSize: "13px",
          lineHeight: "18px",
          scrollBehavior: "smooth"
        }}
      >
        <div ref={messagesContainerRef} className="space-y-0 min-h-full">
          {messages.map((message, index) => (
            <ChatMessage 
              key={message.id} 
              message={message} 
              enableTypewriter={
                message.sender === "ai" && 
                !message.isHtml && 
                index === messages.length - 1 // Only animate the latest AI message
              }
            />
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="mb-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
              <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
                <LoadingIndicator selectedMode={selectedMode} />
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Enhanced Scroll to bottom button */}
      {showScrollButton && (
        <div className="absolute bottom-4 right-4 z-10">
          <Button
            onClick={handleScrollToBottom}
            size="sm"
            variant="secondary"
            className={`
              bg-white/90 dark:bg-gray-800/90 
              hover:bg-white dark:hover:bg-gray-800 
              border border-gray-200 dark:border-gray-700
              shadow-lg backdrop-blur-sm
              transition-all duration-200 ease-in-out
              hover:scale-105 active:scale-95
              ${autoScroll ? "opacity-50" : "opacity-100"}
            `}
          >
            <ChevronDown className="h-4 w-4 mr-1" />
            <span className="text-sm">Scroll to bottom</span>
          </Button>
        </div>
      )}
      
      {/* Scroll indicator */}
      {!autoScroll && (
        <div className="absolute bottom-20 right-4 z-10">
          <div className="bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-200 px-3 py-1 rounded-full text-xs font-medium shadow-sm border border-amber-200 dark:border-amber-700">
            Auto-scroll paused
          </div>
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