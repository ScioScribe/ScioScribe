"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Upload, Download, Search, Loader2, Sparkles, Plus } from "lucide-react"
import { useToast } from "../components/ui/use-toast"
import { useExperimentStore } from "../stores/experiment-store"
import { parseCSVData, getCSVHeaders } from "../data/placeholder"
import { generateHeadersFromPlan, uploadFile } from "../api/dataclean"
import { convertTableToCSV } from "../utils/csv-utils"
import { cn } from "../shared/utils"

interface DataTableViewerProps {
  csvData?: string
}

export function DataTableViewer({ csvData }: DataTableViewerProps) {
  const [tableData, setTableData] = useState<Array<Record<string, string>>>([])
  const [headers, setHeaders] = useState<string[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [filteredData, setFilteredData] = useState<Array<Record<string, string>>>([])
  
  const [isGenerating, setIsGenerating] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  
  // File input ref
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Existing hooks
  const { currentExperiment, editorText, updateExperimentCsvWithSave, highlightRows } = useExperimentStore()
  const { toast } = useToast()

  // Existing useEffect hooks
  useEffect(() => {
    console.log("📊 DataTableViewer received csvData update:", csvData?.substring(0, 100))
    
    if (csvData) {
      try {
        // Ensure csvData is a string before parsing
        if (typeof csvData !== 'string') {
          console.error("csvData is not a string:", typeof csvData, csvData)
          setTableData([])
          setHeaders([])
          setFilteredData([])
          return
        }
        
        const parsedData = parseCSVData(csvData)
        const csvHeaders = getCSVHeaders(csvData)
        setTableData(parsedData)
        setHeaders(csvHeaders)
        setFilteredData(parsedData)
      } catch (error) {
        console.error("Error parsing CSV data:", error)
        setTableData([])
        setHeaders([])
        setFilteredData([])
      }
    } else {
      // Clear data when csvData is empty
      setTableData([])
      setHeaders([])
      setFilteredData([])
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

  const saveCellChanges = (rowId: string, header: string, newValue: string) => {
    // Update the table data
    handleCellEdit(rowId, header, newValue)
    
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
    }
    
    const handleFocus = () => {
      setIsFocused(true)
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        // Save on Enter and blur the input
        e.preventDefault()
        saveCellChanges(rowId, header, value)
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
      saveCellChanges(rowId, header, value)
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    const validTypes = ['.csv', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    
    if (!validTypes.includes(fileExtension)) {
      toast({
        variant: "destructive",
        title: "Invalid file type",
        description: "Please upload a CSV, PDF, or image file (PNG, JPG, etc.)",
      })
      return
    }

    setIsUploading(true)

    try {
      const response = await uploadFile(file, currentExperiment?.id || "demo-experiment", "csv")
      
      if (response.success && response.cleaned_data) {
        let csvContent: string
        
        // Handle case where cleaned_data might be an array of objects instead of CSV string
        if (typeof response.cleaned_data === 'string') {
          csvContent = response.cleaned_data
        } else if (Array.isArray(response.cleaned_data)) {
          // Convert array of objects to CSV string
          const data = response.cleaned_data as Array<Record<string, any>>
          if (data.length > 0) {
            const headers = Object.keys(data[0])
            const rows = data.map(row => 
              headers.map(header => {
                const value = row[header]
                // Handle values that contain commas or quotes
                if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                  return `"${value.replace(/"/g, '""')}"`
                }
                return value
              }).join(',')
            )
            csvContent = [headers.join(','), ...rows].join('\n')
          } else {
            throw new Error("No data returned from file processing")
          }
        } else {
          throw new Error("Unexpected data format returned from server")
        }
        
        console.log("📤 Uploading CSV to experiment store:", csvContent.substring(0, 100) + "...")
        
        // Update the experiment with the new CSV data
        // This will trigger the useEffect to update the local state
        await updateExperimentCsvWithSave(csvContent)
        
        console.log("✅ CSV uploaded to experiment store")
        
        toast({
          title: "File uploaded successfully",
          description: `Processed ${file.name} successfully`,
        })
      } else {
        throw new Error(response.error_message || "Failed to process file")
      }
    } catch (error) {
      console.error("File upload failed:", error)
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Failed to upload file",
      })
    } finally {
      setIsUploading(false)
      // Reset the input
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

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
    <Card className="h-full flex flex-col dark:bg-gray-900 dark:border-gray-800 data-table-viewer w-full">
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

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.pdf,.png,.jpg,.jpeg,.gif,.bmp"
              onChange={handleFileUpload}
              className="hidden"
            />
            
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 px-2 text-xs dark:text-gray-300 dark:hover:text-white"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              title="Upload CSV, PDF, or image file"
            >
              {isUploading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Upload className="h-3 w-3" />
              )}
            </Button>
            
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
              onClick={handleDownload}
              disabled={filteredData.length === 0}
            >
              <Download className="h-3 w-3" />
            </Button>
          </div>
        </div>
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
                    className={cn(
                      "border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800",
                      highlightRows.has(row.id) && "bg-green-50 dark:bg-green-900/40"
                    )}
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
