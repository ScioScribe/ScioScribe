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
 * Uses position-based matching to ensure row IDs align with table rendering
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
  
  // Position-based comparison: compare rows at the same index first
  const maxLength = Math.max(currentRows.length, previousRows.length)
  
  for (let i = 0; i < maxLength; i++) {
    const currentRow = currentRows[i]
    const previousRow = previousRows[i]
    
    if (currentRow && previousRow) {
      // Both rows exist - check if modified
      const changedFields = compareRows(currentRow, previousRow, headers)
      const rowId = currentRow.id // Use the current row's ID
      
      console.log("🔍 DEBUG: Comparing position", i, "rowId:", rowId, "changes:", changedFields.length)
      
      if (changedFields.length > 0) {
        diffs.set(rowId, {
          rowIndex: i,
          changeType: 'modified',
          currentData: currentRow,
          previousData: previousRow,
          changedFields
        })
        stats.modified++
        console.log("🔍 DEBUG: Modified row at position", i, "rowId:", rowId, "fields:", changedFields)
      } else {
        diffs.set(rowId, {
          rowIndex: i,
          changeType: 'unchanged',
          currentData: currentRow,
          previousData: previousRow
        })
        stats.unchanged++
      }
    } else if (currentRow && !previousRow) {
      // New row added at the end
      const rowId = currentRow.id
      diffs.set(rowId, {
        rowIndex: i,
        changeType: 'added',
        currentData: currentRow
      })
      stats.added++
      console.log("🔍 DEBUG: Added row at position", i, "rowId:", rowId)
    } else if (!currentRow && previousRow) {
      // Row was removed from the end
      const rowId = `removed-${previousRow.id}`
      diffs.set(rowId, {
        rowIndex: -1, // Removed rows don't have a current index
        changeType: 'removed',
        previousData: previousRow
      })
      stats.removed++
      console.log("🔍 DEBUG: Removed row from position", i, "originalId:", previousRow.id)
    }
  }
  
  // Additional check: handle inserted rows in the middle by comparing with content-based matching
  // This handles cases where rows are inserted or moved around
  if (currentRows.length > previousRows.length) {
    console.log("🔍 DEBUG: Rows were likely inserted, checking for content-based matches")
    
    // Create content map of previous rows for fallback matching
    const previousContentMap = new Map<string, Record<string, string>>()
    previousRows.forEach(row => {
      const contentKey = createRowKey(row, headers)
      previousContentMap.set(contentKey, row)
    })
    
    // Check current rows that weren't handled by position-based matching
    currentRows.forEach((currentRow, index) => {
      const rowId = currentRow.id
      const contentKey = createRowKey(currentRow, headers)
      
      // If this row wasn't already processed and matches content from previous CSV
      if (!diffs.has(rowId) && previousContentMap.has(contentKey)) {
        // This is likely a moved/reordered row, treat as unchanged unless fields differ
        const previousRow = previousContentMap.get(contentKey)!
        const changedFields = compareRows(currentRow, previousRow, headers)
        
        if (changedFields.length > 0) {
          diffs.set(rowId, {
            rowIndex: index,
            changeType: 'modified',
            currentData: currentRow,
            previousData: previousRow,
            changedFields
          })
          stats.modified++
          console.log("🔍 DEBUG: Content-matched modified row", rowId, "fields:", changedFields)
        } else {
          diffs.set(rowId, {
            rowIndex: index,
            changeType: 'unchanged',
            currentData: currentRow,
            previousData: previousRow
          })
          stats.unchanged++
          console.log("🔍 DEBUG: Content-matched unchanged row", rowId)
        }
      }
    })
  }
  
  console.log("🔍 DEBUG calculateCsvDiff complete:")
  console.log("🔍 Final diff map keys:", Array.from(diffs.keys()))
  console.log("🔍 Row ID to change type mapping:", Array.from(diffs.entries()).map(([id, diff]) => `${id}: ${diff.changeType}`))
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