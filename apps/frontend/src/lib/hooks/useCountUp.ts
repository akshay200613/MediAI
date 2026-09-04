'use client'
import { useState, useEffect } from 'react'

export function useCountUp(target: number, duration = 800): number {
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (target === 0) {
      setCount(0)
      return
    }

    let startTimestamp: number | null = null
    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp
      const progress = Math.min((timestamp - startTimestamp) / duration, 1)
      // Ease out expo formula
      const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      setCount(Math.floor(easeProgress * target))
      if (progress < 1) {
        requestAnimationFrame(step)
      } else {
        setCount(target)
      }
    }

    requestAnimationFrame(step)
  }, [target, duration])

  return count
}
