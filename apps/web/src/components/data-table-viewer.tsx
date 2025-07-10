"use client"

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload, Download, Search } from "lucide-react"
import { uploadCsvFile } from "@/api/dataclean"
import { useChatSessions } from "@/hooks/use-chat-sessions"
import { useToast } from "@/components/ui/use-toast"
import { useExperimentStore } from "@/stores/experiment-store"
import { parseCSVData, getCSVHeaders } from "@/data/placeholder"

interface DataTableViewerProps {
  csvData?: string
}

export function DataTableViewer({ csvData }: DataTableViewerProps) {
  const [tableData, setTableData] = useState<Array<Record<string, string>>>([])
  const [headers, setHeaders] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [filteredData, setFilteredData] = useState<Array<Record<string, string>>>([])

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

  const handleCellEdit = (id: string, field: string, value: string) => {
    setTableData(prev => prev.map(row => 
      row.id === id ? { ...row, [field]: value } : row
    ))
  }

  const { datacleanSession, updateDatacleanSession } = useChatSessions()
  const { currentExperiment, csvData: storeCsv } = useExperimentStore()
  const { toast } = useToast()

  const convertTableToCSV = (data: Array<Record<string, string>>, headers: string[]): string => {
    if (!headers.length || !data.length) return ""
    
    const csvHeaders = headers.join(',')
    const csvRows = data.map(row => 
      headers.map(header => `"${(row[header] || '').replace(/"/g, '""')}"`).join(',')
    )
    
    return [csvHeaders, ...csvRows].join('\n')
  }

  const generateSessionId = (): string => {
    return `csv-session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  const handleStartConversation = async () => {
    const csvString = convertTableToCSV(tableData, headers)
    
    if (!csvString) {
      toast({ title: "No data", description: "Please add some data first" })
      return
    }

    // Get or create session ID
    const sessionId = datacleanSession?.session_id || generateSessionId()
    
    try {
      // For now, use HTTP endpoint (WebSocket integration will be added in Task 3.2)
      const response = await fetch('/api/dataclean/csv-conversation/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          csv_data: csvString,
          user_message: "Hi",
          session_id: sessionId,
          user_id: "demo-user"
        })
      })

      const result = await response.json()

      if (result.success) {
        // Update session state
        updateDatacleanSession({ session_id: sessionId })
        
        // Handle CSV response
        handleCSVResponse({ data: result })
        
        toast({ 
          title: "Conversation Started", 
          description: "Connected to CSV cleaning assistant" 
        })
      } else {
        throw new Error(result.error_message || "Failed to start conversation")
      }
    } catch (error: any) {
      console.error("Failed to start CSV conversation", error)
      toast({ 
        title: "Connection failed", 
        description: error?.message || "Could not connect to CSV assistant", 
        variant: "destructive" 
      })
    }
  }

  const handleCSVResponse = (response: any) => {
    const { original_csv, cleaned_csv, changes_made, suggestions, response_message } = response.data
    
    if (cleaned_csv && cleaned_csv !== original_csv) {
      // Parse cleaned CSV and update table
      try {
        const lines = cleaned_csv.trim().split('\n')
        if (lines.length > 1) {
          const newHeaders = lines[0].split(',').map((h: string) => h.trim())
          const newData = lines.slice(1).map((line: string, index: number) => {
            const values = line.split(',').map((v: string) => v.trim().replace(/^"|"$/g, ''))
            const row: Record<string, string> = { id: (index + 1).toString() }
            newHeaders.forEach((header, i) => {
              row[header] = values[i] || ''
            })
            return row
          })
          
          setHeaders(newHeaders)
          setTableData(newData)
          setFilteredData(newData)
        }
      } catch (error) {
        console.error("Failed to parse cleaned CSV", error)
      }
    }
    
    // Show response message if provided
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
    
    // Show suggestions
    if (suggestions && suggestions.length > 0) {
      console.log("💡 Suggestions received:", suggestions)
    }
  }

  const handleDownload = () => {
    const csvContent = [headers.join(','), ...filteredData.map(row => 
      headers.map(header => row[header] || '').join(',')
    )].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'iris_dataset.csv'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  return (
    <Card className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800">
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
              className="h-6 px-2 text-xs"
              onClick={handleStartConversation}
              title="Start CSV conversation"
            >
              <Upload className="h-3 w-3" />
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
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <div className="flex-1 min-h-0 border-t dark:border-gray-700 overflow-auto">
          {tableData.length > 0 ? (
            <Table>
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
                        <Input
                          value={row[header] || ''}
                          onChange={(e) => handleCellEdit(row.id, header, e.target.value)}
                          className="border-0 bg-transparent p-0 h-auto text-xs focus-visible:ring-1 focus-visible:ring-blue-500"
                          style={{
                            fontFamily: 'ui-monospace, monospace',
                            fontSize: '11px'
                          }}
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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
