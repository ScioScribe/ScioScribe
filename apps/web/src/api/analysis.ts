/**
 * Analysis API functions
 * 
 * This module provides functions to interact with the visualization generation service
 * through the /api/analysis/generate-visualization endpoint and WebSocket streaming.
 */

const BASE_URL = 'http://localhost:8000/api/analysis'
const WS_BASE_URL = 'ws://localhost:8000/api/analysis'

export interface GenerateVisualizationRequest {
  prompt: string
  plan: string
  csv: string
}

export interface GenerateVisualizationResponse {
  html: string
  message: string
}

export interface AnalysisError {
  error: string
  message: string
  details?: string
}

export interface NodeUpdateData {
  node_name: string
  node_data: {
    status: 'starting' | 'completed'
    description: string
  }
  timestamp: string
}

export interface AnalysisWebSocketMessage {
  type: 'node_update' | 'analysis_complete' | 'error' | 'session_status' | 'pong'
  data: Record<string, unknown>
  session_id: string
}

export type AnalysisWebSocketHandler = (message: AnalysisWebSocketMessage) => void

/**
 * Generates a Plotly visualization based on user prompt, plan, and CSV data
 * 
 * @param request - The visualization generation request containing prompt, plan, and CSV data
 * @returns Promise resolving to HTML containing the Plotly visualization
 * @throws Error if the request fails or returns an error
 */
export async function generateVisualization(request: GenerateVisualizationRequest): Promise<GenerateVisualizationResponse> {
  try {
    const response = await fetch(`${BASE_URL}/generate-visualization`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const errorData: AnalysisError = await response.json()
      throw new Error(`Visualization generation failed: ${errorData.message}`)
    }

    const result: GenerateVisualizationResponse = await response.json()
    return result
  } catch (error: unknown) {
    console.error('Analysis request failed:', error)
    throw new Error(error instanceof Error ? error.message : 'Unknown error occurred')
  }
}

/**
 * Creates a WebSocket connection for streaming analysis using the connection manager
 * 
 * @param sessionId - Analysis session ID
 * @param onMessage - Handler for WebSocket messages
 * @param onOpen - Handler for connection open
 * @param onError - Handler for connection errors
 * @param onClose - Handler for connection close
 * @returns WebSocket instance
 */
export function connectAnalysisWebSocket(
  sessionId: string,
  onMessage: AnalysisWebSocketHandler,
  onOpen?: () => void,
  onError?: (error: Event) => void,
  onClose?: (event: CloseEvent) => void
): WebSocket | null {
  const wsUrl = `${WS_BASE_URL}/ws/${sessionId}`
  console.log(`🔌 Connecting to analysis WebSocket: ${wsUrl}`)
  
  try {
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = (event) => {
      console.log('✅ Analysis WebSocket connected', event)
      onOpen?.()
    }
    
    ws.onmessage = (event) => {
      try {
        const message: AnalysisWebSocketMessage = JSON.parse(event.data)
        console.log('📨 Analysis WebSocket message received:', message)
        onMessage(message)
      } catch (error) {
        console.error('❌ Failed to parse WebSocket message:', error)
      }
    }
    
    ws.onerror = (error) => {
      console.error('❌ Analysis WebSocket error:', error)
      onError?.(error)
    }
    
    ws.onclose = (event) => {
      console.log('🔒 Analysis WebSocket closed:', event)
      onClose?.(event)
    }
    
    return ws
  } catch (error) {
    console.error('❌ Failed to create WebSocket:', error)
    onError?.(error as Event)
    return null
  }
}

/**
 * Sends an analysis request via WebSocket
 * 
 * @param ws - WebSocket connection
 * @param sessionId - Analysis session ID
 * @param request - Analysis request data
 */
export function sendAnalysisRequest(
  ws: WebSocket,
  sessionId: string,
  request: GenerateVisualizationRequest
): void {
  if (ws.readyState !== WebSocket.OPEN) {
    console.warn('WebSocket is not open, current state:', ws.readyState)
    throw new Error('WebSocket is not connected')
  }
  
  const message = {
    type: 'analysis_request',
    data: request,
    session_id: sessionId
  }
  
  console.log('📤 Sending analysis request:', message)
  ws.send(JSON.stringify(message))
} 