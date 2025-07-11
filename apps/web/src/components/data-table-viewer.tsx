"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Upload, Download, Search, MessageSquare, Wifi, WifiOff, Loader2, Sparkles, Plus } from "lucide-react"
import { useChatSessions } from "../hooks/use-chat-sessions"
import { useToast } from "../components/ui/use-toast"
import { useExperimentStore } from "../stores/experiment-store"
import { parseCSVData, getCSVHeaders } from "../data/placeholder"
import { websocketManager } from "../utils/streaming-connection-manager"
import { generateHeadersFromPlan } from "../api/dataclean"
import { convertTableToCSV } from "../utils/csv-utils"
import type { WebSocketMessage, WebSocketConnectionHandlers } from "../types/chat-types"

interface DataTableViewerProps {
  csvData?: string
}

export function DataTableViewer({ csvData }: DataTableViewerProps) {
  const [tableData, setTableData] = useState<Array<Record<string, string>>>([])
  const [headers, setHeaders] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [filteredData, setFilteredData] = useState<Array<Record<string, string>>>([])
  
  // WebSocket connection state
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<"disconnected" | "connecting" | "connected" | "error">("disconnected")
  const [conversationActive, setConversationActive] = useState(false)
  const [processingMessage, setProcessingMessage] = useState("")
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [pendingTransformations, setPendingTransformations] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)

  // Keep track of current session for WebSocket handlers
  const sessionRef = useRef<string | null>(null)

  // Existing hooks
  const { datacleanSession, updateDatacleanSession } = useChatSessions()
  const { currentExperiment, editorText, updateExperimentCsvWithSave, updateCsvFromDatacleanResponse } = useExperimentStore()
  const { toast } = useToast()

  // Existing useEffect hooks
  useEffect(() => {
    if (csvData) {
      const parsedData = parseCSVData(csvData)
      const csvHeaders = getCSVHeaders(csvData)
      setTableData(parsedData)
      setHeaders(csvHeaders)
      setFilteredData(parsedData)
    }
  }, [csvData])

  useEffect(() => {
    if (searchTerm) {
      const filtered = tableData.filter(row =>
        Object.values(row).some(value =>
          value.toLowerCase().includes(searchTerm.toLowerCase())
        )
      )
      setFilteredData(filtered)
    } else {
      setFilteredData(tableData)
    }
  }, [searchTerm, tableData])

  // Cleanup effect for timeout
  useEffect(() => {
    const currentTimeout = csvSyncTimeoutRef.current
    return () => {
      if (currentTimeout) {
        clearTimeout(currentTimeout)
      }
    }
  }, [])

  // Debounce ref for CSV sync
  const csvSyncTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const handleCellEdit = (id: string, field: string, value: string) => {
    setTableData(prev => {
      const newData = [...prev]  // copy the array
      const row = newData.find(r => r.id === id)
      if (row) {
        row[field] = value  // mutate the existing row object, preserving its reference
      }
      return newData
    })
  }

  const saveCellChanges = () => {
    // Clear any pending timeout
    if (csvSyncTimeoutRef.current) {
      clearTimeout(csvSyncTimeoutRef.current)
    }
    
    // Immediately save to database
    const csvString = convertTableToCSV(tableData, headers)
    updateExperimentCsvWithSave(csvString)
  }

  // Create a cell component to handle local state
  const EditableCell = ({ rowId, header, initialValue }: { rowId: string, header: string, initialValue: string }) => {
    const [value, setValue] = useState(initialValue)
    const [isFocused, setIsFocused] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    
    // Update local state when the initial value changes, but only if not focused
    useEffect(() => {
      if (!isFocused) {
        setValue(initialValue)
      }
    }, [initialValue, isFocused])
    
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      setValue(newValue)
      handleCellEdit(rowId, header, newValue)
    }
    
    const handleFocus = () => {
      setIsFocused(true)
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        // Save on Enter and blur the input
        e.preventDefault()
        saveCellChanges()
        inputRef.current?.blur()
      }
    }
    
    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      // Get the element that will receive focus
      const relatedTarget = e.relatedTarget as HTMLElement
      
      // Check if we're clicking within the DataTableViewer component
      const tableViewer = e.currentTarget.closest('.data-table-viewer')
      const clickedInsideTable = relatedTarget && tableViewer && tableViewer.contains(relatedTarget)
      
      // If clicking on any element inside the table viewer (including buttons), maintain focus
      if (clickedInsideTable) {
        e.preventDefault()
        // Use requestAnimationFrame to ensure the DOM has updated
        requestAnimationFrame(() => {
          inputRef.current?.focus()
        })
        return
      }
      
      // Only blur if clicking outside the entire table viewer
      setIsFocused(false)
      // Save changes when actually blurring
      saveCellChanges()
    }
    
    return (
      <Input
        ref={inputRef}
        value={value}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="border-0 bg-transparent p-0 h-auto text-xs focus-visible:ring-1 focus-visible:ring-blue-500"
        style={{
          fontFamily: 'ui-monospace, monospace',
          fontSize: '11px'
        }}
      />
    )
  }

  const handleGenerateHeaders = async () => {
    if (!editorText || !editorText.trim()) {
      toast({
        variant: "destructive",
        title: "No experimental plan",
        description: "Please add content to your experimental plan first.",
      })
      return
    }

    setIsGenerating(true)
    
    try {
      const response = await generateHeadersFromPlan(editorText, currentExperiment?.id)
      
      if (response.success) {
        setHeaders(response.headers)
        setTableData([]) // Start with empty table
        updateExperimentCsvWithSave(response.csv_data)
        
        toast({
          title: "Headers generated",
          description: `Successfully generated ${response.headers.length} headers from your experimental plan.`,
        })
      } else {
        toast({
          variant: "destructive",
          title: "Failed to generate headers",
          description: response.error_message || "An unexpected error occurred",
        })
      }
    } catch (error) {
      console.error("Failed to generate headers:", error)
      toast({
        variant: "destructive",
        title: "Failed to generate headers",
        description: error instanceof Error ? error.message : "An unexpected error occurred",
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleAddRow = () => {
    if (headers.length === 0) {
      toast({
        variant: "destructive",
        title: "No headers available",
        description: "Please generate headers first or load CSV data.",
      })
      return
    }

    const newId = (tableData.length ? Number(tableData[tableData.length-1].id) : 0) + 1
    const emptyRow = Object.fromEntries(headers.map(h => [h, ""]))
    const newRow = { id: newId.toString(), ...emptyRow }
    
    setTableData(prev => {
      const newData = [...prev, newRow]
      
      // Immediately sync to CSV
      const csvString = convertTableToCSV(newData, headers)
      updateExperimentCsvWithSave(csvString)
      
      return newData
    })
  }


  const generateSessionId = (): string => {
    return `csv-session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  // WebSocket message handlers
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    console.log("📥 CSV WebSocket message received:", message)
    
    try {
      switch (message.type) {
        case "csv_response":
          handleCSVResponse(message)
          break
          
        case "csv_approval_response":
          handleCSVApprovalResponse(message)
          break
          
        case "processing_status":
          setProcessingMessage(message.data.status as string || "")
          break
          
        case "error":
          console.error("WebSocket error:", message.data.message)
          toast({
            title: "WebSocket Error",
            description: message.data.message as string,
            variant: "destructive"
          })
          setProcessingMessage("")
          break
          
        case "pong":
          // Handle pong messages silently
          break
          
        default:
          console.log("Unknown message type:", message.type)
      }
    } catch (error) {
      console.error("Error handling WebSocket message:", error)
    }
  }, [])

  const handleWebSocketOpen = useCallback(() => {
    console.log("✅ CSV WebSocket connection opened")
    setIsConnected(true)
    setIsConnecting(false)
    setConnectionStatus("connected")
    
    toast({
      title: "Connected",
      description: "Real-time CSV processing connected",
      duration: 3000
    })
  }, [])

  const handleWebSocketError = useCallback((error: Event) => {
    console.error("❌ CSV WebSocket error:", error)
    setIsConnected(false)
    setIsConnecting(false)
    setConnectionStatus("error")
    
    toast({
      title: "Connection Error",
      description: "WebSocket connection failed",
      variant: "destructive"
    })
  }, [])

  const handleWebSocketClose = useCallback((event: CloseEvent) => {
    console.log("🔒 CSV WebSocket connection closed:", event)
    setIsConnected(false)
    setIsConnecting(false)
    setConnectionStatus("disconnected")
    
    if (!event.wasClean) {
      toast({
        title: "Connection Lost",
        description: "WebSocket connection was interrupted",
        variant: "destructive"
      })
    }
  }, [])

  // WebSocket connection management
  const connectWebSocket = useCallback((sessionId: string) => {
    console.log("🔗 Connecting to CSV WebSocket:", sessionId)
    setIsConnecting(true)
    setConnectionStatus("connecting")

    const wsUrl = `ws://localhost:8000/api/dataclean/csv-conversation/ws/${sessionId}`
    
    const handlers: WebSocketConnectionHandlers = {
      onMessage: handleWebSocketMessage,
      onOpen: handleWebSocketOpen,
      onError: handleWebSocketError,
      onClose: handleWebSocketClose
    }

    const connection = websocketManager.createConnection(sessionId, wsUrl, handlers, {
      maxReconnectAttempts: 3,
      reconnectDelay: 2000
    })

    if (connection) {
      sessionRef.current = sessionId
      updateDatacleanSession({ session_id: sessionId })
      return true
    } else {
      setIsConnecting(false)
      setConnectionStatus("error")
      return false
    }
  }, [handleWebSocketMessage, handleWebSocketOpen, handleWebSocketError, handleWebSocketClose, updateDatacleanSession])

  // Send WebSocket message
  const sendWebSocketMessage = useCallback((message: Record<string, unknown>) => {
    if (!sessionRef.current) {
      console.error("No active session for WebSocket message")
      return false
    }

    const websocketMessage: WebSocketMessage = {
      type: "csv_message",
      data: message,
      session_id: sessionRef.current,
      timestamp: new Date().toISOString()
    }

    return websocketManager.sendMessage(sessionRef.current, websocketMessage)
  }, [])

  // Enhanced conversation starter with WebSocket
  const handleStartConversation = useCallback(async () => {
    const csvString = convertTableToCSV(tableData, headers)
    
    if (!csvString) {
      toast({ title: "No data", description: "Please add some data first" })
      return
    }

    const sessionId = datacleanSession?.session_id || generateSessionId()
    
    try {
      // First establish WebSocket connection
      const connected = connectWebSocket(sessionId)
      
      if (!connected) {
        throw new Error("Failed to establish WebSocket connection")
      }

      // Wait for connection to be established
      const waitForConnection = new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error("Connection timeout"))
        }, 10000)

        const checkConnection = () => {
          if (isConnected) {
            clearTimeout(timeout)
            resolve()
          } else if (connectionStatus === "error") {
            clearTimeout(timeout)
            reject(new Error("Connection failed"))
          } else {
            setTimeout(checkConnection, 100)
          }
        }
        
        checkConnection()
      })

      await waitForConnection

      // Send initial CSV message via WebSocket
      const initialMessage = {
        csv_data: csvString,
        user_message: "Hi! I'd like to start cleaning this CSV data. Please analyze it and suggest improvements.",
        user_id: "demo-user"
      }

      const sent = sendWebSocketMessage(initialMessage)
      
      if (sent) {
        setConversationActive(true)
        setProcessingMessage("Starting conversation...")
        
        toast({ 
          title: "Conversation Started", 
          description: "Connected to CSV cleaning assistant via WebSocket" 
        })
      } else {
        throw new Error("Failed to send initial message")
      }

    } catch (error: unknown) {
      console.error("Failed to start CSV conversation via WebSocket", error)
      // Fallback to HTTP if WebSocket fails
      await handleStartConversationHTTP(csvString, sessionId)
    }
  }, [tableData, headers, toast, datacleanSession?.session_id, connectWebSocket, isConnected, connectionStatus, sendWebSocketMessage])

  // HTTP fallback (existing implementation)
  const handleStartConversationHTTP = async (csvString: string, sessionId: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/dataclean/csv-conversation/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          csv_data: csvString,
          user_message: "Hi! I'd like to start cleaning this CSV data.",
          session_id: sessionId,
          user_id: "demo-user"
        })
      })

      const result = await response.json()

      if (result.success) {
        updateDatacleanSession({ session_id: sessionId })
        handleCSVResponse({ data: result })
        setConversationActive(true)
        
        toast({ 
          title: "Conversation Started", 
          description: "Connected to CSV cleaning assistant (HTTP fallback)" 
        })
      } else {
        throw new Error(result.error_message || "Failed to start conversation")
      }
    } catch (error: unknown) {
      console.error("HTTP fallback failed", error)
      toast({ 
        title: "Connection failed", 
        description: error instanceof Error ? error.message : "Could not connect to CSV assistant", 
        variant: "destructive" 
      })
    }
  }

  // Enhanced CSV response handler
  const handleCSVResponse = useCallback((response: Record<string, unknown>) => {
    console.log("📊 Processing CSV response:", response)
    
    const data = response.data || response
    const { 
      original_csv, 
      cleaned_csv, 
      changes_made, 
      suggestions, 
      response_message,
      requires_approval,
      pending_transformations
    } = data
    
    // Handle approval requests
    if (requires_approval && pending_transformations) {
      setAwaitingApproval(true)
      setPendingTransformations(pending_transformations)
      
      toast({
        title: "Approval Required",
        description: `${pending_transformations.length} changes suggested. Please review and approve.`,
        duration: 6000
      })
    }
    
    // Update table data if CSV was cleaned
    if (cleaned_csv && cleaned_csv !== original_csv) {
      try {
        const lines = cleaned_csv.trim().split('\n')
        if (lines.length > 1) {
          const newHeaders = lines[0].split(',').map((h: string) => h.trim())
          const newData = lines.slice(1).map((line: string, index: number) => {
            const values = line.split(',').map((v: string) => v.trim().replace(/^"|"$/g, ''))
            const row: Record<string, string> = { id: (index + 1).toString() }
            newHeaders.forEach((header: string, i: number) => {
              row[header] = values[i] || ''
            })
            return row
          })
          
          setHeaders(newHeaders)
          setTableData(newData)
          setFilteredData(newData)
          
          // Update experiment store with new CSV
          updateCsvFromDatacleanResponse(cleaned_csv)
        }
      } catch (error) {
        console.error("Failed to parse cleaned CSV", error)
      }
    }
    
    // Show response message
    if (response_message) {
      toast({ 
        title: "Assistant Response", 
        description: response_message,
        duration: 5000
      })
    }
    
    // Show changes made
    if (changes_made && changes_made.length > 0) {
      toast({ 
        title: "Data Updated", 
        description: `Applied ${changes_made.length} changes: ${changes_made.join(', ')}`,
        duration: 4000
      })
    }
    
    // Log suggestions for future use
    if (suggestions && suggestions.length > 0) {
      console.log("💡 Suggestions received:", suggestions)
    }
    
    setProcessingMessage("")
  }, [toast, updateCsvFromDatacleanResponse])

  // Handle approval responses
  const handleCSVApprovalResponse = (message: WebSocketMessage) => {
    console.log("✅ CSV approval response received:", message)
    setAwaitingApproval(false)
    setPendingTransformations([])
    handleCSVResponse(message.data)
  }

  // Send approval response
  const sendApprovalResponse = useCallback((approved: boolean, feedback?: string) => {
    if (!sessionRef.current) {
      toast({
        title: "No active session",
        description: "Please start a conversation first",
        variant: "destructive"
      })
      return
    }

    const approvalMessage: WebSocketMessage = {
      type: "csv_approval",
      data: {
        approved,
        user_feedback: feedback,
        transformation_id: "pending", // Simple ID for now
        user_id: "demo-user"
      },
      session_id: sessionRef.current,
      timestamp: new Date().toISOString()
    }

    const sent = websocketManager.sendMessage(sessionRef.current, approvalMessage)
    
    if (sent) {
      setProcessingMessage("Processing your response...")
      toast({
        title: approved ? "Changes Approved" : "Changes Rejected",
        description: "Processing your response...",
        duration: 2000
      })
    } else {
      toast({
        title: "Failed to send response",
        description: "Please check your connection",
        variant: "destructive"
      })
    }
  }, [])


  // Handle download
  const handleDownload = () => {
    const csvContent = [headers.join(','), ...filteredData.map(row => 
      headers.map(header => row[header] || '').join(',')
    )].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cleaned_data.csv'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  return (
    <Card className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800 data-table-viewer" style={{ width: '40vw' }}>
      <CardHeader className="flex-shrink-0 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2 dark:text-white">
            <Upload className="h-4 w-4" />
            Data Table
            {tableData.length > 0 && (
              <span className="text-xs text-muted-foreground dark:text-gray-400">
                ({filteredData.length} of {tableData.length} rows)
              </span>
            )}
            
            {/* Connection Status Indicator */}
            {conversationActive && (
              <div className="flex items-center gap-1 ml-2">
                {isConnecting ? (
                  <Loader2 className="h-3 w-3 animate-spin text-yellow-500" />
                ) : isConnected ? (
                  <Wifi className="h-3 w-3 text-green-500" />
                ) : (
                  <WifiOff className="h-3 w-3 text-red-500" />
                )}
                <span className="text-xs text-muted-foreground">
                  {connectionStatus}
                </span>
              </div>
            )}
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="h-3 w-3 absolute left-2 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-32 h-6 text-xs pl-6 bg-transparent border-gray-300 dark:border-gray-600"
              />
            </div>
            
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 px-2 text-xs dark:text-gray-300 dark:hover:text-white"
              onClick={handleGenerateHeaders}
              disabled={isGenerating}
              title="Generate headers from experimental plan"
            >
              {isGenerating ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Sparkles className="h-3 w-3" />
              )}
            </Button>

            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 px-2 text-xs"
              onClick={handleStartConversation}
              disabled={isConnecting || conversationActive}
              title={conversationActive ? "Conversation active" : "Start CSV conversation"}
            >
              {isConnecting ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : conversationActive ? (
                <MessageSquare className="h-3 w-3 text-green-500" />
              ) : (
                <Upload className="h-3 w-3" />
              )}
            </Button>
            
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 px-2 text-xs"
              onClick={handleDownload}
              disabled={filteredData.length === 0}
            >
              <Download className="h-3 w-3" />
            </Button>
          </div>
        </div>
        
        {/* Processing Status */}
        {processingMessage && (
          <div className="flex items-center gap-2 mt-2 text-xs text-blue-600 dark:text-blue-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            {processingMessage}
          </div>
        )}
        
        {/* Approval Request */}
        {awaitingApproval && pendingTransformations.length > 0 && (
          <div className="mt-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-md border border-yellow-200 dark:border-yellow-700">
            <div className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-2">
              Approval Required
            </div>
            <div className="text-xs text-yellow-700 dark:text-yellow-300 mb-2">
              Suggested changes:
            </div>
            <ul className="text-xs text-yellow-600 dark:text-yellow-400 mb-3 list-disc list-inside">
              {pendingTransformations.map((transformation, index) => (
                <li key={index}>{transformation}</li>
              ))}
            </ul>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="default"
                className="h-6 px-3 text-xs"
                onClick={() => sendApprovalResponse(true)}
              >
                Approve
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-6 px-3 text-xs"
                onClick={() => sendApprovalResponse(false)}
              >
                Reject
              </Button>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <div className="flex-1 min-h-0 border-t dark:border-gray-700 overflow-auto max-w-full">
          {headers.length > 0 ? (
            <div className="w-full overflow-x-auto">
              <Table className="min-w-full">
              <TableHeader className="sticky top-0 bg-background dark:bg-gray-900">
                <TableRow className="border-b dark:border-gray-700">
                  {headers.map((header) => (
                    <TableHead 
                      key={header} 
                      className="text-xs font-semibold text-gray-900 dark:text-gray-100 px-3 py-2"
                    >
                      {header.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredData.map((row) => (
                  <TableRow 
                    key={row.id} 
                    className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    {headers.map((header) => (
                      <TableCell 
                        key={`${row.id}-${header}`} 
                        className="text-xs px-3 py-2 dark:text-gray-300"
                      >
                        <EditableCell 
                          rowId={row.id} 
                          header={header} 
                          initialValue={row[header] || ''} 
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
                
                {/* Add Row Button */}
                {headers.length > 0 && (
                  <TableRow className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                    <TableCell 
                      colSpan={headers.length} 
                      className="text-center py-3"
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleAddRow}
                        className="h-6 px-3 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Add Row
                      </Button>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
              </Table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-xs text-muted-foreground dark:text-gray-400">
              <div className="text-center">
                <Upload className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>Upload CSV data to view table</p>
                <p className="text-xs mt-1 opacity-75">Iris dataset loaded as placeholder</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
