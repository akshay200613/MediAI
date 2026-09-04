'use client'
import { useState, useEffect } from 'react'

export function useStreamingText(fullText: string, enabled = true, speedMs = 12): {
  displayedText: string
  isDone: boolean
} {
  const [displayedText, setDisplayedText] = useState('')
  const [isDone, setIsDone] = useState(!enabled)

  useEffect(() => {
    if (!enabled) {
      setDisplayedText(fullText)
      setIsDone(true)
      return
    }

    setDisplayedText('')
    setIsDone(false)
    let index = 0

    const interval = setInterval(() => {
      if (index < fullText.length) {
        setDisplayedText((prev) => prev + fullText.charAt(index))
        index++
      } else {
        setIsDone(true)
        clearInterval(interval)
      }
    }, speedMs)

    return () => clearInterval(interval)
  }, [fullText, enabled, speedMs])

  return { displayedText, isDone }
}
