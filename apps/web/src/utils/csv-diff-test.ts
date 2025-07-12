/**
 * CSV Diff Test Utility
 * 
 * Simple test functions to validate CSV diff calculation behavior
 */

import { calculateCsvDiff } from './csv-diff'

/**
 * Test basic position-based diff calculation
 */
export function testPositionBasedDiff() {
  console.log("🧪 Testing position-based CSV diff calculation...")
  
  const previousCsv = `name,age,city
John,25,NYC
Jane,30,LA
Bob,35,SF`

  const currentCsv = `name,age,city
John,26,NYC
Jane,30,LA
Bob,35,SF
Alice,28,Chicago`

  const result = calculateCsvDiff(currentCsv, previousCsv)
  
  console.log("🧪 Test Results:")
  console.log("  - Diff map keys:", Array.from(result.diffs.keys()))
  console.log("  - Stats:", result.stats)
  console.log("  - Row 1 should be modified (John's age changed):", result.diffs.get('1')?.changeType)
  console.log("  - Row 4 should be added (Alice):", result.diffs.get('4')?.changeType)
  
  // Verify expectations
  const row1Diff = result.diffs.get('1')
  const row4Diff = result.diffs.get('4')
  
  const success = (
    row1Diff?.changeType === 'modified' &&
    row1Diff?.changedFields?.includes('age') &&
    row4Diff?.changeType === 'added'
  )
  
  console.log("🧪 Test", success ? "✅ PASSED" : "❌ FAILED")
  return success
}

/**
 * Test row ID consistency with parseCSVData
 */
export function testRowIdConsistency() {
  console.log("🧪 Testing row ID consistency...")
  
  const { parseCSVData } = require('../data/placeholder')
  
  const csvData = `name,age,city
John,25,NYC
Jane,30,LA`

  const parsedRows = parseCSVData(csvData)
  const result = calculateCsvDiff(csvData, csvData) // Same data = all unchanged
  
  console.log("🧪 Parsed row IDs:", parsedRows.map(r => r.id))
  console.log("🧪 Diff map keys:", Array.from(result.diffs.keys()))
  
  // All parsed row IDs should exist in diff map
  const allIdsPresent = parsedRows.every(row => result.diffs.has(row.id))
  const allUnchanged = Array.from(result.diffs.values()).every(diff => diff.changeType === 'unchanged')
  
  console.log("🧪 All row IDs present in diff:", allIdsPresent)
  console.log("🧪 All rows marked unchanged:", allUnchanged)
  
  const success = allIdsPresent && allUnchanged
  console.log("🧪 Test", success ? "✅ PASSED" : "❌ FAILED")
  return success
}

/**
 * Run all tests
 */
export function runAllTests() {
  console.log("🧪 Starting CSV Diff Tests...")
  
  const test1 = testPositionBasedDiff()
  const test2 = testRowIdConsistency()
  
  const allPassed = test1 && test2
  console.log("🧪 All tests", allPassed ? "✅ PASSED" : "❌ FAILED")
  
  return allPassed
}