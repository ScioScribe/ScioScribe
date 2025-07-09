/**
 * Experiment Store - Zustand
 * 
 * This store manages all experiment-related state and actions,
 * providing a centralized state management solution for the application.
 */

// @ts-ignore - Zustand will be available after npm install
import { create } from 'zustand'
import type { Experiment } from '@/api/database'
import { 
  getExperiments, 
  createExperiment as createExperimentAPI, 
  updateExperimentPlan, 
  updateExperimentHtml, 
  updateExperimentTitle as updateExperimentTitleAPI 
} from '@/api/database'
import { IRIS_CSV_DATA, IRIS_EXPERIMENT_PLAN } from '@/data/placeholder'

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
  refreshVisualization: () => void
  
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
  
  createFirstExperiment: async () => {
    try {
      const newExperiment = await createExperimentAPI({
        title: "Untitled Experiment",
        experimental_plan: IRIS_EXPERIMENT_PLAN,
        csv_data: IRIS_CSV_DATA,
        visualization_html: ""
      })
      
      // Reload experiments and select the new one
      await get().loadExperiments()
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
  
  refreshVisualization: () => {
    set({ visualizationHtml: "" })
  },
  
  resetState: () => {
    set(initialState)
  },
})) 