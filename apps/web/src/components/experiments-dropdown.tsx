"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { ChevronDown, Plus, FlaskRoundIcon as Flask, AlertCircle, Loader2, Trash } from "lucide-react"
import { createExperiment, type Experiment } from "@/api/database"
import { IRIS_EXPERIMENT_PLAN, IRIS_CSV_DATA } from "@/data/placeholder"
import { useToast } from "@/hooks/use-toast"

interface ExperimentsDropdownProps {
  experiments: Experiment[]
  selectedExperiment: Experiment | null
  onExperimentSelect?: (experiment: Experiment) => void
  onExperimentCreated?: () => void
  onExperimentDelete?: (experimentId: string) => Promise<void>
}

export function ExperimentsDropdown({ experiments, selectedExperiment, onExperimentSelect, onExperimentCreated, onExperimentDelete }: ExperimentsDropdownProps) {
  const [displayTitle, setDisplayTitle] = useState<string>("New Experiment")
  const [error, setError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())
  const { toast } = useToast()

  // Update display title when selected experiment changes
  useEffect(() => {
    if (selectedExperiment) {
      setDisplayTitle(getExperimentTitle(selectedExperiment))
    } else {
      setDisplayTitle("New Experiment")
    }
  }, [selectedExperiment])

  const getExperimentTitle = (experiment: Experiment): string => {
    // Use the title field if available
    if (experiment.title && experiment.title.trim()) {
      return experiment.title
    }
    
    // Try to extract title from plan as fallback
    if (experiment.experimental_plan) {
      const firstLine = experiment.experimental_plan.split('\n')[0]
      if (firstLine.startsWith('#')) {
        return firstLine.replace(/^#+\s*/, '').trim()
      }
    }
    
    return "Untitled Experiment"
  }

  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return "Unknown date"
    }
  }

  const handleExperimentSelect = (experiment: Experiment) => {
    onExperimentSelect?.(experiment)
    console.log("Loading experiment:", getExperimentTitle(experiment), experiment)
  }

  const handleCreateExperiment = async () => {
    setIsCreating(true)
    setError(null)
    
    try {
      const newExperiment = await createExperiment({
        title: "Untitled Experiment",
        experimental_plan: IRIS_EXPERIMENT_PLAN,
        csv_data: IRIS_CSV_DATA,
        visualization_html: ""
      })
      
      // Notify parent to refresh experiments list
      onExperimentCreated?.()
      
      // Select the new experiment
      onExperimentSelect?.(newExperiment)
      
      console.log("Created new experiment:", getExperimentTitle(newExperiment))
    } catch (err) {
      console.error("Failed to create experiment:", err)
      setError(err instanceof Error ? err.message : "Failed to create experiment")
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteExperiment = async (experimentId: string) => {
    if (!onExperimentDelete) return
    
    setDeletingIds(prev => new Set(prev).add(experimentId))
    
    try {
      await onExperimentDelete(experimentId)
      toast({
        title: "Experiment deleted",
        description: "The experiment has been permanently removed.",
      })
    } catch (err) {
      console.error("Failed to delete experiment:", err)
      toast({
        variant: "destructive",
        title: "Failed to delete experiment",
        description: err instanceof Error ? err.message : "An unexpected error occurred",
      })
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(experimentId)
        return newSet
      })
    }
  }

  const buttonContent = error ? (
    <>
      <AlertCircle className="h-4 w-4 mr-2 text-red-500" />
      Error
    </>
  ) : (
    <>
      <Flask className="h-4 w-4 mr-2" />
      {displayTitle}
      <ChevronDown className="h-3 w-3 ml-2" />
    </>
  )

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="h-8 px-3 text-sm dark:text-gray-300 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          }}
        >
          {buttonContent}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-64 dark:bg-gray-800 dark:border-gray-700"
        style={{
          fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
        }}
      >
        {error && (
          <>
            <DropdownMenuItem
              className="text-sm text-red-500 dark:text-red-400 cursor-default"
              onClick={(e) => e.preventDefault()}
            >
              <AlertCircle className="h-4 w-4 mr-2" />
              {error}
            </DropdownMenuItem>
            <DropdownMenuSeparator className="dark:bg-gray-700" />
          </>
        )}
        
        {experiments.length === 0 && !error ? (
          <DropdownMenuItem
            className="text-sm dark:text-gray-400 cursor-default"
            onClick={(e) => e.preventDefault()}
          >
            No experiments yet
          </DropdownMenuItem>
        ) : (
          experiments.map((experiment) => (
            <DropdownMenuItem
              key={experiment.id}
              className="text-sm dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:bg-gray-700 cursor-pointer group p-0"
              onClick={(e) => {
                // Prevent dropdown from closing when clicking on experiment row
                e.preventDefault()
                handleExperimentSelect(experiment)
              }}
            >
              <div className="flex items-center justify-between w-full p-2">
                <div className="flex flex-col flex-1 min-w-0">
                  <span className="font-medium truncate">
                    {getExperimentTitle(experiment)}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatDate(experiment.created_at)}
                  </span>
                </div>
                <div className="flex items-center ml-2">
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-100 dark:hover:bg-red-900/20"
                        disabled={deletingIds.has(experiment.id)}
                        onClick={(e) => {
                          e.stopPropagation()
                        }}
                      >
                        {deletingIds.has(experiment.id) ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Trash className="h-3 w-3 text-red-500" />
                        )}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete Experiment</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to delete "{getExperimentTitle(experiment)}"? This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => handleDeleteExperiment(experiment.id)}
                          className="bg-red-600 hover:bg-red-700"
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            </DropdownMenuItem>
          ))
        )}
        
        {experiments.length > 0 && <DropdownMenuSeparator className="dark:bg-gray-700" />}
        
        <DropdownMenuItem
          onClick={handleCreateExperiment}
          disabled={isCreating}
          className="text-sm dark:text-gray-300 dark:hover:bg-gray-700 dark:focus:bg-gray-700 cursor-pointer disabled:opacity-50"
        >
          {isCreating ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Plus className="h-4 w-4 mr-2" />
          )}
          Create Experiment
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
} 