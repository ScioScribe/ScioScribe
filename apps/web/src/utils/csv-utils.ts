/**
 * CSV Utilities
 * 
 * Utility functions for working with CSV data across the application.
 * These functions provide a consistent way to access and convert CSV data.
 */

import { useExperimentStore } from '../stores/experiment-store'

/**
 * Gets the current CSV data from the experiment store
 * This is the same data source used by DataTableViewer
 * 
 * @returns CSV data as string or empty string if not available
 */
export function getCurrentCsvData(): string {
  try {
    const store = useExperimentStore.getState()
    const csvData = store.csvData || ""
    
    console.log("🔍 getCurrentCsvData - CSV length:", csvData.length)
    if (csvData.length > 0) {
      console.log("🔍 getCurrentCsvData - CSV preview:", csvData.substring(0, 100))
    }
    
    return csvData
  } catch (error) {
    console.error("❌ Error getting current CSV data:", error)
    return ""
  }
}

/**
 * Converts table data to CSV string format
 * Same logic as used in DataTableViewer
 * 
 * @param data Array of record objects
 * @param headers Array of column headers
 * @returns CSV string
 */
export function convertTableToCSV(data: Array<Record<string, string>>, headers: string[]): string {
  if (!headers.length) {
    return ""
  }
  
  // If no data, return just headers
  if (!data.length) {
    return headers.join(',') + '\n'
  }
  
  const csvHeaders = headers.join(',')
  const csvRows = data.map(row => 
    headers.map(header => {
      const value = row[header] || ''
      // Only quote if value contains comma, newline, or quotes
      if (value.includes(',') || value.includes('\n') || value.includes('"')) {
        return `"${value.replace(/"/g, '""')}"`
      }
      return value
    }).join(',')
  )
  
  return [csvHeaders, ...csvRows].join('\n')
}

/**
 * Parses CSV string into table data
 * Basic CSV parsing utility
 * 
 * @param csvString CSV data as string
 * @returns Object with headers and data arrays
 */
export function parseCSVString(csvString: string): { headers: string[], data: Array<Record<string, string>> } {
  try {
    if (!csvString.trim()) {
      return { headers: [], data: [] }
    }
    
    const lines = csvString.trim().split('\n')
    if (lines.length < 2) {
      return { headers: [], data: [] }
    }
    
    const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
    const data = lines.slice(1).map((line, index) => {
      const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
      const row: Record<string, string> = { id: (index + 1).toString() }
      headers.forEach((header, i) => {
        row[header] = values[i] || ''
      })
      return row
    })
    
    return { headers, data }
  } catch {
    console.error("❌ Error parsing CSV string")
    return { headers: [], data: [] }
  }
}

/**
 * Validates if a string contains valid CSV data
 * 
 * @param csvString String to validate
 * @returns Boolean indicating if valid CSV
 */
export function isValidCSV(csvString: string): boolean {
  try {
    if (!csvString.trim()) return false
    
    const lines = csvString.trim().split('\n')
    if (lines.length < 2) return false
    
    const headerCount = lines[0].split(',').length
    return headerCount > 0 && lines.slice(1).every(line => line.split(',').length === headerCount)
  } catch {
    return false
  }
}

/**
 * Gets CSV data with multiple fallback mechanisms
 * Designed for use in message handlers and API calls
 * 
 * @param contextCsv Optional CSV data from context
 * @returns CSV data string
 */
export function getCsvDataWithFallbacks(contextCsv?: string): string {
  // Primary: Use context CSV if provided and valid
  if (contextCsv && contextCsv.trim() && isValidCSV(contextCsv)) {
    console.log("✅ Using CSV data from context")
    return contextCsv
  }
  
  // Fallback: Get from experiment store
  const storeCSV = getCurrentCsvData()
  if (storeCSV && storeCSV.trim() && isValidCSV(storeCSV)) {
    console.log("✅ Using CSV data from experiment store")
    return storeCSV
  }
  
  console.warn("⚠️ No valid CSV data available from any source")
  return ""
}

/**
 * Parses headers from a CSV string
 * 
 * @param csv CSV string to extract headers from
 * @returns Array of header names
 */
export function parseHeadersFromCsv(csv: string): string[] {
  try {
    if (!csv.trim()) return []
    
    const lines = csv.trim().split('\n')
    if (lines.length === 0) return []
    
    // Get first line and parse headers
    const headerLine = lines[0]
    return headerLine.split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  } catch (error) {
    console.error("❌ Error parsing headers from CSV:", error)
    return []
  }
} 