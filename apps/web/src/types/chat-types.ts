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
  tool_id?: string  // For tracking tool execution messages that can be updated
  tool_status?: "pending" | "running" | "completed" | "error"
}

export interface SessionState {
  session_id: string | null
  experiment_id: string | null
  is_active: boolean
  is_waiting_for_approval: boolean
  pending_approval?: Record<string, unknown>
  current_stage?: string | null
  websocket_connection?: WebSocket | null
  last_activity: Date
}

export interface AiChatProps {
  plan?: string
  csv?: string
  editorText?: string
  onPlanChange?: (text: string) => void
  onVisualizationGenerated?: (html: string) => void
}



// WebSocket types
export interface WebSocketMessage {
  type: string
  data: Record<string, unknown>
  timestamp?: string
  session_id: string
}

export interface WebSocketConnectionHandlers {
  onMessage: (message: WebSocketMessage) => void
  onError: (error: Event) => void
  onOpen: () => void
  onClose: (event: CloseEvent) => void
}

export interface WebSocketConnectionOptions {
  maxReconnectAttempts?: number
  reconnectDelay?: number
}

export interface WebSocketConnectionInfo {
  websocket: WebSocket | null
  reconnectAttempts: number
  maxReconnectAttempts: number
  reconnectDelay: number
  onMessage: (message: WebSocketMessage) => void
  onError: (error: Event) => void
  onOpen: () => void
  onClose: (event: CloseEvent) => void
  isReconnecting: boolean
  lastActivity: Date
  lastPingSent: Date
  lastPongReceived: Date
  statusCheckInterval?: NodeJS.Timeout
}

export interface WebSocketConnectionStatus {
  connected: boolean
  reconnectAttempts: number
  maxReconnectAttempts: number
  isReconnecting: boolean
  lastActivity: Date
  lastPingSent: Date
  lastPongReceived: Date
  queuedMessages: number
  timeSinceLastActivity: number
  timeSinceLastPong: number
  connectionHealth: string
  canManualRetry: boolean
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
  updateMessage: (messageId: string, updates: Partial<Message>) => void
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>
  getPlanningSession: () => SessionState
  setPlanningSession: (updates: Partial<SessionState>) => void
  getDatacleanSession: () => SessionState
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
  timestamp?: string
}

export interface ChatSuggestion {
  text: string
  category: "visualization" | "analysis" | "insights"
} 