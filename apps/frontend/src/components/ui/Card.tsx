'use client'
import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { hoverLift, tapScale } from '@/lib/motion'

interface CardProps {
  variant?: 'glass' | 'gradient-border' | 'flat'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  className?: string
  children: ReactNode
  hoverable?: boolean
  onClick?: () => void
}

const paddingClasses = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

function Card({ variant = 'glass', padding = 'md', className, children, hoverable = false, onClick }: CardProps) {
  if (variant === 'gradient-border') {
    return (
      <div className="gradient-border-card">
        <motion.div
          className={cn('inner', paddingClasses[padding], className)}
          whileHover={hoverable ? hoverLift : undefined}
          whileTap={onClick ? tapScale : undefined}
          onClick={onClick}
          role={onClick ? 'button' : undefined}
          tabIndex={onClick ? 0 : undefined}
        >
          {children}
        </motion.div>
      </div>
    )
  }

  return (
    <motion.div
      className={cn(
        variant === 'glass' ? 'glass-card' : 'bg-surface-700/40 rounded-2xl',
        paddingClasses[padding],
        onClick && 'cursor-pointer',
        className,
      )}
      whileHover={hoverable ? hoverLift : undefined}
      whileTap={onClick ? tapScale : undefined}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </motion.div>
  )
}

export { Card }
export type { CardProps }
