"use client"

/**
 * Experiments Carousel Component
 * 
 * A beautiful floating cards carousel that displays existing experiments
 * with glassmorphism effects over the video background.
 */

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ChevronLeft, ChevronRight, Calendar, FileText, BarChart3 } from "lucide-react"
import type { Experiment } from "@/api/database"

interface ExperimentsCarouselProps {
  experiments: Experiment[]
  onExperimentSelect: (experiment: Experiment) => void
}

export function ExperimentsCarousel({ experiments, onExperimentSelect }: ExperimentsCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const itemsPerView = 3
  const maxIndex = Math.max(0, experiments.length - itemsPerView)

  const handlePrevious = () => {
    setCurrentIndex(prev => Math.max(0, prev - 1))
  }

  const handleNext = () => {
    setCurrentIndex(prev => Math.min(maxIndex, prev + 1))
  }

  const formatDate = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      })
    } catch {
      return "Unknown date"
    }
  }

  const getExperimentTitle = (experiment: Experiment): string => {
    if (experiment.title && experiment.title.trim()) {
      return experiment.title
    }
    
    if (experiment.experimental_plan) {
      const firstLine = experiment.experimental_plan.split('\n')[0]
      if (firstLine.startsWith('#')) {
        return firstLine.replace(/^#+\s*/, '').trim()
      }
    }
    
    return "Untitled Experiment"
  }

  const getExperimentPreview = (experiment: Experiment): string => {
    if (experiment.experimental_plan) {
      const lines = experiment.experimental_plan.split('\n')
      const contentLines = lines.slice(1).filter(line => line.trim() && !line.startsWith('#'))
      if (contentLines.length > 0) {
        return contentLines[0].trim().substring(0, 100) + "..."
      }
    }
    return "No description available"
  }

  if (experiments.length === 0) {
    return null
  }

  return (
    <div className="w-full max-w-6xl mx-auto px-4">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">
          Continue Your Research
        </h2>
        <p className="text-gray-300">
          Pick up where you left off with your previous experiments
        </p>
      </div>

      {/* Carousel Container */}
      <div className="relative">
        {/* Navigation Buttons */}
        {experiments.length > itemsPerView && (
          <>
            <Button
              variant="ghost"
              size="icon"
              className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-black/20 hover:bg-black/40 text-white border-0 backdrop-blur-sm"
              onClick={handlePrevious}
              disabled={currentIndex === 0}
            >
              <ChevronLeft className="h-6 w-6" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-black/20 hover:bg-black/40 text-white border-0 backdrop-blur-sm"
              onClick={handleNext}
              disabled={currentIndex >= maxIndex}
            >
              <ChevronRight className="h-6 w-6" />
            </Button>
          </>
        )}

        {/* Cards Container */}
        <div className="overflow-hidden mx-12">
          <div 
            className="flex transition-transform duration-300 ease-in-out gap-6"
            style={{ transform: `translateX(-${currentIndex * (100 / itemsPerView)}%)` }}
          >
            {experiments.map((experiment) => (
              <Card
                key={experiment.id}
                className="flex-shrink-0 w-80 bg-white/10 backdrop-blur-md border-white/20 hover:bg-white/20 transition-all duration-300 cursor-pointer group"
                onClick={() => onExperimentSelect(experiment)}
                style={{ minWidth: `${100 / itemsPerView}%` }}
              >
                <div className="p-6">
                  {/* Card Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-400" />
                      <span className="text-xs text-gray-300 font-medium">
                        EXPERIMENT
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Calendar className="h-3 w-3" />
                      {formatDate(experiment.updated_at || experiment.created_at)}
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="text-lg font-semibold text-white mb-3 line-clamp-2 group-hover:text-blue-300 transition-colors">
                    {getExperimentTitle(experiment)}
                  </h3>

                  {/* Preview */}
                  <p className="text-sm text-gray-300 mb-4 line-clamp-3">
                    {getExperimentPreview(experiment)}
                  </p>

                  {/* Stats */}
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <div className="flex items-center gap-1">
                      <BarChart3 className="h-3 w-3" />
                      <span>
                        {experiment.visualization_html ? 'Has Charts' : 'No Charts'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      <span>
                        {experiment.csv_data ? 'Has Data' : 'No Data'}
                      </span>
                    </div>
                  </div>

                  {/* Hover Effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg" />
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Dots Indicator */}
        {experiments.length > itemsPerView && (
          <div className="flex justify-center mt-6 gap-2">
            {Array.from({ length: maxIndex + 1 }).map((_, index) => (
              <button
                key={index}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  index === currentIndex 
                    ? 'bg-white w-6' 
                    : 'bg-white/40 hover:bg-white/60'
                }`}
                onClick={() => setCurrentIndex(index)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
} 