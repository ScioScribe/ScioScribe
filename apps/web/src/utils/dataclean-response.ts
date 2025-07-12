/**
 * Dataclean Response Utilities
 * 
 * Provides utilities to normalize and extract CSV data from various
 * dataclean API response formats.
 */

export interface NormalizedCsvData {
  csvString: string | null
  source: 'cleaned_csv' | 'cleaned_data' | 'csv_data' | 'data' | 'none'
  wasArray: boolean
}

/**
 * Array to CSV conversion utility
 */
function convertArrayToCsv(data: Array<Record<string, unknown>>): string {
  try {
    if (!data || data.length === 0) return ""
    
    // Get headers from first object
    const headers = Object.keys(data[0])
    
    // Create CSV content
    let csvContent = headers.join(',') + '\n'
    
    // Add data rows
    data.forEach(row => {
      const values = headers.map(header => {
        const value = row[header]
        // Escape commas and quotes in values
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`
        }
        return value || ''
      })
      csvContent += values.join(',') + '\n'
    })
    
    return csvContent
  } catch (error) {
    console.error("❌ Error converting array to CSV:", error)
    return ""
  }
}

/**
 * Normalize dataclean API response to extract CSV data
 * 
 * Handles multiple response formats:
 * - response.data.cleaned_csv (string)
 * - response.data.cleaned_data (array or string) 
 * - response.data.csv_data (string)
 * - response.cleaned_csv (string)
 * - response.csv_data (string)
 * - response.data (string or array - direct CSV data)
 */
export function normalizeCsvFromDatacleanResponse(response: unknown): NormalizedCsvData {
  const result: NormalizedCsvData = {
    csvString: null,
    source: 'none',
    wasArray: false
  }

  if (!response || typeof response !== 'object') {
    return result
  }

  const resp = response as Record<string, unknown>

  // Try to extract from nested data object first
  if (resp.data && typeof resp.data === 'object') {
    const data = resp.data as Record<string, unknown>
    
    // Priority 1: response.data.cleaned_csv (most specific)
    if (typeof data.cleaned_csv === 'string' && data.cleaned_csv.trim()) {
      result.csvString = data.cleaned_csv.trim()
      result.source = 'cleaned_csv'
      return result
    }
    
    // Priority 2: response.data.cleaned_data (could be array or string)
    if (data.cleaned_data) {
      if (typeof data.cleaned_data === 'string' && data.cleaned_data.trim()) {
        result.csvString = data.cleaned_data.trim()
        result.source = 'cleaned_data'
        return result
      }
      if (Array.isArray(data.cleaned_data) && data.cleaned_data.length > 0) {
        result.csvString = convertArrayToCsv(data.cleaned_data as Array<Record<string, unknown>>)
        result.source = 'cleaned_data'
        result.wasArray = true
        return result
      }
    }
    
    // Priority 3: response.data.csv_data
    if (typeof data.csv_data === 'string' && data.csv_data.trim()) {
      result.csvString = data.csv_data.trim()
      result.source = 'csv_data'
      return result
    }
  }
  
  // Try direct fields on response object
  // Priority 4: response.cleaned_csv
  if (typeof resp.cleaned_csv === 'string' && resp.cleaned_csv.trim()) {
    result.csvString = resp.cleaned_csv.trim()
    result.source = 'cleaned_csv'
    return result
  }
  
  // Priority 5: response.csv_data
  if (typeof resp.csv_data === 'string' && resp.csv_data.trim()) {
    result.csvString = resp.csv_data.trim()
    result.source = 'csv_data'
    return result
  }
  
  // Priority 6: response.data as direct CSV (legacy fallback)
  if (typeof resp.data === 'string' && resp.data.trim()) {
    result.csvString = resp.data.trim()
    result.source = 'data'
    return result
  }
  
  // Priority 7: response.data as array (legacy fallback)
  if (Array.isArray(resp.data) && resp.data.length > 0) {
    result.csvString = convertArrayToCsv(resp.data as Array<Record<string, unknown>>)
    result.source = 'data'
    result.wasArray = true
    return result
  }

  return result
}

/**
 * Extract CSV data from dataclean response with logging
 * 
 * @param response - The dataclean API response
 * @param context - Optional context for logging (e.g., endpoint name)
 * @returns CSV string or null if not found
 */
export function extractCsvFromDatacleanResponse(
  response: unknown, 
  context: string = 'unknown'
): string | null {
  const normalized = normalizeCsvFromDatacleanResponse(response)
  
  if (normalized.csvString) {
    console.log(`✅ Extracted CSV from ${context}:`, {
      source: normalized.source,
      wasArray: normalized.wasArray,
      length: normalized.csvString.length,
      preview: normalized.csvString.substring(0, 100)
    })
    return normalized.csvString
  } else {
    console.warn(`⚠️ No CSV data found in ${context} response:`, {
      responseKeys: response && typeof response === 'object' ? Object.keys(response) : 'not-object',
      hasData: response && typeof response === 'object' && 'data' in response,
      dataKeys: response && typeof response === 'object' && 'data' in response && typeof (response as Record<string, unknown>).data === 'object' 
        ? Object.keys((response as Record<string, unknown>).data as Record<string, unknown>) 
        : 'no-data-object'
    })
    return null
  }
}

/**
 * Validate CSV data format
 */
export function validateCsvData(csvString: string): {
  isValid: boolean
  error?: string
  rowCount?: number
  columnCount?: number
} {
  if (!csvString || typeof csvString !== 'string') {
    return { isValid: false, error: 'CSV data is not a string' }
  }

  const trimmed = csvString.trim()
  if (!trimmed) {
    return { isValid: false, error: 'CSV data is empty' }
  }

  try {
    const lines = trimmed.split('\n')
    if (lines.length < 1) {
      return { isValid: false, error: 'CSV must have at least a header row' }
    }

    const headerColumns = lines[0].split(',').length
    if (headerColumns < 1) {
      return { isValid: false, error: 'CSV header must have at least one column' }
    }

    // Check if all rows have same number of columns (basic validation)
    for (let i = 1; i < Math.min(lines.length, 10); i++) { // Check first 10 rows
      const columnCount = lines[i].split(',').length
      if (columnCount !== headerColumns) {
        console.warn(`⚠️ Row ${i + 1} has ${columnCount} columns, expected ${headerColumns}`)
      }
    }

    return {
      isValid: true,
      rowCount: lines.length - 1, // excluding header
      columnCount: headerColumns
    }
  } catch (error) {
    return {
      isValid: false,
      error: `CSV parsing error: ${error instanceof Error ? error.message : 'unknown error'}`
    }
  }
}