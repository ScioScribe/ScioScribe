/**
 * Experiment Store - Zustand
 * 
 * This store manages all experiment-related state and actions,
 * providing a centralized state management solution for the application.
 */

import { create } from 'zustand'
import type { Experiment } from '@/api/database'
import { 
  getExperiments, 
  createExperiment as createExperimentAPI, 
  updateExperimentPlan, 
  updateExperimentHtml, 
  updateExperimentTitle as updateExperimentTitleAPI,
  updateExperimentCsv as updateExperimentCsvAPI,
  deleteExperiment as deleteExperimentAPI,
  getExperimentDiff,
  acceptRejectCsvChanges
} from '@/api/database'
import { extractCsvFromDatacleanResponse, validateCsvData } from '@/utils/dataclean-response'
import { IRIS_CSV_DATA, IRIS_EXPERIMENT_PLAN } from '@/data/placeholder'
import { convertPlanningStateToText } from '@/handlers/planning-state-handler'

// Type definitions for planning state
interface PlanningVariables {
  independent?: string
  dependent?: string
  controlled?: string
}

interface PlanningMessage {
  sender: string
  content: string
}

interface PlanningApprovals {
  [key: string]: boolean
}

interface PlanningState {
  experiment_id?: string
  current_stage?: string
  objective?: string
  research_query?: string
  methodology?: string
  variables?: PlanningVariables
  design?: string
  data_requirements?: string
  analysis_plan?: string
  chat_history?: PlanningMessage[]
  is_complete?: boolean
  approvals?: PlanningApprovals
}

// Type definitions for dataclean response
interface DatacleanData {
  [key: string]: unknown
}

interface DatacleanResponse {
  data?: DatacleanData[] | string | DatacleanData
}

// Planning state conversion utility (now using the structured handler)
const convertPlanningStateToString = (planningState: PlanningState): string => {
  try {
    if (!planningState) return "";

    // Use the new structured text formatter instead of raw JSON
    // Convert PlanningState to Record<string, unknown> for compatibility
    return convertPlanningStateToText(planningState as Record<string, unknown>);
  } catch (error) {
    console.error("❌ Error converting planning state to string:", error);
    return `# Experiment Plan\n\n*Error formatting planning data: ${error instanceof Error ? error.message : 'Unknown error'}*`;
  }
}


interface ExperimentState {
  // Core state
  currentExperiment: Experiment | null
  experiments: Experiment[]
  isLoading: boolean
  isCreatingExperiment: boolean
  
  // Content state
  experimentTitle: string
  editorText: string
  csvData: string
  visualizationHtml: string
  // Highlight support
  highlightRows: Set<string>
  
  // CSV versioning state
  previousCsv: string | null
  csvVersion: number
  hasDiff: boolean
}

interface ExperimentActions {
  // Core actions
  setLoading: (isLoading: boolean) => void
  setExperiments: (experiments: Experiment[]) => void
  setCurrentExperiment: (experiment: Experiment | null) => void
  
  // Content actions
  setExperimentTitle: (title: string) => void
  setEditorText: (text: string) => void
  setCsvData: (csv: string) => void
  setVisualizationHtml: (html: string) => void
  
  // Complex actions with side effects
  loadExperiments: () => Promise<void>
  createFirstExperiment: () => Promise<void>
  createExperiment: () => Promise<Experiment>
  selectExperiment: (experiment: Experiment) => void
  updateEditorTextWithSave: (text: string) => Promise<void>
  updateVisualizationHtmlWithSave: (html: string) => Promise<void>
  updateExperimentTitleWithSave: (title: string) => Promise<void>
  updateExperimentCsvWithSave: (csv: string) => Promise<void>
  refreshVisualization: () => void
  
  // Experiment management
  removeExperiment: (experimentId: string) => Promise<void>
  
  // Planning integration functions
  updatePlanFromPlanningState: (planningState: PlanningState) => Promise<void>
  updatePlanFromPlanningMessage: (message: string, stage?: string) => Promise<void>
  
