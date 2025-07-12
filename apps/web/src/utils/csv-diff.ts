/**
 * CSV Diff Utility
 * 
 * Provides utilities to calculate row-level differences between CSV data,
 * supporting change detection for AI agent modifications.
 */

import { parseCSVData } from '@/data/placeholder'

export type ChangeType = 'added' | 'removed' | 'modified' | 'unchanged'

export interface RowDiff {
  rowIndex: number
  changeType: ChangeType
  currentData?: Record<string, string>
  previousData?: Record<string, string>
  changedFields?: string[]
}

export interface CsvDiffResult {
  diffs: Map<string, RowDiff>
  stats: {
    added: number
    removed: number
    modified: number
    unchanged: number
  }
  headers: string[]
}



/**
 * Create a unique key for a row based on its content
 */
function createRowKey(row: Record<string, string>, headers: string[]): string {
  return headers.map(header => row[header] || '').join('|')
}

/**
 * Compare two rows and find changed fields
 */
function compareRows(current: Record<string, string>, previous: Record<string, string>, headers: string[]): string[] {
  const changedFields: string[] = []
  
  for (const header of headers) {
    if ((current[header] || '') !== (previous[header] || '')) {
      changedFields.push(header)
    }
  }
  
  return changedFields
}

/**
 * Calculate differences between current and previous CSV data
 * Now uses actual row IDs from parsed data instead of synthetic indices
 */
export function calculateCsvDiff(currentCsv: string, previousCsv: string): CsvDiffResult {
  // Parse both CSVs using the same parsing logic that creates row IDs
  const currentRows = parseCSVData(currentCsv)
  const previousRows = parseCSVData(previousCsv)
  
  console.log("🔍 DEBUG calculateCsvDiff: Current rows sample:", currentRows.slice(0, 3).map(r => ({ id: r.id, keys: Object.keys(r) })))
  console.log("🔍 DEBUG calculateCsvDiff: Previous rows sample:", previousRows.slice(0, 3).map(r => ({ id: r.id, keys: Object.keys(r) })))
  
  // Use headers from current CSV (assumes structure is maintained)
  const headers = currentCsv.trim() ? 
    currentCsv.trim().split('\n')[0].split(',').map(h => h.trim().replace(/^"|"$/g, '')) : []
  
  if (headers.length === 0) {
    return {
      diffs: new Map(),
      stats: { added: 0, removed: 0, modified: 0, unchanged: 0 },
      headers: []
    }
  }
  
  const diffs = new Map<string, RowDiff>()
  const stats = { added: 0, removed: 0, modified: 0, unchanged: 0 }
  
  // Create maps for efficient lookup using content-based keys
  const previousRowMap = new Map<string, { row: Record<string, string>, index: number }>()
  previousRows.forEach((row, index) => {
    const key = createRowKey(row, headers)
    previousRowMap.set(key, { row, index })
  })
  
  const currentRowMap = new Map<string, { row: Record<string, string>, index: number }>()
  currentRows.forEach((row, index) => {
    const key = createRowKey(row, headers)
    currentRowMap.set(key, { row, index })
  })
  
  // Find added and modified rows - use actual row.id from parsed data
  currentRows.forEach((currentRow, currentIndex) => {
    const key = createRowKey(currentRow, headers)
    const rowId = currentRow.id // Use actual row ID from parsed data instead of synthetic index
    
    console.log("🔍 DEBUG: Processing row", { rowId, currentIndex, contentKey: key.substring(0, 50) })
    
    if (!previousRowMap.has(key)) {
      // Row is new (added)
      diffs.set(rowId, {
        rowIndex: currentIndex,
        changeType: 'added',
        currentData: currentRow
      })
      stats.added++
      console.log("🔍 DEBUG: Added row", rowId)
    } else {
      // Row exists, check if modified
      const previousEntry = previousRowMap.get(key)!
      const changedFields = compareRows(currentRow, previousEntry.row, headers)
      
      if (changedFields.length > 0) {
        diffs.set(rowId, {
          rowIndex: currentIndex,
          changeType: 'modified',
          currentData: currentRow,
          previousData: previousEntry.row,
          changedFields
        })
        stats.modified++
        console.log("🔍 DEBUG: Modified row", rowId, "fields:", changedFields)
      } else {
        diffs.set(rowId, {
          rowIndex: currentIndex,
          changeType: 'unchanged',
          currentData: currentRow,
          previousData: previousEntry.row
        })
        stats.unchanged++
      }
    }
  })
  
  // Find removed rows
  previousRows.forEach((previousRow) => {
    const key = createRowKey(previousRow, headers)
    
    if (!currentRowMap.has(key)) {
      // Row was removed - use actual row ID with a prefix to avoid conflicts
      const rowId = `removed-${previousRow.id}`
      diffs.set(rowId, {
        rowIndex: -1, // Removed rows don't have a current index
        changeType: 'removed',
        previousData: previousRow
      })
      stats.removed++
      console.log("🔍 DEBUG: Removed row", rowId)
    }
  })
  
  console.log("🔍 DEBUG calculateCsvDiff complete:")
  console.log("🔍 Final diff map keys:", Array.from(diffs.keys()))
  console.log("🔍 Stats:", stats)
  
  return {
    diffs,
    stats,
    headers
  }
}

/**
 * Get row IDs by change type
 */
export function getRowIdsByType(diffs: Map<string, RowDiff>, changeType: ChangeType): string[] {
  return Array.from(diffs.entries())
    .filter(([, diff]) => diff.changeType === changeType)
    .map(([rowId]) => rowId)
}

/**
 * Check if there are any pending changes
 */
export function hasPendingChanges(diffs: Map<string, RowDiff>): boolean {
  return Array.from(diffs.values()).some(diff => diff.changeType !== 'unchanged')
}

/**
 * Get change summary text
 */
export function getChangeSummary(stats: CsvDiffResult['stats']): string {
  const parts: string[] = []
  
  if (stats.added > 0) parts.push(`${stats.added} added`)
  if (stats.modified > 0) parts.push(`${stats.modified} modified`) 
  if (stats.removed > 0) parts.push(`${stats.removed} removed`)
  
  if (parts.length === 0) return 'No changes'
  
  return parts.join(', ')
}