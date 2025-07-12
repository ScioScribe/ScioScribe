"use client"

import React, { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Upload, Download, Search, Loader2, Sparkles, Plus, AlertCircle, Check, X } from "lucide-react"
import { useToast } from "../components/ui/use-toast"
import { useExperimentStore } from "../stores/experiment-store"
import { parseCSVData, getCSVHeaders } from "../data/placeholder"
import { generateHeadersFromPlan, uploadFile } from "../api/dataclean"
import { convertTableToCSV } from "../utils/csv-utils"
import { calculateCsvDiff, type RowDiff, type ChangeType } from "../utils/csv-diff"
import { extractCsvFromDatacleanResponse } from "../utils/dataclean-response"
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
  
  // Diff state
  const [csvDiff, setCsvDiff] = useState<Map<string, RowDiff>>(new Map())
  const [showDiff, setShowDiff] = useState(false)
  
  // File input ref
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Existing hooks
  const { 
    currentExperiment, 
    editorText, 
    updateExperimentCsvWithSave, 
    updateCsvFromDatacleanResponse,
    highlightRows,
    previousCsv,
    hasDiff,
    acceptCsvChanges,
    rejectCsvChanges
  } = useExperimentStore()
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
        
        console.log("🔍 DEBUG: Parsed CSV data")
        console.log("🔍 Row count:", parsedData.length)
        console.log("🔍 Headers:", csvHeaders)
        console.log("🔍 Sample row IDs:", parsedData.slice(0, 5).map(row => row.id))
        console.log("🔍 Sample rows:", parsedData.slice(0, 2))
        
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

  // Calculate diff when there are changes to show
  useEffect(() => {
    if (hasDiff && csvData && previousCsv) {
      try {
        console.log("🔍 DEBUG: Calculating CSV diff...")
        console.log("🔍 Current CSV preview:", csvData.substring(0, 200))
        console.log("🔍 Previous CSV preview:", previousCsv.substring(0, 200))
        
        const diffResult = calculateCsvDiff(csvData, previousCsv)
        console.log("🔍 DEBUG: Diff calculation complete")
        console.log("🔍 Diff map keys:", Array.from(diffResult.diffs.keys()))
        console.log("🔍 Diff map entries:", Array.from(diffResult.diffs.entries()).map(([k, v]) => `${k}: ${v.changeType}`))
        
        setCsvDiff(diffResult.diffs)
        setShowDiff(true)
      } catch (error) {
        console.error("Error calculating CSV diff:", error)
        setCsvDiff(new Map())
        setShowDiff(false)
      }
    } else {
      setCsvDiff(new Map())
      setShowDiff(false)
    }
  }, [hasDiff, csvData, previousCsv])

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

  // Utility functions for diff visualization
  const getRowChangeType = (row: Record<string, string>): ChangeType => {
    // Defensive check: ensure row has an ID
    if (!row?.id) {
      console.warn("🔍 WARNING: Row missing ID in getRowChangeType:", row)
      return 'unchanged'
    }
    
    // Use the actual row ID directly - no transformation needed!
    const rowId = row.id
    
    console.log("🔍 DEBUG getRowChangeType:", {
      rowId,
      diffMapHasKey: csvDiff.has(rowId),
      changeType: csvDiff.get(rowId)?.changeType,
      allDiffKeys: Array.from(csvDiff.keys()).slice(0, 10) // Show first 10 keys
    })
    
    // Defensive check: return unchanged if no diff data found
    const diff = csvDiff.get(rowId)
    return diff?.changeType || 'unchanged'
  }

  const getRowClassName = (row: Record<string, string>): string => {
    if (!showDiff) return ''
    
    const changeType = getRowChangeType(row)
    switch (changeType) {
      case 'added':
        return 'bg-green-100/50 border-l-2 border-green-300'
      case 'modified':
        return 'bg-yellow-100/50 border-l-2 border-yellow-300'
      case 'removed':
        return 'bg-red-100/50 border-l-2 border-red-300'
      default:
        return ''
    }
  }

  const getCellClassName = (row: Record<string, string>, fieldName: string): string => {
    if (!showDiff) return ''
    
    // Defensive check: ensure row has an ID and fieldName is provided
    if (!row?.id || !fieldName) {
      console.warn("🔍 WARNING: Missing row ID or fieldName in getCellClassName:", { rowId: row?.id, fieldName })
      return ''
    }
    
    // Use the actual row ID directly - no transformation needed!
    const rowId = row.id
    const diff = csvDiff.get(rowId)
    
    console.log("🔍 DEBUG getCellClassName:", {
      rowId,
      fieldName,
      diffMapHasKey: csvDiff.has(rowId),
      changeType: diff?.changeType,
      changedFields: diff?.changedFields,
      isFieldChanged: diff?.changedFields?.includes(fieldName)
    })
    
    // Defensive check: ensure diff exists and has modified status with changed fields
    if (diff?.changeType === 'modified' && diff.changedFields?.includes(fieldName)) {
      return 'bg-yellow-100/60'
    }
    
    return ''
  }

  // Calculate diff statistics
  const getDiffStats = () => {
    const stats = { added: 0, modified: 0, removed: 0, unchanged: 0 }
    
    csvDiff.forEach((diff) => {
      stats[diff.changeType]++
    })
    
    return stats
  }

  // Change summary component
  const ChangeSummary = () => {
    if (!showDiff) return null
    
    const stats = getDiffStats()
    const totalChanges = stats.added + stats.modified + stats.removed
    
    if (totalChanges === 0) return null
    
    return (
      <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded border border-blue-200 dark:border-blue-800">
        <AlertCircle className="h-3 w-3 text-blue-500" />
        <span>AI Changes:</span>
        {stats.added > 0 && (
          <span className="text-green-600 dark:text-green-400">+{stats.added} added</span>
        )}
        {stats.modified > 0 && (
          <span className="text-yellow-600 dark:text-yellow-400">~{stats.modified} modified</span>
        )}
        {stats.removed > 0 && (
          <span className="text-red-600 dark:text-red-400">-{stats.removed} removed</span>
        )}
      </div>
    )
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
        
        // Use agent versioning system for CSV updates from generateHeadersFromPlan
        try {
          // Convert GenerateHeadersResponse to DatacleanResponse format
          const datacleanResponse = {
            response_type: "data_preview" as const,
            message: "Headers generated successfully",
            data: {
              csv_data: response.csv_data,
              headers: response.headers
            }
          }
          await updateCsvFromDatacleanResponse(datacleanResponse)
          console.log("✅ Headers generated with agent versioning")
        } catch (csvError) {
          console.warn("⚠️ Failed to use agent versioning, falling back to direct update:", csvError)
          // Fallback to direct update if versioning fails
          if (response.csv_data) {
            updateExperimentCsvWithSave(response.csv_data)
          }
        }
        
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
      
      if (response.success) {
        console.log("📤 Processing upload response with agent versioning")
        
        // Use agent versioning system for file uploads
        try {
          // Convert ProcessFileCompleteResponse to DatacleanResponse format
          const datacleanResponse = {
            response_type: "data_preview" as const,
            message: "File uploaded successfully",
            data: {
              cleaned_data: response.cleaned_data,
              artifact_id: response.artifact_id
            }
          }
          await updateCsvFromDatacleanResponse(datacleanResponse)
          console.log("✅ File uploaded with agent versioning")
        } catch (csvError) {
          console.warn("⚠️ Failed to use agent versioning for upload, falling back to manual processing:", csvError)
          
          // Fallback to manual processing if versioning fails
          if (response.cleaned_data) {
            const csvContent = extractCsvFromDatacleanResponse(response, 'file-upload')
            if (csvContent) {
              await updateExperimentCsvWithSave(csvContent)
              console.log("✅ File uploaded with fallback processing")
            } else {
              throw new Error("No valid CSV data found in upload response")
            }
          } else {
            throw new Error("No cleaned_data in upload response")
          }
        }
        
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
    <Card className="h-full flex flex-col shadow-lg border-0 bg-card/95 backdrop-blur-sm data-table-viewer w-full">
      <CardHeader className="flex-shrink-0 pb-3 px-4 pt-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
              <div className="p-1.5 rounded-lg bg-green-100 dark:bg-green-900/30">
                <Upload className="h-4 w-4 text-green-600 dark:text-green-400" />
              </div>
              Data Table
              {tableData.length > 0 && (
                <span className="text-xs text-muted-foreground/70 font-normal">
                  ({filteredData.length} of {tableData.length} rows)
                </span>
              )}
            </CardTitle>
            <ChangeSummary />
          </div>
          
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

            {/* Accept/Reject Controls */}
            {showDiff && (
              <>
                <div className="w-px h-4 bg-muted" />
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="h-6 px-2 text-xs"
                  onClick={async () => {
                    try {
                      await acceptCsvChanges()
                      toast({
                        title: "Changes accepted",
                        description: "AI modifications have been accepted",
                      })
                    } catch {
                      toast({
                        title: "Error",
                        description: "Failed to accept changes",
                        variant: "destructive",
                      })
                    }
                  }}
                  title="Accept all AI changes"
                >
                  <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-green-500/20 text-green-600 dark:bg-green-400/20 mr-1">
                    <Check className="h-3 w-3" />
                  </span>
                  Accept
                </Button>
                
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="h-6 px-2 text-xs"
                  onClick={async () => {
                    try {
                      await rejectCsvChanges()
                      toast({
                        title: "Changes rejected",
                        description: "AI modifications have been reverted",
                      })
                    } catch {
                      toast({
                        title: "Error",
                        description: "Failed to reject changes",
                        variant: "destructive",
                      })
                    }
                  }}
                  title="Reject all AI changes"
                >
                  <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-red-500/20 text-red-600 dark:bg-red-400/20 mr-1">
                    <X className="h-3 w-3" />
                  </span>
                  Reject
                </Button>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 p-0 bg-gradient-to-b from-card to-muted/20">
        <div className="flex-1 min-h-0 border-t border-border/50 overflow-auto max-w-full backdrop-blur-sm">
          {headers.length > 0 ? (
            <div className="w-full overflow-x-auto">
              <Table className="min-w-full">
              <TableHeader className="sticky top-0 bg-background/95 backdrop-blur-sm">
                <TableRow className="border-b border-border/50">
                  {headers.map((header) => (
                    <TableHead 
                      key={header} 
                      className="text-xs font-semibold text-foreground px-3 py-3"
                    >
                      {header.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredData.map((row) => {
                  const rowChangeClass = getRowClassName(row)
                  return (
                    <TableRow 
                      key={row.id} 
                      className={cn(
                        "border-b border-border/30 hover:bg-muted/50 transition-colors",
                        highlightRows.has(row.id) && "bg-green-50 dark:bg-green-900/40",
                        rowChangeClass
                      )}
                    >
                      {headers.map((header) => {
                        const cellChangeClass = getCellClassName(row, header)
                        return (
                          <TableCell 
                            key={`${row.id}-${header}`} 
                            className={cn(
                              "text-xs px-3 py-2 text-foreground/90",
                              cellChangeClass
                            )}
                          >
                            <EditableCell 
                              rowId={row.id} 
                              header={header} 
                              initialValue={row[header] || ''} 
                            />
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  )
                })}
                
                {/* Add Row Button */}
                {headers.length > 0 && (
                  <TableRow className="border-b border-border/30 hover:bg-muted/30 transition-colors">
                    <TableCell 
                      colSpan={headers.length} 
                      className="text-center py-3"
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleAddRow}
                        className="h-6 px-3 text-xs text-muted-foreground hover:text-foreground transition-colors"
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
