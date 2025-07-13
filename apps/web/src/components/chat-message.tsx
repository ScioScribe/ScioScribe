/**
 * Chat Message Component
 * 
 * This component renders individual chat messages with enhanced styling,
 * formatting for different message types and senders, typewriter animation,
 * and Cursor-style tool execution indicators.
 */

import { useState, useEffect, useRef } from "react"
import type { Message } from "@/types/chat-types"
import { 
  ToolExecutionDisplay, 
  AgentMessageContainer, 
  ApprovalMessageDisplay,
  parseMessageForToolExecution 
} from "@/components/enhanced-message-display"

interface ChatMessageProps {
  message: Message
  enableTypewriter?: boolean
  onTypewriterComplete?: () => void
}

export function ChatMessage({ message, enableTypewriter = true, onTypewriterComplete }: ChatMessageProps) {
  const isUser = message.sender === "user"
  const isAi = message.sender === "ai"
  
  // Typewriter animation state
  const [displayedText, setDisplayedText] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [showCursor, setShowCursor] = useState(false)
  const textRef = useRef<HTMLPreElement>(null)

  // Typewriter animation effect
  useEffect(() => {
    if (!isAi || !enableTypewriter || message.isHtml) {
      setDisplayedText(message.content)
      setIsTyping(false)
      setShowCursor(false)
      return
    }

    // Reset state
    setDisplayedText("")
    setIsTyping(true)
    setShowCursor(true)

    const text = message.content
    let index = 0
    let animationFrameId: number | null = null
    
    // Calculate typing speed based on content length
    const baseSpeed = 8 // Much faster base speed
    const speedVariation = Math.random() * 4 + 2 // 2-6ms variation
    const typingSpeed = baseSpeed + speedVariation
    
    const typeNextChar = () => {
      if (index < text.length) {
        // Update text in batches for better performance
        const batchSize = Math.random() > 0.6 ? 3 : Math.random() > 0.3 ? 2 : 1 // More frequent batching
        const nextIndex = Math.min(index + batchSize, text.length)
        setDisplayedText(text.slice(0, nextIndex))
        index = nextIndex
        
        // Force DOM update by using requestAnimationFrame
        animationFrameId = requestAnimationFrame(() => {
          // Add some randomness to typing speed for natural feel
          const currentSpeed = typingSpeed + (Math.random() * 10 - 5)
          setTimeout(typeNextChar, currentSpeed)
        })
      } else {
        setIsTyping(false)
        // Keep cursor visible for a short time after typing completes
        setTimeout(() => {
          setShowCursor(false)
          // Call completion callback if provided
          onTypewriterComplete?.()
        }, 500)
      }
    }

    // Start typing with a small delay
    const startDelay = setTimeout(typeNextChar, 100)

    return () => {
      clearTimeout(startDelay)
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId)
      }
    }
  /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [message.content, message.isHtml, isAi, enableTypewriter])

  // Cursor blinking effect
  useEffect(() => {
    if (!showCursor || !isTyping) return

    const cursorInterval = setInterval(() => {
      // Force re-render to make cursor blink
      textRef.current?.setAttribute('data-cursor-state', Date.now().toString())
    }, 530) // Slightly slower than typical cursor blink

    return () => clearInterval(cursorInterval)
  }, [showCursor, isTyping])

  return (
    <div className="mb-2 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      {isUser && (
        <div className="text-gray-900 dark:text-gray-100 font-bold">
          <span className="text-blue-500 mr-2">→</span>
          {message.content}
        </div>
      )}
      
      {isAi && (
        <div className="text-gray-700 dark:text-gray-300 mt-0.5">
          {message.isHtml ? (
            <div dangerouslySetInnerHTML={{ __html: message.content }} />
          ) : (
            <EnhancedMessageRenderer 
              message={message}
              displayedText={displayedText}
              isTyping={isTyping}
              showCursor={showCursor}
              textRef={textRef}
            />
          )}
        </div>
      )}
      

    </div>
  )
}

/**
 * Enhanced message renderer that uses the new UI components
 */
interface EnhancedMessageRendererProps {
  message: Message
  displayedText: string
  isTyping: boolean
  showCursor: boolean
  textRef: React.RefObject<HTMLPreElement | null>
}

function EnhancedMessageRenderer({ 
  message, 
  displayedText, 
  isTyping, 
  showCursor, 
  textRef 
}: EnhancedMessageRendererProps) {
  const parsedMessage = parseMessageForToolExecution(message.content, message)
  
  switch (parsedMessage.type) {
    case 'tool_execution':
      return (
        <ToolExecutionDisplay
          toolName={parsedMessage.toolName}
          description={parsedMessage.description}
          status={parsedMessage.status}
        />
      )
    
    case 'system_status':
      if (parsedMessage.isConnecting) {
        return (
          <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
            <div className="text-sm text-blue-700 dark:text-blue-300">
              Establishing connection...
            </div>
          </div>
        )
      } else if (parsedMessage.isConnected) {
        return (
          <div className="flex items-center gap-3 px-4 py-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <div className="text-sm text-green-700 dark:text-green-300">
              Connected - Ready for real-time updates
            </div>
          </div>
        )
      }
      return renderDefaultMessage()
    
    case 'error':
      return (
        <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="relative">
            <pre ref={textRef} className="whitespace-pre-wrap font-inherit text-red-700 dark:text-red-300">
              {displayedText}
              {isTyping && showCursor && (
                <span 
                  className="inline-block w-2 h-5 bg-red-500 ml-1" 
                  style={{
                    animation: 'cursor-blink 1.06s infinite',
                    verticalAlign: 'text-bottom'
                  }}
                />
              )}
            </pre>
          </div>
        </div>
      )
    
    default:
      // Check if it's an approval message
      if (message.response_type === 'approval') {
        return (
          <ApprovalMessageDisplay message={displayedText}>
            {/* Future: Add approval buttons here */}
          </ApprovalMessageDisplay>
        )
      }
      
      return (
        <AgentMessageContainer 
          agentType={message.mode as 'plan' | 'analysis' | 'execute'}
          showBorder={true}
        >
          {renderDefaultMessage()}
        </AgentMessageContainer>
      )
  }
  
  function renderDefaultMessage() {
    return (
      <div className="relative">
        <pre 
          ref={textRef} 
          className="whitespace-pre-wrap leading-relaxed text-gray-800 dark:text-gray-200 font-inherit"
        >
          {displayedText}
          {isTyping && showCursor && (
            <span 
              className="inline-block w-2 h-5 bg-blue-500 ml-1" 
              style={{
                animation: 'cursor-blink 1.06s infinite',
                verticalAlign: 'text-bottom'
              }}
            />
          )}
        </pre>
      </div>
    )
  }
}

 