/**
 * Chat Suggestions Component
 * 
 * This component displays contextual suggestions based on the current mode
 * to help users get started with different types of queries.
 */

import { Button } from "@/components/ui/button"
import { Lightbulb } from "lucide-react"
import { SAMPLE_PROMPTS } from "@/data/placeholder"

interface ChatSuggestionsProps {
  selectedMode: string
  onSuggestionClick: (suggestion: string) => void
}

export function ChatSuggestions({ selectedMode, onSuggestionClick }: ChatSuggestionsProps) {
  const suggestions = getSuggestionsForMode(selectedMode)
  
  return (
    <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 p-3">
      <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1">
        <Lightbulb className="h-3 w-3" />
        Try these suggestions:
      </div>
      <div className="space-y-1">
        {suggestions.slice(0, 3).map((suggestion, index) => (
          <Button
            key={index}
            onClick={() => onSuggestionClick(suggestion)}
            variant="outline"
            className="block w-full text-left text-xs p-2 rounded bg-white dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600"
          >
            {suggestion}
          </Button>
        ))}
      </div>
    </div>
  )
}

/**
 * Gets suggestions based on the current mode
 * @param mode The selected mode
 * @returns Array of suggestion strings
 */
function getSuggestionsForMode(mode: string): string[] {
  switch (mode) {
    case "analysis":
      return SAMPLE_PROMPTS.visualization.concat(SAMPLE_PROMPTS.insights)
    case "plan":
      return SAMPLE_PROMPTS.analysis
    case "execute":
      return [
        "Clean the data by removing null values",
        "Remove outliers from the dataset",
        "Transform categorical variables to numerical",
        "Fill missing values with mean/median",
        "Apply data normalization",
        "Filter rows based on conditions"
      ]
    default:
      return SAMPLE_PROMPTS.visualization
  }
} 