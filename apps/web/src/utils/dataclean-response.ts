/**
 * Data Cleaning Response Utilities - Simplified Version
 * 
 * This module provides utilities for extracting and processing CSV data
 * from data cleaning API responses.
 */

import { DataProcessResponse } from '@/api/dataclean';

/**
 * Extract CSV data from various response formats
 * Returns the CSV string or null if not found
 */
export function extractCsvFromDatacleanResponse(response: any, source: string = 'unknown'): string | null {
  console.log(`🔍 [${source}] Extracting CSV from response:`, response ? 'Object received' : 'No response')
  
  if (!response) {
    console.warn(`⚠️ [${source}] Response is null or undefined`)
    return null
  }
  
  // Handle new simplified DataProcessResponse format
  if ('csv_data' in response && response.csv_data) {
    console.log(`✅ [${source}] Found csv_data in response`)
    return response.csv_data
  }
  
  // Handle upload response format (cleaned_data field)
  if ('cleaned_data' in response && response.cleaned_data) {
    console.log(`✅ [${source}] Found cleaned_data in response`)
    return response.cleaned_data
  }
  
  // Handle legacy formats for backward compatibility
  if (response.data) {
    // Check for cleaned_csv in data object
    if (typeof response.data === 'object' && response.data.cleaned_csv) {
      console.log(`✅ [${source}] Found cleaned_csv in data object`)
      return response.data.cleaned_csv
    }
    
    // Check for original_csv in data object
    if (typeof response.data === 'object' && response.data.original_csv) {
      console.log(`✅ [${source}] Found original_csv in data object`)
      return response.data.original_csv
    }
    
    // Check if data itself is CSV string
    if (typeof response.data === 'string' && response.data.includes(',')) {
      console.log(`✅ [${source}] Data appears to be CSV string`)
      return response.data
    }
    
    // Check for nested csv_data in data
    if (typeof response.data === 'object' && response.data.csv_data) {
      console.log(`✅ [${source}] Found csv_data in data object`)
      return response.data.csv_data
    }
    
    // Check for nested cleaned_data in data
    if (typeof response.data === 'object' && response.data.cleaned_data) {
      console.log(`✅ [${source}] Found cleaned_data in data object`)
      return response.data.cleaned_data
    }
  }
  
  // Direct properties on response
  if (response.cleaned_csv) {
    console.log(`✅ [${source}] Found cleaned_csv directly on response`)
    return response.cleaned_csv
  }
  
  if (response.cleaned_data) {
    console.log(`✅ [${source}] Found cleaned_data directly on response`)
    return response.cleaned_data
  }
  
  if (response.original_csv) {
    console.log(`✅ [${source}] Found original_csv directly on response`)
    return response.original_csv
  }
  
  // Check if response itself is a CSV string
  if (typeof response === 'string' && response.includes(',') && response.includes('\n')) {
    console.log(`✅ [${source}] Response itself appears to be CSV string`)
    return response
  }
  
  console.warn(`⚠️ [${source}] No CSV data found in response`)
  return null
}

/**
 * Validate CSV data structure
 */
export function validateCsvData(csvData: string): {
  isValid: boolean
  error?: string
  rowCount?: number
  columnCount?: number
} {
  if (!csvData || typeof csvData !== 'string') {
    return { isValid: false, error: 'CSV data is empty or not a string' }
  }
  
  const lines = csvData.trim().split('\n')
  if (lines.length < 2) {
    return { isValid: false, error: 'CSV must have at least a header and one data row' }
  }
  
  const header = lines[0].split(',')
  const columnCount = header.length
  
  if (columnCount === 0) {
    return { isValid: false, error: 'CSV header has no columns' }
  }
  
  // Check if all rows have the same number of columns
  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(',')
    if (row.length !== columnCount) {
      return { 
        isValid: false, 
        error: `Row ${i + 1} has ${row.length} columns but header has ${columnCount} columns` 
      }
    }
  }
  
  return {
    isValid: true,
    rowCount: lines.length - 1, // Exclude header
    columnCount
  }
}