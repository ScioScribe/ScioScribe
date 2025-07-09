/**
 * Chat Types and Interfaces
 * 
 * This file contains all the TypeScript interfaces and types used by the AI Chat system.
 * It provides type definitions for messages, sessions, streaming events, and component props.
 */

export interface Message {
  id: string
  content: string
  sender: "user" | "ai"
  timestamp: Date
  isHtml?: boolean
  mode?: "plan" | "execute" | "analysis"
  session_id?: string
  response_type?: "text" | "html" | "approval" | "confirmation" | "error"
}

export interface SessionState {
  session_id: string | null
  experiment_id: string | null
  is_active: boolean
  is_waiting_for_approval: boolean
  pending_approval?: Record<string, unknown>
  stream_connection?: EventSource | null
  last_activity: Date
}

export interface AiChatProps {
  plan?: string
  csv?: string
  editorText?: string
  onPlanChange?: (text: string) => void
  onVisualizationGenerated?: (html: string) => void
}

export interface StreamingConnectionHandlers {
  onMessage: (event: MessageEvent) => void
  onError: (error: Event) => void
  onOpen: () => void
}

export interface StreamingConnectionOptions {
  maxReconnectAttempts?: number
  reconnectDelay?: number
}

export interface StreamingConnectionInfo {
  eventSource: EventSource | null
  reconnectAttempts: number
  maxReconnectAttempts: number
  reconnectDelay: number
  onMessage: (event: MessageEvent) => void
  onError: (error: Event) => void
  onOpen: () => void
  isReconnecting: boolean
  lastActivity: Date
  statusCheckInterval?: NodeJS.Timeout
}

export interface ConnectionStatus {
  connected: boolean
  reconnectAttempts: number
  maxReconnectAttempts: number
  isReconnecting: boolean
  lastActivity: Date
}

export interface ApprovalResponse {
  isApprovalResponse: boolean
  approved: boolean
  feedback?: string
}

export interface ChatMode {
  value: "plan" | "execute" | "analysis"
  label: string
  description: string
}

export interface MessageHandlerContext {
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>
  planningSession: SessionState
  setPlanningSession: (updates: Partial<SessionState>) => void
  datacleanSession: SessionState
  setDatacleanSession: (updates: Partial<SessionState>) => void
  updatePlanFromPlanningState: (state: Record<string, unknown>) => Promise<void>
  updatePlanFromPlanningMessage: (message: string, stage: string) => Promise<void>
  updateCsvFromDatacleanResponse: (response: Record<string, unknown>) => Promise<void>
  onVisualizationGenerated?: (html: string) => void
  plan: string
  csv: string
}

export interface StreamEvent {
  event_type: string
  data: Record<string, unknown>
  timestamp?: string
}

export interface DatacleanResponse {
  response_type: "text" | "data_preview" | "suggestion" | "confirmation" | "error"
  message: string
  data?: Record<string, unknown>
  suggestions?: Array<{
    type: string
    description: string
    confidence: number
  }>
  next_steps?: string[]
}

export interface PlanningStreamEvent {
  event_type: "update" | "approval_request" | "error" | "heartbeat"
  data: Record<string, unknown>
}

export interface ChatSuggestion {
  text: string
  category: "visualization" | "analysis" | "insights"
} 