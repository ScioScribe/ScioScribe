/**
 * Experiment Store Hooks
 * 
 * This module provides utility hooks for accessing specific parts of the 
 * experiment store with optimized selectors to prevent unnecessary re-renders.
 */

import { useExperimentStore } from '@/stores/experiment-store'

// Type for the store state
type ExperimentStoreState = ReturnType<typeof useExperimentStore.getState>

/**
 * Hook to get current experiment data
 */
export const useCurrentExperiment = () => {
  return useExperimentStore((state: ExperimentStoreState) => ({
    currentExperiment: state.currentExperiment,
    experimentTitle: state.experimentTitle,
    selectExperiment: state.selectExperiment,
  }))
}

/**
 * Hook to get experiment list data
 */
export const useExperimentsList = () => {
  return useExperimentStore((state: ExperimentStoreState) => ({
    experiments: state.experiments,
    isLoading: state.isLoading,
    loadExperiments: state.loadExperiments,
    createFirstExperiment: state.createFirstExperiment,
  }))
}

/**
 * Hook to get editor content data
 */
export const useEditorContent = () => {
  return useExperimentStore((state: ExperimentStoreState) => ({
    editorText: state.editorText,
    updateEditorText: state.updateEditorTextWithSave,
    setEditorText: state.setEditorText,
  }))
}

/**
 * Hook to get visualization data
 */
export const useVisualization = () => {
  return useExperimentStore((state: ExperimentStoreState) => ({
    visualizationHtml: state.visualizationHtml,
    updateVisualizationHtml: state.updateVisualizationHtmlWithSave,
    refreshVisualization: state.refreshVisualization,
  }))
}

/**
 * Hook to get CSV data
 */
export const useCsvData = () => {
  return useExperimentStore((state: ExperimentStoreState) => ({
    csvData: state.csvData,
    setCsvData: state.setCsvData,
  }))
}

/**
 * Hook to get title management
 */
export const useExperimentTitle = () => {
  return useExperimentStore((state: ExperimentStoreState) => ({
    experimentTitle: state.experimentTitle,
    updateTitle: state.updateExperimentTitleWithSave,
  }))
}

/**
 * Hook to get loading state
 */
export const useLoadingState = () => {
  return useExperimentStore((state: ExperimentStoreState) => state.isLoading)
} 