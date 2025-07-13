/**
 * Chat Input Component
 * 
 * This component handles user input, mode selection, and message sending
 * for the chat interface. It includes a mode dropdown and input field.
 */

import type React from "react"
import TextareaAutosize from "react-textarea-autosize"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Microscope } from "lucide-react"
import { cn } from "@/shared/utils"
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
  inputRef: React.RefObject<HTMLTextAreaElement | null>
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
                Plan
              </SelectItem>
              <SelectItem value="execute" className="text-xs dark:text-gray-300 dark:focus:bg-gray-700">
                Execute
              </SelectItem>
              <SelectItem value="analysis" className="text-xs dark:text-gray-300 dark:focus:bg-gray-700">
                Analysis
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
        {/* Suggestions toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleSuggestions}
          className="text-xs"
          disabled={isLoading}
        >
          Suggestions
        </Button>
      </div>

      {/* Input Field */}
      <div className="px-6 py-3">
        <div className="relative">
          <TextareaAutosize
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={onKeyPress}
            placeholder={getPlaceholderText(selectedMode)}
            className={cn(
              "w-full resize-none border-0 bg-transparent px-4 py-3 pr-12 text-sm",
              "placeholder:text-muted-foreground/60",
              "focus-visible:outline-none focus-visible:ring-0",
              "text-foreground",
              "leading-relaxed"
            )}
            style={{
              fontFamily: '"Source Code Pro", ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              fontSize: "14px",
              lineHeight: "1.5",
            }}
            minRows={3}
            maxRows={8}
            disabled={isLoading}
          />
          
          {/* Submit button inside textarea - bottom right */}
          <Button
            onClick={onSendMessage}
            disabled={isLoading || !inputValue.trim()}
            size="sm"
            className="absolute bottom-2 right-2 h-8 w-8 p-0 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200"
          >
            <Microscope className="h-3.5 w-3.5 text-blue-500" />
          </Button>
          
          {/* Container with subtle border */}
          <div className="absolute inset-0 -z-10 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 shadow-sm transition-all duration-200 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 focus-within:border-gray-400 dark:focus-within:border-gray-500 focus-within:shadow-md" />
        </div>
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