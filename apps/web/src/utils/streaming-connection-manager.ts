/**
 * WebSocket Connection Manager
 * 
 * This utility class manages WebSocket connections for real-time bidirectional
 * communication with the backend. It handles connection lifecycle, reconnection
 * logic, error handling, health monitoring, and message protocol.
 */

import type { 
  WebSocketConnectionHandlers, 
  WebSocketConnectionOptions, 
  WebSocketConnectionInfo, 
  WebSocketConnectionStatus,
  WebSocketMessage
} from "@/types/chat-types"

export class WebSocketConnectionManager {
  private connections: Map<string, WebSocketConnectionInfo> = new Map()
  private messageQueue: Map<string, WebSocketMessage[]> = new Map()
  private healthCheckInterval?: NodeJS.Timeout

  constructor() {
    // Start periodic health check
    this.startHealthCheck()
  }

  /**
   * Creates a new WebSocket connection for the given session
   * @param sessionId Unique identifier for the session
   * @param url WebSocket URL endpoint
   * @param handlers Event handlers for connection lifecycle
   * @param options Connection options like retry limits
   * @returns WebSocket instance or null if creation failed
   */
  createConnection(
    sessionId: string,
    url: string,
    handlers: WebSocketConnectionHandlers,
    options?: WebSocketConnectionOptions
  ): WebSocket | null {
    try {
      console.log("🔄 Creating WebSocket connection for session:", sessionId)
      console.log("🔗 WebSocket URL:", url)
      
      const websocket = new WebSocket(url)
      console.log("✅ WebSocket created successfully")
      console.log("📊 Initial readyState:", websocket.readyState)
      console.log("📊 WebSocket.CONNECTING =", WebSocket.CONNECTING)
      console.log("📊 WebSocket.OPEN =", WebSocket.OPEN)
      console.log("📊 WebSocket.CLOSING =", WebSocket.CLOSING)
      console.log("📊 WebSocket.CLOSED =", WebSocket.CLOSED)
      
      const connectionInfo: WebSocketConnectionInfo = {
        websocket,
        reconnectAttempts: 0,
        maxReconnectAttempts: options?.maxReconnectAttempts || 3,
        reconnectDelay: options?.reconnectDelay || 2000,
        onMessage: handlers.onMessage,
        onError: handlers.onError,
        onOpen: handlers.onOpen,
        onClose: handlers.onClose,
        isReconnecting: false,
        lastActivity: new Date(),
        lastPingSent: new Date(),
        lastPongReceived: new Date(),
        statusCheckInterval: undefined
      }
      
      // Set up event handlers with enhanced debugging
      websocket.onopen = () => {
        console.log("✅ WEBSOCKET onopen triggered!")
        console.log("✅ WebSocket connection opened for session:", sessionId)
        console.log("📊 WebSocket readyState:", websocket.readyState)
        connectionInfo.isReconnecting = false
        connectionInfo.reconnectAttempts = 0
        connectionInfo.lastActivity = new Date()
        
        // Send any queued messages
        this.processMessageQueue(sessionId)
        
        handlers.onOpen()
      }
      
      websocket.onmessage = (event) => {
        console.log("🎯 WEBSOCKET onMessage triggered!")
        console.log("📥 WebSocket event.data:", event.data)
        console.log("📥 WebSocket event.type:", event.type)
        
        try {
          // Basic validation of event data
          if (!event.data || typeof event.data !== 'string') {
            console.warn("⚠️ Invalid event data received:", event.data)
            return
          }
          
          connectionInfo.lastActivity = new Date()
          connectionInfo.reconnectAttempts = 0 // Reset on successful message
          
          // Parse WebSocket message
          const message: WebSocketMessage = JSON.parse(event.data)
          
          // Handle system messages
          if (message.type === 'pong') {
            connectionInfo.lastPongReceived = new Date()
            console.log("🏓 Pong received from server")
            return
          }
          
          handlers.onMessage(message)
        } catch (error) {
          console.error("❌ Error processing WebSocket message:", error)
          console.error("❌ Raw message data:", event.data)
        }
      }
      
      websocket.onerror = (error) => {
        console.error("❌ WEBSOCKET onerror triggered!")
        console.error("❌ WebSocket error for session:", sessionId, error)
        console.log("📊 WebSocket readyState:", websocket.readyState)
        console.log("📊 WebSocket url:", websocket.url)
        
        this.handleConnectionError(sessionId, error)
      }
      
      websocket.onclose = (event) => {
        console.log("🔒 WEBSOCKET onclose triggered!")
        console.log("🔒 WebSocket connection closed for session:", sessionId)
        console.log("📊 Close code:", event.code)
        console.log("📊 Close reason:", event.reason)
        console.log("📊 Was clean close:", event.wasClean)
        
        // Clean up status check interval
        if (connectionInfo.statusCheckInterval) {
          clearInterval(connectionInfo.statusCheckInterval)
          connectionInfo.statusCheckInterval = undefined
        }
        
        // Handle close event
        handlers.onClose(event)
        
        // Attempt reconnection if not a clean close
        if (!event.wasClean && connectionInfo.reconnectAttempts < connectionInfo.maxReconnectAttempts) {
          this.handleConnectionError(sessionId, event)
        }
      }
      
      this.connections.set(sessionId, connectionInfo)
      
      // Initialize message queue for this session
      if (!this.messageQueue.has(sessionId)) {
        this.messageQueue.set(sessionId, [])
      }
      
      // Add periodic status monitoring
      const statusCheckInterval = setInterval(() => {
        console.log(`📊 WebSocket status check for ${sessionId}:`)
        console.log(`  - readyState: ${websocket.readyState} (${this.getReadyStateString(websocket.readyState)})`)
        console.log(`  - url: ${websocket.url}`)
        console.log(`  - lastActivity: ${connectionInfo.lastActivity}`)
        console.log(`  - reconnectAttempts: ${connectionInfo.reconnectAttempts}`)
        console.log(`  - isReconnecting: ${connectionInfo.isReconnecting}`)
        
        // Send ping if connection is open and it's been a while
        if (websocket.readyState === WebSocket.OPEN) {
          const timeSinceLastPing = new Date().getTime() - connectionInfo.lastPingSent.getTime()
          if (timeSinceLastPing > 30000) { // 30 seconds
            this.sendPing(sessionId)
          }
        }
        
        // Check for stale connections
        const timeSinceActivity = new Date().getTime() - connectionInfo.lastActivity.getTime()
        if (timeSinceActivity > 60000 && websocket.readyState === WebSocket.OPEN) {
          console.warn(`⚠️ Connection appears stale (${Math.round(timeSinceActivity / 1000)}s since last activity)`)
        }
        
        if (websocket.readyState === WebSocket.CLOSED) {
          console.log("❌ WebSocket is CLOSED, clearing interval")
          clearInterval(statusCheckInterval)
        }
      }, 5000) // Check every 5 seconds
      
      // Store interval for cleanup
      connectionInfo.statusCheckInterval = statusCheckInterval
      
      // Add immediate status check after creation
      setTimeout(() => {
        console.log("🔍 WebSocket status 1 second after creation:")
        console.log(`  - readyState: ${websocket.readyState}`)
        console.log(`  - Expected CONNECTING(0) or OPEN(1), got: ${websocket.readyState}`)
        
        if (websocket.readyState === WebSocket.CLOSED) {
          console.error("❌ WebSocket closed immediately after creation - check URL/server")
        }
      }, 1000)
      
      return websocket
    } catch (error) {
      console.error("❌ Failed to create WebSocket connection:", error)
      handlers.onError(error as Event)
      return null
    }
  }
  
