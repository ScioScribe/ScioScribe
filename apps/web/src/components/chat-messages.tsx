/**
 * Chat Messages Component
 * 
 * This component displays the list of chat messages with proper scrolling
 * and loading states. It uses the ChatMessage component for individual messages.
 */

import { useEffect, useRef } from "react"
import { ChatMessage } from "@/components/chat-message"
import type { Message } from "@/types/chat-types"

interface ChatMessagesProps {
  messages: Message[]
  isLoading: boolean
  selectedMode: string
}

export function ChatMessages({ messages, isLoading, selectedMode }: ChatMessagesProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div
      ref={scrollAreaRef}
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
  )
}

/**
 * Loading indicator component that shows mode-specific loading text
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
 * Gets mode-specific loading text
 * @param mode The selected mode
 * @returns Loading text for the mode
 */
function getLoadingText(mode: string): string {
  switch (mode) {
    case "analysis":
      return "Generating visualization..."
    case "plan":
      return "Planning experiment..."
    case "execute":
      return "Processing data..."
    default:
      return "Processing..."
  }
} 