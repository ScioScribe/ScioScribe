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
  deleteExperiment as deleteExperimentAPI 
} from '@/api/database'
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
    return convertPlanningStateToText(planningState);
  } catch (error) {
    console.error("❌ Error converting planning state to string:", error);
    return `# Experiment Plan\n\n*Error formatting planning data: ${error instanceof Error ? error.message : 'Unknown error'}*`;
  }
}

// Array to CSV conversion utility
const convertArrayToCsv = (data: DatacleanData[]): string => {
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

interface ExperimentState {
  // Core state
  currentExperiment: Experiment | null
  experiments: Experiment[]
  isLoading: boolean
  
  // Content state
  experimentTitle: string
  editorText: string
  csvData: string
  visualizationHtml: string
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
  experimentTitle: "Untitled Experiment",
  editorText: IRIS_EXPERIMENT_PLAN,
  csvData: IRIS_CSV_DATA,
  visualizationHtml: "",
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
       
       // Extract CSV data from response
       let csvData = ""
       
       if (response.data) {
         if (typeof response.data === "string") {
           csvData = response.data
         } else if (Array.isArray(response.data)) {
           // Convert array of objects to CSV
           csvData = convertArrayToCsv(response.data)
         } else {
           console.warn("⚠️ Unexpected data format in dataclean response")
           csvData = JSON.stringify(response.data, null, 2)
         }
       }
       
       if (csvData) {
         await get().updateCsvFromDatacleanData(csvData)
       }
       
       console.log("✅ CSV updated from dataclean response")
     } catch (error) {
       console.error("❌ Failed to update CSV from dataclean response:", error)
     }
   },
   
   updateCsvFromDatacleanData: async (csvData: string) => {
     try {
       console.log("📊 Updating CSV from dataclean data")
       
       // Use the new updateExperimentCsvWithSave action
       await get().updateExperimentCsvWithSave(csvData)
       
       console.log("✅ CSV updated from dataclean data")
     } catch (error) {
       console.error("❌ Failed to update CSV from dataclean data:", error)
     }
   },

   createFirstExperiment: async () => {
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
    set({ csvData: csv })
    
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
  
  resetState: () => {
    set(initialState)
  },
})) 