  /**
   * Sends a message via WebSocket
   * @param sessionId Session identifier
   * @param message Message to send
   * @returns True if sent successfully, false otherwise
   */
  sendMessage(sessionId: string, message: WebSocketMessage): boolean {
    const connection = this.connections.get(sessionId)
    if (!connection || !connection.websocket) {
      console.error("❌ No WebSocket connection found for session:", sessionId)
      // Queue the message for when connection is restored
      this.queueMessage(sessionId, message)
      return false
    }
    
    // Check if we should circuit break (too many failures)
    if (connection.reconnectAttempts >= connection.maxReconnectAttempts && !connection.isReconnecting) {
      console.warn(`⚠️ Circuit breaker: Not sending message to failed connection ${sessionId}`)
      this.queueMessage(sessionId, message)
      return false
    }
    
    if (connection.websocket.readyState !== WebSocket.OPEN) {
      console.warn("⚠️ WebSocket not open, queueing message for session:", sessionId)
      this.queueMessage(sessionId, message)
      return false
    }
    
    try {
      const messageStr = JSON.stringify(message)
      connection.websocket.send(messageStr)
      console.log("📤 Message sent via WebSocket:", message.type)
      connection.lastActivity = new Date()
      return true
    } catch (error) {
      console.error("❌ Failed to send WebSocket message:", error)
      this.queueMessage(sessionId, message)
      
      // If send fails on an "open" connection, trigger error handling
      this.handleConnectionError(sessionId, new Event("send_failed"))
      return false
    }
  }
  
