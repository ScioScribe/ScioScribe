"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Upload, Download, Search, Filter } from "lucide-react"
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

  const handleUpload = () => {
    console.log("📁 Upload functionality would be implemented here")
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
              onClick={handleUpload}
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
