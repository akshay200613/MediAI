'use client'
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { tapScale } from '@/lib/motion'

type ButtonVariant = 'primary' | 'secondary' | 'outlined' | 'outlinedDark' | 'danger' | 'ghost' | 'pill' | 'tealGradient'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
  fullWidth?: boolean
  children: ReactNode
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  outlined: 'btn-outlined',
  outlinedDark: 'btn-outlined-dark',
  danger: 'btn-danger',
  ghost: 'flex items-center justify-center gap-2 bg-transparent hover:bg-white/5 text-slate-400 hover:text-white font-medium rounded-xl transition-all duration-200',
  pill: 'btn-pill',
  tealGradient: 'btn-teal-gradient',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'text-xs px-3 py-1.5',
  md: 'text-sm',
  lg: 'text-base px-8 py-3.5',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, icon, fullWidth = false, children, className, disabled, ...props }, ref) => {
    return (
      <motion.button
        ref={ref}
        whileTap={disabled || loading ? undefined : tapScale}
        className={cn(
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
          'focus-ring',
          className,
        )}
        disabled={disabled || loading}
        {...(props as HTMLMotionProps<'button'>)}
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            {children}
          </>
        ) : (
          <>
            {icon && <span className="flex-shrink-0">{icon}</span>}
            {children}
          </>
        )}
      </motion.button>
    )
  },
)

Button.displayName = 'Button'
export { Button }
export type { ButtonProps, ButtonVariant, ButtonSize }