  /**
   * Queues a message for later sending when connection is restored
   * @param sessionId Session identifier
   * @param message Message to queue
   */
  private queueMessage(sessionId: string, message: WebSocketMessage) {
    if (!this.messageQueue.has(sessionId)) {
      this.messageQueue.set(sessionId, [])
    }
    
    const queue = this.messageQueue.get(sessionId)!
    queue.push(message)
    console.log(`📋 Message queued for session ${sessionId}, queue length: ${queue.length}`)
  }
  
  /**
   * Processes queued messages for a session
   * @param sessionId Session identifier
   */
  private processMessageQueue(sessionId: string) {
    const queue = this.messageQueue.get(sessionId)
    if (!queue || queue.length === 0) return
    
    console.log(`📋 Processing ${queue.length} queued messages for session ${sessionId}`)
    
    // Send all queued messages
    while (queue.length > 0) {
      const message = queue.shift()!
      if (!this.sendMessage(sessionId, message)) {
        // If sending fails, put it back at the front of the queue
        queue.unshift(message)
        break
      }
    }
  }
  
  /**
   * Sends a ping message to keep connection alive
   * @param sessionId Session identifier
   */
  private sendPing(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (!connection) return
    
    const pingMessage: WebSocketMessage = {
      type: 'ping',
      data: { timestamp: new Date().toISOString() },
      session_id: sessionId
    }
    
    if (this.sendMessage(sessionId, pingMessage)) {
      connection.lastPingSent = new Date()
      console.log("🏓 Ping sent to server")
    }
  }
  
  /**
   * Handles connection errors and initiates reconnection if within limits
   * @param sessionId Session identifier for the failed connection
   * @param error Error event or close event
   */
  private handleConnectionError(sessionId: string, error?: Event) {
    const connection = this.connections.get(sessionId)
    if (!connection) {
      console.error("❌ Connection not found for session:", sessionId)
      return
    }
    
    const readyState = connection.websocket?.readyState
    console.log(`🔍 Connection error details for session ${sessionId}:`)
    console.log(`  - ReadyState: ${readyState}`)
    console.log(`  - Reconnect attempts: ${connection.reconnectAttempts}/${connection.maxReconnectAttempts}`)
    console.log(`  - Is reconnecting: ${connection.isReconnecting}`)
    console.log(`  - Error type: ${error?.type || 'unknown'}`)
    
    // Call error handler
    if (error) {
      connection.onError(error)
    }
    
    // Attempt reconnection if within limits
    if (connection.reconnectAttempts < connection.maxReconnectAttempts && !connection.isReconnecting) {
      connection.isReconnecting = true
      connection.reconnectAttempts++
      
      // Exponential backoff with jitter
      const baseDelay = connection.reconnectDelay
      const exponentialDelay = Math.min(baseDelay * Math.pow(2, connection.reconnectAttempts - 1), 30000) // Max 30s
      const jitter = Math.random() * 1000 // Add up to 1s jitter
      const finalDelay = exponentialDelay + jitter
      
      console.log(`🔄 Attempting to reconnect session ${sessionId} (attempt ${connection.reconnectAttempts}/${connection.maxReconnectAttempts})`)
      console.log(`⏰ Reconnect delay: ${Math.round(finalDelay)}ms (exponential backoff)`)
      
      setTimeout(() => {
        this.reconnectSession(sessionId)
      }, finalDelay)
    } else {
      if (connection.reconnectAttempts >= connection.maxReconnectAttempts) {
        console.error("❌ Max reconnection attempts reached for session:", sessionId)
        this.handleMaxReconnectAttemptsReached(sessionId)
      }
      if (connection.isReconnecting) {
        console.error("❌ Already reconnecting session:", sessionId)
      }
    }
  }

