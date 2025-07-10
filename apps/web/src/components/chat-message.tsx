/**
 * Chat Message Component
 * 
 * This component renders individual chat messages with proper styling,
 * formatting for different message types and senders, and typewriter
 * animation for AI messages.
 */

import { useState, useEffect } from "react"
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
    
    // Calculate typing speed based on content length
    const baseSpeed = 25
    const speedVariation = Math.random() * 15 + 5 // 5-20ms variation
    const typingSpeed = baseSpeed + speedVariation
    
    const typeNextChar = () => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1))
        index++
        
        // Add some randomness to typing speed for natural feel
        const currentSpeed = typingSpeed + (Math.random() * 10 - 5)
        setTimeout(typeNextChar, currentSpeed)
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
    }
  }, [message.content, message.isHtml, isAi, enableTypewriter])

  // Cursor blinking effect
  useEffect(() => {
    if (!showCursor) return

    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev)
    }, 530) // Slightly slower than typical cursor blink

    return () => clearInterval(cursorInterval)
  }, [showCursor])

  return (
    <div className="mb-4 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
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
        <div className="text-gray-700 dark:text-gray-300 mt-1 pl-4">
          {message.mode && (
            <span className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
              [{message.mode}] {getResponseTypeIndicator(message.response_type)}
            </span>
          )}
          {message.isHtml ? (
            <div dangerouslySetInnerHTML={{ __html: message.content }} />
          ) : (
            <div className="relative">
              <pre className="whitespace-pre-wrap font-inherit">
                {displayedText}
                {isTyping && showCursor && (
                  <span className="inline-block w-2 h-5 bg-blue-500 ml-1 animate-pulse" />
                )}
              </pre>
              {/* Typing indicator for longer messages */}
              {isTyping && displayedText.length > 50 && (
                <div className="absolute -bottom-1 left-0 flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                  <div className="flex space-x-1">
                    <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce"></div>
                    <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                    <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                  </div>
                  <span>typing...</span>
                </div>
              )}
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