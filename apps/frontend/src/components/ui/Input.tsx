'use client'
import { forwardRef, useState, type InputHTMLAttributes } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string
  error?: string
  lightMode?: boolean
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, lightMode = false, type, className, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false)
    const isPassword = type === 'password'
    const inputType = isPassword ? (showPassword ? 'text' : 'password') : type

    return (
      <div className="w-full">
        {label && (
          <label className={lightMode ? 'form-label-light' : 'form-label'}>
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            type={inputType}
            className={cn(
              lightMode ? 'input-ivory' : 'input-field',
              isPassword && 'pr-12',
              'focus-ring',
              className,
            )}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2 transition-colors focus-ring rounded-md p-0.5',
                lightMode
                  ? 'text-slate-400 hover:text-slate-600'
                  : 'text-slate-400 hover:text-slate-200',
              )}
              tabIndex={-1}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          )}
        </div>
        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: 'auto', marginTop: 6 }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              className="flex items-center gap-1 text-red-400 text-xs overflow-hidden"
            >
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              {error}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    )
  },
)

Input.displayName = 'Input'
export { Input }
export type { InputProps }