  // Dataclean integration functions
  updateCsvFromDatacleanResponse: (response: DatacleanResponse) => Promise<void>
  updateCsvFromDatacleanData: (csvData: string) => Promise<void>
  clearHighlightRows: () => void
  
  // CSV versioning actions
  loadExperimentDiff: () => Promise<void>
  acceptCsvChanges: () => Promise<void>
  rejectCsvChanges: () => Promise<void>
  
  // Reset actions
  resetState: () => void
}

type ExperimentStore = ExperimentState & ExperimentActions

// Type definitions for Zustand
type SetState = (partial: Partial<ExperimentStore> | ((state: ExperimentStore) => Partial<ExperimentStore>)) => void
type GetState = () => ExperimentStore

const initialState: ExperimentState = {
  currentExperiment: null,
  experiments: [],
  isLoading: true,
  isCreatingExperiment: false,
  experimentTitle: "Untitled Experiment",
  editorText: IRIS_EXPERIMENT_PLAN,
  csvData: IRIS_CSV_DATA,
  visualizationHtml: "",
  highlightRows: new Set(),
  previousCsv: null,
  csvVersion: 0,
  hasDiff: false,
}

export const useExperimentStore = create<ExperimentStore>((set: SetState, get: GetState) => ({
  ...initialState,
  
  // Basic setters
  setLoading: (isLoading: boolean) => 
    set({ isLoading }),
  
  setExperiments: (experiments: Experiment[]) => 
    set({ experiments }),
  
  setCurrentExperiment: (currentExperiment: Experiment | null) => 
    set({ currentExperiment }),
  
  setExperimentTitle: (experimentTitle: string) => 
    set({ experimentTitle }),
  
  setEditorText: (editorText: string) => 
    set({ editorText }),
  
  setCsvData: (csvData: string) => 
    set({ csvData }),
  
  setVisualizationHtml: (visualizationHtml: string) => 
    set({ visualizationHtml }),

  // Utility to clear row highlights
  clearHighlightRows: () => set({ highlightRows: new Set() }),
  
  // Complex actions with side effects
  loadExperiments: async () => {
    set({ isLoading: true })
    try {
      const data = await getExperiments()
      set({ experiments: data })
      
      // If experiments exist, load the first one
      if (data.length > 0) {
        get().selectExperiment(data[0])
      }
    } catch (error) {
      console.error("Failed to load experiments:", error)
    } finally {
      set({ isLoading: false })
    }
  },
  
  // Planning integration functions
  updatePlanFromPlanningState: async (planningState: PlanningState) => {
    try {
      console.log("🎯 Updating plan from planning state:", planningState)
      
      // Convert planning state to formatted string
      const formattedPlan = convertPlanningStateToString(planningState)
      
      // Update the editor text (this will also save to database)
      await get().updateEditorTextWithSave(formattedPlan)
      
      console.log("✅ Plan updated from planning state")
    } catch (error) {
      console.error("❌ Failed to update plan from planning state:", error)
    }
  },
  
  updatePlanFromPlanningMessage: async (message: string, stage?: string) => {
    try {
      console.log("📝 Updating plan from planning message:", message)
      
      const currentPlan = get().editorText
      const timestamp = new Date().toISOString()
      
      // Append planning message to current plan
      const updatedPlan = `${currentPlan}\n\n## Planning Session Update - ${timestamp}\n\n${stage ? `**Stage:** ${stage}\n\n` : ""}${message}\n\n---\n`
      
      // Update the editor text (this will also save to database)
      await get().updateEditorTextWithSave(updatedPlan)
      
      console.log("✅ Plan updated from planning message")
    } catch (error) {
      console.error("❌ Failed to update plan from planning message:", error)
    }
  },
   
   // Dataclean integration functions
   updateCsvFromDatacleanResponse: async (response: DatacleanResponse) => {
     try {
       console.log("🧹 Updating CSV from dataclean response:", response)
       
       // Extract CSV data using standardized utility
       const csvData = extractCsvFromDatacleanResponse(response, 'dataclean-response')
       
       if (csvData) {
         // Validate CSV data before processing
         const validation = validateCsvData(csvData)
         if (!validation.isValid) {
           console.error("❌ Invalid CSV data:", validation.error)
           throw new Error(`Invalid CSV data: ${validation.error}`)
         }
         
         console.log("📊 CSV validation passed:", {
           rowCount: validation.rowCount,
           columnCount: validation.columnCount
         })
         
         // Use the agent update function to properly handle versioning
         await get().updateCsvFromDatacleanData(csvData)
       } else {
         console.warn("⚠️ No CSV data found in dataclean response")
       }
       
       console.log("✅ CSV updated from dataclean response")
     } catch (error) {
       console.error("❌ Failed to update CSV from dataclean response:", error)
       throw error
     }
   },
   
   updateCsvFromDatacleanData: async (csvData: string) => {
     try {
       console.log("📊 Updating CSV from dataclean data (agent update)")
       
       // Mark this as an agent update by calling the API directly
       const { currentExperiment, experiments, csvVersion } = get()
       if (currentExperiment) {
         const updatedExperiment = await updateExperimentCsvAPI(
           currentExperiment.id, 
           csvData,
           { 
             isAgentUpdate: true,
             expectedVersion: csvVersion
           }
         )
         
         // Update state with new experiment data
         set({ 
           currentExperiment: updatedExperiment,
           csvData: updatedExperiment.csv_data || csvData,
           previousCsv: updatedExperiment.previous_csv || null,
           csvVersion: updatedExperiment.csv_version,
           hasDiff: !!updatedExperiment.previous_csv
         })
         
         // Update the experiments array
         const updatedExperiments = experiments.map((exp: Experiment) => 
           exp.id === currentExperiment.id ? updatedExperiment : exp
         )
         set({ experiments: updatedExperiments })
       }
       
       console.log("✅ CSV updated from dataclean data")
     } catch (error) {
       console.error("❌ Failed to update CSV from dataclean data:", error)
     }
   },

   createFirstExperiment: async () => {
     const state = get()
     
     // Debouncing: Check if we're already creating an experiment
     if (state.isCreatingExperiment) {
       console.log("⏳ Experiment creation already in progress, skipping duplicate call")
       return
     }
     
     // Set flag to prevent duplicate calls
     set({ isCreatingExperiment: true })
     
     try {
       const newExperiment = await createExperimentAPI({
         title: "Untitled Experiment",
         experimental_plan: IRIS_EXPERIMENT_PLAN,
         csv_data: IRIS_CSV_DATA,
         visualization_html: ""
       })
       
       // Add the new experiment to the experiments array instead of reloading all
       const { experiments } = get()
       const updatedExperiments = [newExperiment, ...experiments]
       set({ experiments: updatedExperiments })
       
       // Select the new experiment
       get().selectExperiment(newExperiment)
     } catch (error) {
       console.error("Failed to create experiment:", error)
     } finally {
       // Clear the flag after operation completes
       set({ isCreatingExperiment: false })
     }
   },

   createExperiment: async () => {
     const state = get()
     
     // Debouncing: Check if we're already creating an experiment
     if (state.isCreatingExperiment) {
       console.log("⏳ Experiment creation already in progress, skipping duplicate call")
       throw new Error("Experiment creation already in progress")
     }
     
     // Set flag to prevent duplicate calls
     set({ isCreatingExperiment: true })
     
     try {
       const newExperiment = await createExperimentAPI({
         title: "Untitled Experiment",
         experimental_plan: IRIS_EXPERIMENT_PLAN,
         csv_data: IRIS_CSV_DATA,
         visualization_html: ""
       })
       
       // Add the new experiment to the experiments array instead of reloading all
       const { experiments } = get()
       const updatedExperiments = [newExperiment, ...experiments]
       set({ experiments: updatedExperiments })
       
       return newExperiment
     } catch (error) {
       console.error("Failed to create experiment:", error)
       throw error
     } finally {
       // Clear the flag after operation completes
       set({ isCreatingExperiment: false })
     }
   },
  
  selectExperiment: (experiment: Experiment) => {
    console.log("Selected experiment:", experiment)
    
    set({
      currentExperiment: experiment,
      experimentTitle: experiment.title || "Untitled Experiment",
      editorText: experiment.experimental_plan || IRIS_EXPERIMENT_PLAN,
      csvData: experiment.csv_data || IRIS_CSV_DATA,
      visualizationHtml: experiment.visualization_html || "",
      previousCsv: experiment.previous_csv || null,
      csvVersion: experiment.csv_version || 0,
      hasDiff: !!experiment.previous_csv,
    })
  },
  
  updateEditorTextWithSave: async (text: string) => {
    set({ editorText: text })
    
    // Auto-save to database if experiment is selected
    const { currentExperiment } = get()
    if (currentExperiment) {
      try {
        await updateExperimentPlan(currentExperiment.id, text)
        console.log("Plan updated in database")
      } catch (error) {
        console.error("Failed to update plan:", error)
      }
    }
  },
  
  updateVisualizationHtmlWithSave: async (html: string) => {
    set({ visualizationHtml: html })
    
    // Auto-save to database if experiment is selected
    const { currentExperiment } = get()
    if (currentExperiment) {
      try {
        await updateExperimentHtml(currentExperiment.id, html)
        console.log("Visualization updated in database")
      } catch (error) {
        console.error("Failed to update visualization:", error)
      }
    }
  },
  
  updateExperimentTitleWithSave: async (title: string) => {
    set({ experimentTitle: title })
    
    // Auto-save to database if experiment is selected
    const { currentExperiment, experiments } = get()
    if (currentExperiment) {
      try {
        const updatedExperiment = await updateExperimentTitleAPI(currentExperiment.id, title)
        
        // Update the current experiment with the new title
        set({ currentExperiment: updatedExperiment })
        
        // Update the experiments array to reflect the new title
        const updatedExperiments = experiments.map((exp: Experiment) => 
          exp.id === currentExperiment.id 
            ? { ...exp, title: title, updated_at: updatedExperiment.updated_at }
            : exp
        )
        set({ experiments: updatedExperiments })
        
        console.log("Title updated in database")
      } catch (error) {
        console.error("Failed to update title:", error)
      }
    }
  },
  
  updateExperimentCsvWithSave: async (csv: string) => {
    const { csvData: prevCsvData, highlightRows } = get()

    // Compute added rows (simple diff by line value after header)
    try {
      const prevLines = prevCsvData ? prevCsvData.trim().split('\n').slice(1) : []
      const newLines = csv.trim().split('\n').slice(1)
      const prevSet = new Set(prevLines)
      const addedLines: string[] = []
      newLines.forEach(line => { if (!prevSet.has(line)) addedLines.push(line) })

      // Determine ids of added rows using their position (index+1) in new CSV
      const addedRowIds = new Set<string>()
      if (addedLines.length) {
        const headerPlusLines = csv.trim().split('\n')
        headerPlusLines.slice(1).forEach((line, idx) => {
          if (addedLines.includes(line)) {
            addedRowIds.add((idx + 1).toString())
          }
        })
      }

      // Merge with existing highlightRows
      const merged = new Set([...highlightRows, ...addedRowIds])
      set({ highlightRows: merged, csvData: csv })
      // Auto-clear highlight after 8s
      if (addedRowIds.size) {
        setTimeout(() => {
          const current = get().highlightRows
          addedRowIds.forEach(id => current.delete(id))
          set({ highlightRows: new Set(current) })
        }, 8000)
      }
    } catch (e) {
      console.warn('Highlight diff error', e)
      set({ csvData: csv })
    }
    
    // Auto-save to database if experiment is selected
    const { currentExperiment, experiments } = get()
    if (currentExperiment) {
      try {
        const updatedExperiment = await updateExperimentCsvAPI(currentExperiment.id, csv)
        
        // Update the current experiment with the new CSV data
        set({ currentExperiment: updatedExperiment })
        
        // Update the experiments array to reflect the new CSV
        const updatedExperiments = experiments.map((exp: Experiment) => 
          exp.id === currentExperiment.id 
            ? { ...exp, csv_data: csv, updated_at: updatedExperiment.updated_at }
            : exp
        )
        set({ experiments: updatedExperiments })
        
        console.log("CSV updated in database")
      } catch (error) {
        console.error("Failed to update CSV:", error)
        throw error
      }
    }
  },
  
  refreshVisualization: () => {
    set({ visualizationHtml: "" })
  },
  
  removeExperiment: async (experimentId: string) => {
    try {
      // Delete from database
      await deleteExperimentAPI(experimentId)
      
      // Remove from local state
      const { experiments, currentExperiment } = get()
      const updatedExperiments = experiments.filter(exp => exp.id !== experimentId)
      set({ experiments: updatedExperiments })
      
      // Handle current experiment switching if deleted experiment was active
      if (currentExperiment?.id === experimentId) {
        if (updatedExperiments.length > 0) {
          // Select the first experiment (most recently created)
          get().selectExperiment(updatedExperiments[0])
        } else {
          // No experiments left, clear current experiment
          set({ 
            currentExperiment: null,
            experimentTitle: "New Experiment",
            editorText: IRIS_EXPERIMENT_PLAN,
            csvData: IRIS_CSV_DATA,
            visualizationHtml: "",
          })
        }
      }
      
      console.log("✅ Experiment removed successfully")
    } catch (error) {
      console.error("❌ Failed to remove experiment:", error)
      throw error
    }
  },
  
  // CSV versioning actions
  loadExperimentDiff: async () => {
    try {
      const { currentExperiment } = get()
      if (!currentExperiment) return
      
      const diff = await getExperimentDiff(currentExperiment.id)
      
      if (diff.has_diff) {
        set({
          previousCsv: diff.previous_csv || null,
          csvVersion: diff.csv_version || 0,
          hasDiff: true
        })
      }
    } catch (error) {
      console.error("Failed to load experiment diff:", error)
    }
  },
  
  acceptCsvChanges: async () => {
    try {
      const { currentExperiment, experiments } = get()
      if (!currentExperiment) return
      
      const updatedExperiment = await acceptRejectCsvChanges(currentExperiment.id, 'accept')
      
      // Update state
      set({
        currentExperiment: updatedExperiment,
        previousCsv: null,
        hasDiff: false,
        csvVersion: updatedExperiment.csv_version
      })
      
      // Update experiments list
      const updatedExperiments = experiments.map((exp: Experiment) => 
        exp.id === currentExperiment.id ? updatedExperiment : exp
      )
      set({ experiments: updatedExperiments })
      
      console.log("✅ CSV changes accepted")
    } catch (error) {
      console.error("Failed to accept CSV changes:", error)
      throw error
    }
  },
  
  rejectCsvChanges: async () => {
    try {
      const { currentExperiment, experiments } = get()
      if (!currentExperiment) return
      
      const updatedExperiment = await acceptRejectCsvChanges(currentExperiment.id, 'reject')
      
      // Update state with reverted CSV
      set({
        currentExperiment: updatedExperiment,
        csvData: updatedExperiment.csv_data || "",
        previousCsv: null,
        hasDiff: false,
        csvVersion: updatedExperiment.csv_version
      })
      
      // Update experiments list
      const updatedExperiments = experiments.map((exp: Experiment) => 
        exp.id === currentExperiment.id ? updatedExperiment : exp
      )
      set({ experiments: updatedExperiments })
      
      console.log("✅ CSV changes rejected")
    } catch (error) {
      console.error("Failed to reject CSV changes:", error)
      throw error
    }
  },
  
  resetState: () => {
    set(initialState)
  },
})) 