/**
 * Chat Messages Component
 * 
 * This component displays the list of chat messages with enhanced auto-scroll,
 * loading states, and real-time WebSocket connection status.
 */

import { useEffect, useRef, useState, useCallback } from "react"
import { ChatMessage } from "@/components/chat-message"
import { Button } from "@/components/ui/button"
import { ChevronDown } from "lucide-react"
import { ThinkingIndicator } from "@/components/enhanced-message-display"
import type { Message } from "@/types/chat-types"

interface ChatMessagesProps {
  messages: Message[]
  isLoading: boolean
  selectedMode: string
}

export function ChatMessages({ 
  messages, 
  isLoading, 
  selectedMode
}: ChatMessagesProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [showScrollButton, setShowScrollButton] = useState(false)
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
    
    // Clear previous timeout
    if (scrollTimeoutRef.current !== undefined) {
      clearTimeout(scrollTimeoutRef.current)
    }
    
    // Reset scrolling state after a delay
    scrollTimeoutRef.current = setTimeout(() => {
      // setIsScrolling(false) // This line is removed
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
      {/* AI Chat Header */}
      <div className="flex-shrink-0 px-4 pt-4 pb-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
            <svg className="h-4 w-4 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-foreground">AI Chat</h3>
          <div className="flex items-center gap-1 ml-2">
            <div className={`w-2 h-2 rounded-full ${
              selectedMode === "analysis" ? "bg-purple-500" :
              selectedMode === "plan" ? "bg-blue-500" :
              selectedMode === "execute" ? "bg-green-500" :
              "bg-gray-400"
            }`} />
            <span className="text-xs text-muted-foreground capitalize">{selectedMode}</span>
          </div>
        </div>
      </div>

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

          {/* Enhanced thinking indicator */}
          {isLoading && (
            <ThinkingIndicator 
              message={getThinkingMessage(selectedMode)}
              isVisible={isLoading}
            />
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
 * Get thinking message based on selected mode
 */
function getThinkingMessage(selectedMode: string): string {
  switch (selectedMode) {
    case "plan":
      return "Planning your experiment"
    case "execute":
      return "Processing your data"
    case "analysis":
      return "Analyzing your request"
    default:
      return "Thinking"
  }
} 