  /**
   * Handles the case when max reconnection attempts are reached
   * @param sessionId Session identifier
   */
  private handleMaxReconnectAttemptsReached(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (!connection) return

    console.log(`🚫 Max reconnection attempts reached for ${sessionId}, enabling graceful degradation`)
    
    // Create a detailed error event for the application to handle
    const maxAttemptsError = new Event("max_reconnect_attempts") as Event & {
      sessionId: string
      queuedMessages: number
      lastError: string
    }
    maxAttemptsError.sessionId = sessionId
    maxAttemptsError.queuedMessages = this.messageQueue.get(sessionId)?.length || 0
    maxAttemptsError.lastError = "Maximum reconnection attempts exceeded"
    
    // Notify the application
    connection.onError(maxAttemptsError)
    
    // Don't close the connection immediately - keep it for potential manual retry
    // The application can decide whether to show a retry button or fallback UI
  }

  /**
   * Manually retry connection after max attempts reached
   * @param sessionId Session identifier to retry
   * @returns True if retry was initiated, false if not possible
   */
  manualRetryConnection(sessionId: string): boolean {
    const connection = this.connections.get(sessionId)
    if (!connection) {
      console.error("❌ No connection found for manual retry:", sessionId)
      return false
    }

    // Reset reconnection attempts for manual retry
    connection.reconnectAttempts = 0
    connection.isReconnecting = false

    console.log(`🔄 Manual retry initiated for session ${sessionId}`)
    
    // Attempt reconnection
    this.handleConnectionError(sessionId)
    return true
  }

  /**
   * Attempts to reconnect a failed session with enhanced session recovery
   * @param sessionId Session identifier to reconnect
   */
  private reconnectSession(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (!connection) return
    
    try {
      console.log(`🔄 Reconnecting session ${sessionId}...`)
      
      // Store original connection details for recovery
      const originalUrl = connection.websocket?.url || ""
      const queuedMessageCount = this.messageQueue.get(sessionId)?.length || 0
      
      // Close existing connection
      if (connection.websocket) {
        connection.websocket.close()
      }
      
      // Create new connection with enhanced recovery
      if (originalUrl) {
        console.log(`📡 Reconnecting to ${originalUrl} with ${queuedMessageCount} queued messages`)
        
        const newConnection = this.createConnection(
          sessionId,
          originalUrl,
          {
            onMessage: connection.onMessage,
            onError: connection.onError,
                         onOpen: () => {
               console.log(`✅ Session ${sessionId} reconnected successfully`)
               
               // Send session recovery message
               this.sendSessionRecoveryMessage(sessionId, queuedMessageCount)
               
               // Call original open handler
               connection.onOpen()
             },
            onClose: connection.onClose
          },
          {
            maxReconnectAttempts: connection.maxReconnectAttempts,
            reconnectDelay: connection.reconnectDelay
          }
        )
        
        if (!newConnection) {
          throw new Error("Failed to create reconnection")
        }
      } else {
        throw new Error("No original URL found for reconnection")
      }
    } catch (error) {
      console.error("❌ Failed to reconnect session:", sessionId, error)
      
      // Mark as not reconnecting so error handler can try again
      connection.isReconnecting = false
      
      // Continue with error handling
      this.handleConnectionError(sessionId)
    }
  }

  /**
   * Sends a session recovery message to help with backend session restoration
   * @param sessionId Session identifier
   * @param queuedMessageCount Number of messages that were queued
   */
  private sendSessionRecoveryMessage(sessionId: string, queuedMessageCount: number) {
    const recoveryMessage: WebSocketMessage = {
      type: 'session_recovery',
      data: { 
        recovered_at: new Date().toISOString(),
        queued_message_count: queuedMessageCount,
        client_session_id: sessionId
      },
      session_id: sessionId
    }
    
    // Send recovery message (will be queued if connection not ready)
    if (this.sendMessage(sessionId, recoveryMessage)) {
      console.log(`📡 Session recovery message sent for ${sessionId}`)
    }
  }
  
  /**
   * Closes a WebSocket connection and cleans up resources
   * @param sessionId Session identifier to close
   */
  closeConnection(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (connection && connection.websocket) {
      console.log("🔒 Closing WebSocket connection for session:", sessionId)
      
      // Clear status check interval if it exists
      if (connection.statusCheckInterval) {
        clearInterval(connection.statusCheckInterval)
        console.log("🔒 Cleared status check interval for session:", sessionId)
      }
      
      connection.websocket.close()
      this.connections.delete(sessionId)
      
      // Clear message queue
      this.messageQueue.delete(sessionId)
    }
  }
  
