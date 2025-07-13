/**
 * Data Cleaning API Client - Simplified Version
 * 
 * This module provides a clean interface to the data processing API.
 */

export type DataAction = 'analyze' | 'clean' | 'describe' | 'add_row' | 'delete_row';

export interface DataProcessRequest {
  action: DataAction;
  csv_data: string;
  experiment_id?: string;
  params?: Record<string, any>;
}

export interface DataProcessResponse {
  success: boolean;
  action: string;
  csv_data?: string;
  changes?: string[];
  analysis?: {
    issues: Array<{
      type: string;
      column?: string;
      count?: number;
      percentage?: number;
      severity: string;
      fix: string;
    }>;
    total_issues: number;
    data_quality_score: number;
  };
  description?: {
    shape: { rows: number; columns: number };
    columns: string[];
    dtypes: Record<string, string>;
    memory_usage: string;
    column_stats: Record<string, any>;
    sample_data: Record<string, any>[];
  };
  ai_message: string;
  error?: string;
}

/**
 * Process data with the specified action
 */
export async function processData(
  action: DataAction,
  csvData: string,
  experimentId?: string,
  params?: Record<string, any>
): Promise<DataProcessResponse> {
  try {
    const response = await fetch('/api/dataclean/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action,
        csv_data: csvData,
        experiment_id: experimentId,
        params: params || {}
      } as DataProcessRequest),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Data processing error:', error);
    return {
      success: false,
      action,
      ai_message: '❌ Failed to process data. Please try again.',
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

/**
 * Helper function to detect action from user message
 */
export function detectAction(message: string): DataAction {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes('analyze') || lowerMessage.includes('check') || lowerMessage.includes('quality')) {
    return 'analyze';
  } else if (lowerMessage.includes('clean') || lowerMessage.includes('fix')) {
    return 'clean';
  } else if (lowerMessage.includes('describe') || lowerMessage.includes('overview') || lowerMessage.includes('summary')) {
    return 'describe';
  } else if (lowerMessage.includes('add') && lowerMessage.includes('row')) {
    return 'add_row';
  } else if (lowerMessage.includes('delete') || lowerMessage.includes('remove')) {
    return 'delete_row';
  }
  
  // Default to analyze if unsure
  return 'analyze';
}

/**
 * Extract parameters from user message
 */
export function extractParams(message: string, action: DataAction): Record<string, any> {
  const params: Record<string, any> = {};
  
  if (action === 'add_row') {
    // Try to extract key-value pairs from message
    // Example: "add row with name=John, age=30"
    const matches = message.matchAll(/(\w+)\s*=\s*([^,]+)/g);
    const rowData: Record<string, any> = {};
    
    for (const match of matches) {
      const key = match[1].trim();
      let value: any = match[2].trim();
      
      // Try to parse as number
      if (!isNaN(Number(value))) {
        value = Number(value);
      }
      
      rowData[key] = value;
    }
    
    if (Object.keys(rowData).length > 0) {
      params.row_data = rowData;
    }
  } else if (action === 'delete_row') {
    // Try to extract condition
    // Example: "delete rows where department=Sales"
    const whereMatch = message.match(/where\s+(\w+)\s*=\s*(.+)/i);
    if (whereMatch) {
      const column = whereMatch[1].trim();
      let value: any = whereMatch[2].trim();
      
      // Remove quotes if present
      if ((value.startsWith('"') && value.endsWith('"')) || 
          (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      
      // Try to parse as number
      if (!isNaN(Number(value))) {
        value = Number(value);
      }
      
      params.condition = { [column]: value };
    }
  }
  
  return params;
}

// Additional API functions for frontend compatibility

/**
 * Response type for file upload
 */
export interface ProcessFileCompleteResponse {
  success: boolean;
  artifact_id: string;
  cleaned_data?: string;
  data_shape?: number[];
  error_message?: string;
}

/**
 * Upload a file (CSV, PDF, or image) for processing
 */
export async function uploadFile(
  file: File,
  experimentId: string = "demo-experiment",
  responseFormat: string = "csv"
): Promise<ProcessFileCompleteResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('experiment_id', experimentId);
    formData.append('response_format', responseFormat);
    
    const response = await fetch('/api/dataclean/upload', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Upload failed: ${error}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('File upload error:', error);
    return {
      success: false,
      artifact_id: '',
      error_message: error instanceof Error ? error.message : 'Upload failed'
    };
  }
}

/**
 * Response type for header generation
 */
export interface GenerateHeadersResponse {
  success: boolean;
  headers: string[];
  csv_data: string;
  error_message?: string;
}

/**
 * Generate CSV headers from experimental plan
 */
export async function generateHeadersFromPlan(
  plan: string,
  experimentId?: string
): Promise<GenerateHeadersResponse> {
  try {
    const response = await fetch('/api/dataclean/generate-headers', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        plan,
        experiment_id: experimentId,
      }),
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to generate headers: ${error}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Header generation error:', error);
    return {
      success: false,
      headers: [],
      csv_data: '',
      error_message: error instanceof Error ? error.message : 'Generation failed'
    };
  }
}

/**
 * Conversation session types
 */
export interface StartConversationRequest {
  user_id?: string;
  session_id?: string;
  artifact_id?: string;
  file_path?: string;
  csv_data?: string;
  user_message?: string;
}

export interface StartConversationResponse {
  session_id: string;
  user_id: string;
  status: string;
  message: string;
  capabilities: string[];
  session_info: {
    created_at: string;
    session_type: string;
    state: string;
  };
}

/**
 * Start a conversation session (mainly for compatibility)
 */
export async function startConversation(
  request: StartConversationRequest
): Promise<StartConversationResponse> {
  // For the simplified version, we just return a mock session
  // The actual data processing happens through the processData function
  const sessionId = request.session_id || `session-${Date.now()}`;
  
  return {
    session_id: sessionId,
    user_id: request.user_id || 'default-user',
    status: 'active',
    message: 'Ready to process your data',
    capabilities: ['analyze', 'clean', 'describe', 'add_row', 'delete_row'],
    session_info: {
      created_at: new Date().toISOString(),
      session_type: 'dataclean',
      state: 'active'
    }
  };
}

// WebSocket support for conversational dataclean
import { WebSocketConnectionManager } from '@/utils/streaming-connection-manager';
import type { WebSocketConnectionHandlers, WebSocketMessage } from '@/types/chat-types';

// Singleton WebSocket manager instance
const websocketManager = new WebSocketConnectionManager();

/**
 * Connect to dataclean WebSocket for streaming conversation
 */
export function connectDatacleanSession(
  sessionId: string,
  handlers: WebSocketConnectionHandlers
): WebSocket | null {
  console.log('🔗 Connecting to dataclean WebSocket:', sessionId);
  
  const wsUrl = `ws://localhost:8000/api/dataclean/ws/${sessionId}`;
  
  try {
    const connection = websocketManager.createConnection(
      sessionId,
      wsUrl,
      handlers,
      {
        maxReconnectAttempts: 3,
        reconnectDelay: 2000
      }
    );
    
    if (connection) {
      console.log('✅ Dataclean WebSocket connected:', sessionId);
    } else {
      console.error('❌ Failed to connect dataclean WebSocket:', sessionId);
    }
    
    return connection;
  } catch (error) {
    console.error('❌ Dataclean WebSocket error:', error);
    return null;
  }
}

/**
 * Send message through dataclean WebSocket
 */
export function sendDatacleanWebSocketMessage(
  sessionId: string,
  message: string,
  csvData?: string
): boolean {
  console.log('📤 Sending dataclean WebSocket message:', sessionId);
  
  const wsMessage: WebSocketMessage = {
    type: 'message',
    data: {
      message,
      csv_data: csvData
    },
    session_id: sessionId
  };
  
  return websocketManager.sendMessage(sessionId, wsMessage);
}

/**
 * Check if dataclean session is connected
 */
export function isDatacleanSessionConnected(sessionId: string): boolean {
  return websocketManager.isConnected(sessionId);
}

/**
 * Get dataclean connection status
 */
export function getDatacleanConnectionStatus(sessionId: string) {
  return websocketManager.getConnectionStatus(sessionId);
}

/**
 * Close dataclean WebSocket connection
 */
export function closeDatacleanSession(sessionId: string): void {
  console.log('🔌 Closing dataclean session:', sessionId);
  websocketManager.closeConnection(sessionId);
}

/**
 * Get dataclean WebSocket connection
 */
export function getDatacleanConnection(sessionId: string): WebSocket | null {
  return websocketManager.getConnection(sessionId);
}

/**
 * Retry dataclean connection
 */
export function retryDatacleanConnection(sessionId: string): boolean {
  console.log('🔄 Retrying dataclean connection:', sessionId);
  return websocketManager.manualRetryConnection(sessionId);
} 