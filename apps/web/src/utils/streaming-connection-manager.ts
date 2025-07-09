/**
 * Streaming Connection Manager
 * 
 * This utility class manages EventSource connections for real-time streaming
 * communication with the backend. It handles connection lifecycle, reconnection
 * logic, error handling, and health monitoring.
 */

import type { 
  StreamingConnectionHandlers, 
  StreamingConnectionOptions, 
  StreamingConnectionInfo, 
  ConnectionStatus 
} from "@/types/chat-types"

export class StreamingConnectionManager {
  private connections: Map<string, StreamingConnectionInfo> = new Map()

  /**
   * Creates a new streaming connection for the given session
   * @param sessionId Unique identifier for the session
   * @param url EventSource URL endpoint
   * @param handlers Event handlers for connection lifecycle
   * @param options Connection options like retry limits
   * @returns EventSource instance or null if creation failed
   */
  createConnection(
    sessionId: string,
    url: string,
    handlers: StreamingConnectionHandlers,
    options?: StreamingConnectionOptions
  ): EventSource | null {
    try {
      console.log("🔄 Creating streaming connection for session:", sessionId)
      console.log("🔗 EventSource URL:", url)
      console.log("🔗 EventSource options:", { withCredentials: false })
      
      const eventSource = new EventSource(url, { withCredentials: false })
      console.log("✅ EventSource created successfully")
      console.log("📊 Initial readyState:", eventSource.readyState)
      console.log("📊 EventSource.CONNECTING =", EventSource.CONNECTING)
      console.log("📊 EventSource.OPEN =", EventSource.OPEN)
      console.log("📊 EventSource.CLOSED =", EventSource.CLOSED)
      
      const connectionInfo: StreamingConnectionInfo = {
        eventSource,
        reconnectAttempts: 0,
        maxReconnectAttempts: options?.maxReconnectAttempts || 3,
        reconnectDelay: options?.reconnectDelay || 2000,
        onMessage: handlers.onMessage,
        onError: handlers.onError,
        onOpen: handlers.onOpen,
        isReconnecting: false,
        lastActivity: new Date(),
        statusCheckInterval: undefined
      }
      
      // Set up event handlers with enhanced debugging
      eventSource.onmessage = (event) => {
        console.log("🎯 EVENTSOURCE onMessage triggered!")
        console.log("📥 EventSource event.data:", event.data)
        console.log("📥 EventSource event.type:", event.type)
        console.log("📥 EventSource event.lastEventId:", event.lastEventId)
        
        connectionInfo.lastActivity = new Date()
        connectionInfo.reconnectAttempts = 0 // Reset on successful message
        handlers.onMessage(event)
      }
      
      eventSource.onerror = (error) => {
        console.error("❌ EVENTSOURCE onerror triggered!")
        console.error("❌ Stream error for session:", sessionId, error)
        console.log("📊 EventSource readyState:", eventSource.readyState)
        console.log("📊 EventSource url:", eventSource.url)
        this.handleConnectionError(sessionId)
      }
      
      eventSource.onopen = () => {
        console.log("✅ EVENTSOURCE onopen triggered!")
        console.log("✅ Stream connection opened for session:", sessionId)
        console.log("📊 EventSource readyState:", eventSource.readyState)
        connectionInfo.isReconnecting = false
        connectionInfo.reconnectAttempts = 0
        handlers.onOpen()
      }
      
      this.connections.set(sessionId, connectionInfo)
      
      // Add periodic status monitoring
      const statusCheckInterval = setInterval(() => {
        console.log(`📊 EventSource status check for ${sessionId}:`)
        console.log(`  - readyState: ${eventSource.readyState}`)
        console.log(`  - url: ${eventSource.url}`)
        console.log(`  - lastActivity: ${connectionInfo.lastActivity}`)
        
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log("❌ EventSource is CLOSED, clearing interval")
          clearInterval(statusCheckInterval)
        }
      }, 5000) // Check every 5 seconds
      
      // Store interval for cleanup
      connectionInfo.statusCheckInterval = statusCheckInterval
      
      // Add immediate status check after creation
      setTimeout(() => {
        console.log("🔍 EventSource status 1 second after creation:")
        console.log(`  - readyState: ${eventSource.readyState}`)
        console.log(`  - Expected CONNECTING(0) or OPEN(1), got: ${eventSource.readyState}`)
        
        if (eventSource.readyState === EventSource.CLOSED) {
          console.error("❌ EventSource closed immediately after creation - check URL/server")
        }
      }, 1000)
      
      return eventSource
    } catch (error) {
      console.error("❌ Failed to create streaming connection:", error)
      handlers.onError(error as Event)
      return null
    }
  }
  
  /**
   * Handles connection errors and initiates reconnection if within limits
   * @param sessionId Session identifier for the failed connection
   */
  private handleConnectionError(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (!connection) return
    
    connection.onError(new Event("connection_error"))
    
    // Attempt reconnection if within limits
    if (connection.reconnectAttempts < connection.maxReconnectAttempts && !connection.isReconnecting) {
      connection.isReconnecting = true
      connection.reconnectAttempts++
      
      console.log(`🔄 Attempting to reconnect session ${sessionId} (attempt ${connection.reconnectAttempts}/${connection.maxReconnectAttempts})`)
      
      setTimeout(() => {
        this.reconnectSession(sessionId)
      }, connection.reconnectDelay)
    } else {
      console.error("❌ Max reconnection attempts reached for session:", sessionId)
      this.closeConnection(sessionId)
    }
  }
  
  /**
   * Attempts to reconnect a failed session
   * @param sessionId Session identifier to reconnect
   */
  private reconnectSession(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (!connection) return
    
    try {
      // Close existing connection
      if (connection.eventSource) {
        connection.eventSource.close()
      }
      
      // Create new connection with same handlers
      const originalUrl = connection.eventSource?.url || ""
      if (originalUrl) {
        this.createConnection(
          sessionId,
          originalUrl,
          {
            onMessage: connection.onMessage,
            onError: connection.onError,
            onOpen: connection.onOpen
          },
          {
            maxReconnectAttempts: connection.maxReconnectAttempts,
            reconnectDelay: connection.reconnectDelay
          }
        )
      }
    } catch (error) {
      console.error("❌ Failed to reconnect session:", sessionId, error)
      this.closeConnection(sessionId)
    }
  }
  
  /**
   * Closes a streaming connection and cleans up resources
   * @param sessionId Session identifier to close
   */
  closeConnection(sessionId: string) {
    const connection = this.connections.get(sessionId)
    if (connection && connection.eventSource) {
      console.log("🔒 Closing streaming connection for session:", sessionId)
      
      // Clear status check interval if it exists
      if (connection.statusCheckInterval) {
        clearInterval(connection.statusCheckInterval)
        console.log("🔒 Cleared status check interval for session:", sessionId)
      }
      
      connection.eventSource.close()
      this.connections.delete(sessionId)
    }
  }
  
  /**
   * Gets the EventSource instance for a session
   * @param sessionId Session identifier
   * @returns EventSource instance or null if not found
   */
  getConnection(sessionId: string): EventSource | null {
    return this.connections.get(sessionId)?.eventSource || null
  }
  
  /**
   * Checks if a session has an active connection
   * @param sessionId Session identifier
   * @returns True if connected, false otherwise
   */
  isConnected(sessionId: string): boolean {
    const connection = this.connections.get(sessionId)
    return connection?.eventSource?.readyState === EventSource.OPEN
  }
  
  /**
   * Gets detailed status information for a connection
   * @param sessionId Session identifier
   * @returns Connection status object or null if not found
   */
  getConnectionStatus(sessionId: string): ConnectionStatus | null {
    const connection = this.connections.get(sessionId)
    if (!connection) return null
    
    return {
      connected: connection.eventSource?.readyState === EventSource.OPEN,
      reconnectAttempts: connection.reconnectAttempts,
      maxReconnectAttempts: connection.maxReconnectAttempts,
      isReconnecting: connection.isReconnecting,
      lastActivity: connection.lastActivity
    }
  }
  
  /**
   * Closes all active connections
   */
  closeAllConnections() {
    console.log("🔒 Closing all streaming connections")
    this.connections.forEach((_, sessionId) => {
      this.closeConnection(sessionId)
    })
  }
  
  /**
   * Performs health check on all connections and closes inactive ones
   */
  performHealthCheck() {
    const now = new Date()
    const timeoutMs = 5 * 60 * 1000 // 5 minutes
    
    this.connections.forEach((connection, sessionId) => {
      if (now.getTime() - connection.lastActivity.getTime() > timeoutMs) {
        console.log("⏰ Connection health check timeout for session:", sessionId)
        this.closeConnection(sessionId)
      }
    })
  }
}

// Export a singleton instance for use across the application
export const streamingManager = new StreamingConnectionManager() 