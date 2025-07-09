/**
 * Chat Message Component
 * 
 * This component renders individual chat messages with proper styling
 * and formatting for different message types and senders.
 */

import type { Message } from "@/types/chat-types"

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.sender === "user"
  const isAi = message.sender === "ai"

  return (
    <div className="mb-4">
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
            <pre className="whitespace-pre-wrap font-inherit">
              {message.content}
            </pre>
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