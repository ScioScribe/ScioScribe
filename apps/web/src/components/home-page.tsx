"use client"

/**
 * Home Page Component
 * 
 * Landing page with video background, ScioScribe branding, and main call-to-action
 * to create a new experiment. This is the entry point when users first visit the app.
 */

import { Button } from "@/components/ui/button"
import { ExperimentsCarousel } from "@/components/experiments-carousel"
import { useExperimentStore } from "@/stores"
import { FileText, Play } from "lucide-react"
import type { Experiment } from "@/api/database"

interface HomePageProps {
  onNavigateToExperiment?: () => void
  onExperimentSelect?: (experiment: Experiment) => void
}

export function HomePage({ onNavigateToExperiment, onExperimentSelect }: HomePageProps) {
  const { experiments, isLoading, createFirstExperiment, selectExperiment } = useExperimentStore()

  const handleCreateExperiment = async () => {
    try {
      await createFirstExperiment()
      onNavigateToExperiment?.()
    } catch (error) {
      console.error("Failed to create experiment:", error)
    }
  }

  const handleExperimentSelect = (experiment: Experiment) => {
    selectExperiment(experiment)
    onExperimentSelect?.(experiment)
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="relative h-screen w-full overflow-hidden">
        <video
          className="absolute inset-0 w-full h-full object-cover"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/video.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-black/40" />
        <div className="relative z-10 flex items-center justify-center h-full">
          <div className="text-lg text-white">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative h-screen w-full overflow-hidden">
      {/* Video Background */}
      <video
        className="absolute inset-0 w-full h-full object-cover"
        autoPlay
        loop
        muted
        playsInline
      >
        <source src="/video.mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>

      {/* Dark overlay for better text readability */}
      <div className="absolute inset-0 bg-black/40" />

      {/* Content */}
      <div className="relative z-10 flex flex-col h-full text-white">
        {/* Header Section */}
        <div className="flex-shrink-0 flex flex-col items-center justify-center pt-20 pb-12">
          {/* Logo and Title */}
          <div className="flex items-center gap-4 mb-8">
            <FileText className="h-16 w-16 text-blue-400" />
            <h1
              className="text-6xl font-bold tracking-tight"
              style={{
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
              }}
            >
              ScioScribe
            </h1>
          </div>

          {/* Subtitle */}
          <p 
            className="text-xl text-gray-200 mb-8 text-center max-w-2xl"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            }}
          >
            Your AI-powered research companion for experiment design, data analysis, and scientific discovery
          </p>
        </div>

        {/* Experiments Carousel Section */}
        {experiments.length > 0 && (
          <div className="flex-1 flex items-center justify-center py-8">
            <ExperimentsCarousel 
              experiments={experiments} 
              onExperimentSelect={handleExperimentSelect}
            />
          </div>
        )}

        {/* Call to Action Section */}
        <div className="flex-shrink-0 flex flex-col items-center justify-center pb-20">
          <Button
            onClick={handleCreateExperiment}
            size="lg"
            className="px-12 py-6 text-lg font-semibold bg-blue-600 hover:bg-blue-700 text-white border-0 shadow-lg hover:shadow-xl transition-all duration-300 mb-8"
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            }}
          >
            <Play className="h-5 w-5 mr-3" />
            New Experiment
          </Button>

          {/* Additional Info */}
          <div className="text-center">
            <p className="text-sm text-gray-300 mb-2">
              Plan • Execute • Analyze
            </p>
            <p className="text-xs text-gray-400">
              Powered by advanced AI agents for comprehensive research workflows
            </p>
          </div>
        </div>
      </div>
    </div>
  )
} 