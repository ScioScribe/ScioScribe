/**
 * Chat Input Component
 * 
 * This component handles user input, mode selection, and message sending
 * for the chat interface. It includes a mode dropdown and input field.
 */

import type React from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Send, Lightbulb } from "lucide-react"
import type { SessionState } from "@/types/chat-types"

interface ChatInputProps {
  inputValue: string
  setInputValue: (value: string) => void
  selectedMode: string
  onModeChange: (mode: string) => void
  onSendMessage: () => void
  onToggleSuggestions: () => void
  onKeyPress: (e: React.KeyboardEvent) => void
  isLoading: boolean
  planningSession: SessionState
  datacleanSession: SessionState
  inputRef: React.RefObject<HTMLInputElement | null>
}

export function ChatInput({
  inputValue,
  setInputValue,
  selectedMode,
  onModeChange,
  onSendMessage,
  onToggleSuggestions,
  onKeyPress,
  isLoading,
  planningSession,
  datacleanSession,
  inputRef
}: ChatInputProps) {
  return (
    <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-transparent">
      {/* Mode Selector */}
      <div className="px-6 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Select value={selectedMode} onValueChange={onModeChange}>
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
          
          {/* Session indicators */}
          <SessionIndicators
            selectedMode={selectedMode}
            planningSession={planningSession}
            datacleanSession={datacleanSession}
          />
        </div>
        
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs"
          onClick={onToggleSuggestions}
        >
          <Lightbulb className="h-3 w-3" />
        </Button>
      </div>

      {/* Input Field */}
      <div className="px-6 py-3 flex items-center gap-2">
        <Input
          ref={inputRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={onKeyPress}
          placeholder={getPlaceholderText(selectedMode)}
          className="flex-1 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-2 focus-visible:ring-0 focus-visible:outline-none text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
          style={{
            fontFamily: '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            fontSize: "14px",
            lineHeight: "20px",
          }}
          disabled={isLoading}
        />
        <Button
          onClick={onSendMessage}
          disabled={isLoading || !inputValue.trim()}
          size="sm"
          className="h-8 px-3"
        >
          <Send className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}

/**
 * Session indicators component to show active session status
 */
interface SessionIndicatorsProps {
  selectedMode: string
  planningSession: SessionState
  datacleanSession: SessionState
}

function SessionIndicators({ selectedMode, planningSession, datacleanSession }: SessionIndicatorsProps) {
  if (selectedMode === "plan" && planningSession.is_active) {
    return (
      <span className="text-xs text-green-500 dark:text-green-400">
        ● Session: {planningSession.session_id?.slice(-8)}
      </span>
    )
  }
  
  if (selectedMode === "execute" && datacleanSession.is_active) {
    return (
      <span className="text-xs text-green-500 dark:text-green-400">
        ● Session: {datacleanSession.session_id?.slice(-8)}
      </span>
    )
  }
  
  return null
}

/**
 * Gets the appropriate placeholder text for different modes
 * @param mode The selected mode
 * @returns Placeholder text for the input field
 */
function getPlaceholderText(mode: string): string {
  switch (mode) {
    case "analysis":
      return "Ask me to create charts or analyze the iris data..."
    case "plan":
      return "Describe your experiment or research question..."
    case "execute":
      return "Ask me to clean or transform your data..."
    default:
      return "Ask me anything..."
  }
} 