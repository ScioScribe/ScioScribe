/**
 * Enhanced Message Display Components
 * 
 * These components provide Cursor-style UI enhancements for chat messages,
 * including tool execution indicators, thinking animations, and better
 * visual separation between different types of content.
 */

/* eslint-disable react-refresh/only-export-components */
import { useState, useEffect } from "react"
import { Loader2, Play, CheckCircle, AlertCircle } from "lucide-react"

interface ToolExecutionDisplayProps {
  toolName: string
  description: string
  status: 'running' | 'completed' | 'error' | 'pending'
  children?: React.ReactNode
}

/**
 * Simplified tool execution display with clean styling
 */
export function ToolExecutionDisplay({ 
  toolName, 
  description, 
  status 
}: ToolExecutionDisplayProps) {
  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'pending':
        return <Play className="h-4 w-4 text-gray-400" />
      default:
        return <Play className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20'
      case 'completed':
        return 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
      case 'error':
        return 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
      case 'pending':
        return 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50'
      default:
        return 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50'
    }
  }

  return (
    <div className={`
      mb-3 rounded-lg border transition-all duration-200 
      ${getStatusColor()}
      ${status === 'running' ? 'shadow-sm' : ''}
    `}>
      <div className="px-4 py-3 flex items-center gap-3">
        <div className="flex-shrink-0">
          {getStatusIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
            {toolName}
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
            {description}
          </div>
        </div>
      </div>
    </div>
  )
}

interface ThinkingIndicatorProps {
  message?: string
  isVisible: boolean
}

/**
 * Cursor-style thinking indicator with animated dots
 */
export function ThinkingIndicator({ message = "Thinking", isVisible }: ThinkingIndicatorProps) {
  const [dots, setDots] = useState("")

  useEffect(() => {
    if (!isVisible) return

    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === "...") return ""
        return prev + "."
      })
    }, 500)

    return () => clearInterval(interval)
  }, [isVisible])

  if (!isVisible) return null

  return (
    <div className="mb-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex-shrink-0">
          <div className="w-4 h-4 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full animate-pulse" />
        </div>
        <div className="flex-1">
          <span className="text-sm text-gray-700 dark:text-gray-300 italic">
            {message}{dots}
          </span>
        </div>
      </div>
    </div>
  )
}

interface StageProgressionProps {
  stages: Array<{
    name: string
    status: 'pending' | 'active' | 'completed' | 'error'
    description?: string
  }>
  currentStage?: string
}

/**
 * Visual stage progression indicator for planning agents
 */
