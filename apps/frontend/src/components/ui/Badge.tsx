'use client'
import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type BadgeVariant = 'blue' | 'green' | 'yellow' | 'red' | 'gray' | 'teal'

interface BadgeProps {
  variant?: BadgeVariant
  children: ReactNode
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  blue:   'badge-blue',
  green:  'badge-green',
  yellow: 'badge-yellow',
  red:    'badge-red',
  gray:   'badge-gray',
  teal:   'badge bg-primary-500/20 text-primary-300 border border-primary-500/30',
}

function Badge({ variant = 'gray', children, className }: BadgeProps) {
  return (
    <span className={cn(variantClasses[variant], className)}>
      {children}
    </span>
  )
}

export { Badge }
export type { BadgeProps, BadgeVariant }
