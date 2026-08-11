'use client'
import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
  variant?: 'rect' | 'circle' | 'text'
  width?: string | number
  height?: string | number
  lines?: number
}

function Skeleton({ className, variant = 'rect', width, height, lines = 1 }: SkeletonProps) {
  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height

  if (variant === 'text' && lines > 1) {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="shimmer h-4 rounded"
            style={{ width: i === lines - 1 ? '60%' : '100%' }}
          />
        ))}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'shimmer',
        variant === 'circle' && 'rounded-full',
        variant === 'text' && 'h-4 rounded',
        variant === 'rect' && 'rounded-xl',
        className,
      )}
      style={style}
    />
  )
}

export { Skeleton }
export type { SkeletonProps }