  /**
   * Gets the WebSocket instance for a session
   * @param sessionId Session identifier
   * @returns WebSocket instance or null if not found
   */
  getConnection(sessionId: string): WebSocket | null {
    return this.connections.get(sessionId)?.websocket || null
  }
  
  /**
   * Checks if a session has an active connection
   * @param sessionId Session identifier
   * @returns True if connected, false otherwise
   */
  isConnected(sessionId: string): boolean {
    const connection = this.connections.get(sessionId)
    return connection?.websocket?.readyState === WebSocket.OPEN
  }
  
  /**
   * Gets detailed status information for a connection
   * @param sessionId Session identifier
   * @returns Connection status object or null if not found
   */
  getConnectionStatus(sessionId: string): WebSocketConnectionStatus | null {
    const connection = this.connections.get(sessionId)
    if (!connection) return null
    
    const now = new Date()
    const timeSinceActivity = now.getTime() - connection.lastActivity.getTime()
    const timeSincePong = now.getTime() - connection.lastPongReceived.getTime()
    
    return {
      connected: connection.websocket?.readyState === WebSocket.OPEN,
      reconnectAttempts: connection.reconnectAttempts,
      maxReconnectAttempts: connection.maxReconnectAttempts,
      isReconnecting: connection.isReconnecting,
      lastActivity: connection.lastActivity,
      lastPingSent: connection.lastPingSent,
      lastPongReceived: connection.lastPongReceived,
      queuedMessages: this.messageQueue.get(sessionId)?.length || 0,
      timeSinceLastActivity: timeSinceActivity,
      timeSinceLastPong: timeSincePong,
      connectionHealth: this.assessConnectionHealth(sessionId),
      canManualRetry: connection.reconnectAttempts >= connection.maxReconnectAttempts
    }
  }

  /**
   * Assess the health of a connection
   * @param sessionId Session identifier
   * @returns Health assessment string
   */
  private assessConnectionHealth(sessionId: string): string {
    const connection = this.connections.get(sessionId)
    if (!connection || !connection.websocket) return "no_connection"
    
    const now = new Date()
    const timeSinceActivity = now.getTime() - connection.lastActivity.getTime()
    const timeSincePong = now.getTime() - connection.lastPongReceived.getTime()
    
    switch (connection.websocket.readyState) {
      case WebSocket.CONNECTING:
        return "connecting"
      case WebSocket.OPEN:
        if (timeSinceActivity < 30000 && timeSincePong < 60000) {
          return "healthy"
        } else if (timeSinceActivity < 120000) {
          return "stable"
        } else {
          return "stale"
        }
      case WebSocket.CLOSING:
        return "closing"
      case WebSocket.CLOSED:
        if (connection.isReconnecting) {
          return "reconnecting"
        } else if (connection.reconnectAttempts >= connection.maxReconnectAttempts) {
          return "failed"
        } else {
          return "disconnected"
        }
      default:
        return "unknown"
    }
  }
  
  /**
   * Closes all active connections
   */
  closeAllConnections() {
    console.log("🔒 Closing all WebSocket connections")
    this.connections.forEach((_, sessionId) => {
      this.closeConnection(sessionId)
    })
  }
  
  /**
   * Starts periodic health check for all connections
   */
  private startHealthCheck() {
    this.healthCheckInterval = setInterval(() => {
      this.performHealthCheck()
    }, 60000) // Check every minute
  }
  
