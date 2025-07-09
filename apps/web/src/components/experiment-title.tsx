"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Input } from "@/components/ui/input"

interface ExperimentTitleProps {
  initialTitle?: string
  onTitleChange?: (title: string) => void
}

export function ExperimentTitle({ initialTitle = "Untitled Experiment", onTitleChange }: ExperimentTitleProps) {
  const [title, setTitle] = useState(initialTitle)
  const [isEditing, setIsEditing] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Update title when initialTitle changes
  useEffect(() => {
    setTitle(initialTitle)
  }, [initialTitle])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const handleTitleClick = () => {
    setIsEditing(true)
  }

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTitle(e.target.value)
  }

  const handleTitleSubmit = () => {
    setIsEditing(false)
    if (onTitleChange) {
      onTitleChange(title)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleTitleSubmit()
    } else if (e.key === "Escape") {
      setTitle(initialTitle)
      setIsEditing(false)
    }
  }

  const handleBlur = () => {
    handleTitleSubmit()
  }

  if (isEditing) {
    return (
      <Input
        ref={inputRef}
        value={title}
        onChange={handleTitleChange}
        onKeyDown={handleKeyPress}
        onBlur={handleBlur}
        className="text-center bg-transparent border-0 focus-visible:ring-0 focus-visible:outline-none text-lg font-medium dark:text-white px-2 py-1 max-w-md"
        style={{
          fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
        }}
      />
    )
  }

  return (
    <h2
      onClick={handleTitleClick}
      className="text-lg font-medium text-gray-900 dark:text-white cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
      style={{
        fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
      }}
    >
      {title}
    </h2>
  )
} 