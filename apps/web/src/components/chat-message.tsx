/**
 * Chat Message Component
 * 
 * This component renders individual chat messages with proper styling,
 * formatting for different message types and senders, and typewriter
 * animation for AI messages.
 */

import { useState, useEffect, useRef } from "react"
import type { Message } from "@/types/chat-types"

interface ChatMessageProps {
  message: Message
  enableTypewriter?: boolean
}

export function ChatMessage({ message, enableTypewriter = true }: ChatMessageProps) {
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
    const baseSpeed = 20 // Slightly faster base speed
    const speedVariation = Math.random() * 10 + 5 // 5-15ms variation
    const typingSpeed = baseSpeed + speedVariation
    
    const typeNextChar = () => {
      if (index < text.length) {
        // Update text in batches for better performance
        const batchSize = Math.random() > 0.8 ? 2 : 1 // Occasionally type 2 chars at once
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
        setTimeout(() => setShowCursor(false), 500)
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
          {message.mode && (
            <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">
              [{message.mode}]
            </span>
          )}
          {message.content}
        </div>
      )}
      
      {isAi && (
        <div className="text-gray-700 dark:text-gray-300 mt-0.5 pl-3">
          {message.mode && (
            <span className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
              [{message.mode}] {getResponseTypeIndicator(message.response_type)}
            </span>
          )}
          {message.isHtml ? (
            <div dangerouslySetInnerHTML={{ __html: message.content }} />
          ) : (
            <div className="relative">
              <pre ref={textRef} className="whitespace-pre-wrap font-inherit">
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
          )}
        </div>
      )}
      

    </div>
  )
}

/**
 * Gets the appropriate indicator for different response types
 * @param responseType The type of response
 * @returns String indicator for the response type
 */
function getResponseTypeIndicator(responseType?: string): string {
  switch (responseType) {
    case "approval":
      return "⚠️ Approval Required"
    case "confirmation":
      return "❓ Confirmation"
    case "error":
      return "❌ Error"
    default:
      return ""
  }
} 