  /**
   * Enhanced health check with connection recovery
   */
  performHealthCheck() {
    const now = new Date()
    const timeoutMs = 5 * 60 * 1000 // 5 minutes
    const staleConnectionMs = 2 * 60 * 1000 // 2 minutes for stale detection
    
    this.connections.forEach((connection, sessionId) => {
      const timeSinceActivity = now.getTime() - connection.lastActivity.getTime()
      const timeSincePong = now.getTime() - connection.lastPongReceived.getTime()
      
      // Check for completely inactive connections
      if (timeSinceActivity > timeoutMs || timeSincePong > timeoutMs) {
        console.log("⏰ Connection health check timeout for session:", sessionId)
        this.closeConnection(sessionId)
        return
      }
      
      // Check for stale connections that might need a ping
      if (connection.websocket?.readyState === WebSocket.OPEN) {
        const timeSinceLastPing = now.getTime() - connection.lastPingSent.getTime()
        
        if (timeSinceActivity > staleConnectionMs && timeSinceLastPing > 30000) {
          console.log(`📡 Sending health check ping to potentially stale connection ${sessionId}`)
          this.sendPing(sessionId)
        }
      }
      
      // Check for connections stuck in CONNECTING state
      if (connection.websocket?.readyState === WebSocket.CONNECTING) {
        const connectionAge = now.getTime() - connection.lastActivity.getTime()
        if (connectionAge > 30000) { // 30 seconds stuck connecting
          console.warn(`⚠️ Connection stuck in CONNECTING state for ${sessionId}, forcing reconnection`)
          this.handleConnectionError(sessionId, new Event("stuck_connecting"))
        }
      }
    })
  }

  /**
   * Gets human-readable string for WebSocket readyState
   * @param readyState The WebSocket readyState value
   * @returns Human-readable string
   */
  private getReadyStateString(readyState: number): string {
    switch (readyState) {
      case WebSocket.CONNECTING:
        return "CONNECTING"
      case WebSocket.OPEN:
        return "OPEN"
      case WebSocket.CLOSING:
        return "CLOSING"
      case WebSocket.CLOSED:
        return "CLOSED"
      default:
        return "UNKNOWN"
    }
  }

  /**
   * Gets a comprehensive debug summary of all connections
   * @returns Debug summary object
   */
  getDebugSummary(): {
    totalConnections: number
    totalQueuedMessages: number
    connections: Record<string, {
      readyState: number | undefined
      readyStateString: string
      url: string | undefined
      lastActivity: Date
      timeSinceActivityMs: number
      timeSinceActivitySeconds: number
      reconnectAttempts: number
      maxReconnectAttempts: number
      isReconnecting: boolean
      reconnectDelay: number
      lastPingSent: Date
      lastPongReceived: Date
      queuedMessages: number
    }>
  } {
    const summary = {
      totalConnections: this.connections.size,
      totalQueuedMessages: Array.from(this.messageQueue.values()).reduce((sum, queue) => sum + queue.length, 0),
      connections: {} as Record<string, {
        readyState: number | undefined
        readyStateString: string
        url: string | undefined
        lastActivity: Date
        timeSinceActivityMs: number
        timeSinceActivitySeconds: number
        reconnectAttempts: number
        maxReconnectAttempts: number
        isReconnecting: boolean
        reconnectDelay: number
        lastPingSent: Date
        lastPongReceived: Date
        queuedMessages: number
      }>
    }

    this.connections.forEach((connection, sessionId) => {
      const timeSinceActivity = new Date().getTime() - connection.lastActivity.getTime()
      summary.connections[sessionId] = {
        readyState: connection.websocket?.readyState,
        readyStateString: connection.websocket ? this.getReadyStateString(connection.websocket.readyState) : "NULL",
        url: connection.websocket?.url,
        lastActivity: connection.lastActivity,
        timeSinceActivityMs: timeSinceActivity,
        timeSinceActivitySeconds: Math.round(timeSinceActivity / 1000),
        reconnectAttempts: connection.reconnectAttempts,
        maxReconnectAttempts: connection.maxReconnectAttempts,
        isReconnecting: connection.isReconnecting,
        reconnectDelay: connection.reconnectDelay,
        lastPingSent: connection.lastPingSent,
        lastPongReceived: connection.lastPongReceived,
        queuedMessages: this.messageQueue.get(sessionId)?.length || 0
      }
    })

    return summary
  }

  /**
   * Logs comprehensive debug information for all connections
   */
  logDebugInfo(): void {
    console.log("🔍 === WEBSOCKET CONNECTION DEBUG INFO ===")
    const summary = this.getDebugSummary()
    console.log("📊 Debug Summary:", JSON.stringify(summary, null, 2))
    console.log("🔍 === END DEBUG INFO ===")
  }
  
  /**
   * Clean up resources when shutting down
   */
  destroy() {
    this.closeAllConnections()
    
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
      this.healthCheckInterval = undefined
    }
    
    this.messageQueue.clear()
    console.log("🔒 WebSocket connection manager destroyed")
  }
}

// Export a singleton instance for use across the application
export const websocketManager = new WebSocketConnectionManager() 