export function StageProgression({ stages, currentStage }: StageProgressionProps) {
  return (
    <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-800/30 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
        Experiment Planning Progress
      </div>
      <div className="space-y-2">
        {stages.map((stage, index) => {
          const isActive = stage.name === currentStage || stage.status === 'active'
          const isCompleted = stage.status === 'completed'
          const isError = stage.status === 'error'
          
          return (
            <div key={stage.name} className="flex items-center gap-3">
              <div className="flex-shrink-0">
                {isError ? (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                ) : isCompleted ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : isActive ? (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                ) : (
                  <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium ${
                  isActive ? 'text-blue-600 dark:text-blue-400' :
                  isCompleted ? 'text-green-600 dark:text-green-400' :
                  isError ? 'text-red-600 dark:text-red-400' :
                  'text-gray-500 dark:text-gray-400'
                }`}>
                  {stage.name}
                </div>
                {stage.description && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {stage.description}
                  </div>
                )}
              </div>
              {index < stages.length - 1 && (
                <div className={`w-px h-6 ${
                  isCompleted ? 'bg-green-300' : 'bg-gray-200 dark:bg-gray-600'
                }`} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface AgentMessageContainerProps {
  children: React.ReactNode
  agentType?: 'plan' | 'analysis' | 'execute'
  showBorder?: boolean
}

/**
 * Enhanced container for agent-generated text with rich visual styling
 */
export function AgentMessageContainer({ 
  children, 
  agentType = 'plan',
  showBorder = true 
}: AgentMessageContainerProps) {
  const getAgentConfig = () => {
    switch (agentType) {
      case 'plan':
        return {
          borderColor: 'border-blue-200 dark:border-blue-800',
          backgroundColor: 'bg-blue-50 dark:bg-blue-900/20',
          accentColor: 'bg-blue-500',
          icon: '🎯',
          label: 'Planning Agent'
        }
      case 'analysis':
        return {
          borderColor: 'border-purple-200 dark:border-purple-800',
          backgroundColor: 'bg-purple-50 dark:bg-purple-900/20',
          accentColor: 'bg-purple-500',
          icon: '📊',
          label: 'Analysis Agent'
        }
      case 'execute':
        return {
          borderColor: 'border-green-200 dark:border-green-800',
          backgroundColor: 'bg-green-50 dark:bg-green-900/20',
          accentColor: 'bg-green-500',
          icon: '⚡',
          label: 'Execution Agent'
        }
      default:
        return {
          borderColor: 'border-gray-200 dark:border-gray-700',
          backgroundColor: 'bg-gray-50 dark:bg-gray-800/50',
          accentColor: 'bg-gray-500',
          icon: '🤖',
          label: 'AI Agent'
        }
    }
  }

  if (!showBorder) {
    return <>{children}</>
  }

  const config = getAgentConfig()

  return (
    <div className={`
      mb-3 rounded-lg border ${config.borderColor} ${config.backgroundColor}
      shadow-sm transition-all duration-200 hover:shadow-md
    `}>
      {/* Agent header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-current/10">
        <div className={`w-2 h-2 rounded-full ${config.accentColor} animate-pulse`} />
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
          {config.icon} {config.label}
        </span>
      </div>
      
      {/* Agent content */}
      <div className="px-4 py-3">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          {children}
        </div>
      </div>
    </div>
  )
}

interface ApprovalMessageDisplayProps {
  message: string
  children?: React.ReactNode
}

/**
 * Enhanced approval message display with prominent styling
 */
export function ApprovalMessageDisplay({ message, children }: ApprovalMessageDisplayProps) {
  return (
    <div className="mb-3 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 shadow-sm">
      {/* Approval header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-amber-200/50 dark:border-amber-700/50">
        <div className="flex-shrink-0">
          <div className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center">
            <span className="text-white text-sm font-bold">!</span>
          </div>
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-amber-800 dark:text-amber-200">
            ⚠️ Approval Required
          </div>
          <div className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
            Please review and approve to continue
          </div>
        </div>
      </div>
      
      {/* Approval content */}
      <div className="px-4 py-3">
        <div className="prose prose-sm dark:prose-invert max-w-none text-amber-900 dark:text-amber-100">
          {message}
        </div>
        {children && (
          <div className="mt-3 pt-3 border-t border-amber-200/50 dark:border-amber-700/50">
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Utility function to parse tool execution messages and determine display type
 */
export function parseMessageForToolExecution(content: string, message?: { tool_id?: string; tool_status?: string }) {
  // Check if it's a tracked tool execution message
  if (message?.tool_id) {
    const nodeUpdateMatch = content.match(/^🔄 \*\*(.*?)\*\*\n\n(.*?)\n\nStatus: (.*)$/s)
    if (nodeUpdateMatch) {
      return {
        type: 'tool_execution' as const,
        toolName: nodeUpdateMatch[1],
        description: nodeUpdateMatch[2],
        status: (message.tool_status || 'running') as 'pending' | 'running' | 'completed' | 'error'
      }
    }
  }

  // Check if it's a node update message (analysis mode) - fallback for legacy parsing
  const nodeUpdateMatch = content.match(/^🔄 \*\*(.*?)\*\*\n\n(.*?)\n\nStatus: (.*)$/s)
  if (nodeUpdateMatch) {
    return {
      type: 'tool_execution' as const,
      toolName: nodeUpdateMatch[1],
      description: nodeUpdateMatch[2],
      status: nodeUpdateMatch[3].toLowerCase().includes('complete') ? 'completed' as const : 'running' as const
    }
  }

  // Check for connection/setup messages
  if (content.includes('**Connecting to') || content.includes('**Analysis Stream')) {
    return {
      type: 'system_status' as const,
      isConnecting: content.includes('Connecting'),
      isConnected: content.includes('Connected')
    }
  }

  // Check for error messages
  if (content.includes('❌') || content.includes('Error')) {
    return {
      type: 'error' as const
    }
  }

  // Default to agent message
  return {
    type: 'agent_message' as const
  }
}