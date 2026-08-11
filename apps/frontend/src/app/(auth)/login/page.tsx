'use client'
import { useState, useMemo, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, ShieldCheck, Sparkles, BrainCircuit, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth/context'
import toast from 'react-hot-toast'
import { springSnappy, easeOutExpo, staggerContainer, fadeSlideUp } from '@/lib/motion'

// Validation schemas
const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

const registerSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
})

type LoginFormData = z.infer<typeof loginSchema>
type RegisterFormData = z.infer<typeof registerSchema>

function AuthForm() {
  const searchParams = useSearchParams()
  const initialMode = searchParams?.get('mode') === 'register' ? 'register' : 'login'
  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { login, register: registerUser } = useAuth()
  const router = useRouter()

  // Form setup for Login
  const {
    register: registerLogin,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  // Form setup for Register
  const {
    register: registerReg,
    handleSubmit: handleRegSubmit,
    watch: watchReg,
    formState: { errors: regErrors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const passwordValue = watchReg('password', '')

  // Password strength (0-4)
  const passwordStrength = useMemo(() => {
    if (!passwordValue) return 0
    let score = 0
    if (passwordValue.length >= 8) score += 1
    if (/[A-Z]/.test(passwordValue)) score += 1
    if (/[0-9]/.test(passwordValue)) score += 1
    if (/[^A-Za-z0-9]/.test(passwordValue)) score += 1
    return score
  }, [passwordValue])

  const onLoginSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    try {
      await login(data.email, data.password)
      toast.success('Welcome back!')
      router.push('/dashboard')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Invalid email or password'
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  const onRegisterSubmit = async (data: RegisterFormData) => {
    setIsLoading(true)
    try {
      await registerUser(data.email, data.password, data.full_name)
      toast.success('Account created successfully!')
      router.push('/dashboard')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed'
      toast.error(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-[400px]">
      {/* Animated Toggle Switcher */}
      <div className="flex bg-slate-800/80 lg:bg-slate-200/80 p-1 rounded-xl mb-6 relative border border-white/10 lg:border-slate-300/60 shadow-inner">
        <motion.div
          layout
          transition={springSnappy}
          className="absolute top-1 bottom-1 rounded-lg bg-primary-500 lg:bg-white shadow-md"
          style={{
            left: mode === 'login' ? '4px' : 'calc(50% + 2px)',
            width: 'calc(50% - 6px)',
          }}
        />
        <button
          type="button"
          onClick={() => setMode('login')}
          className={`flex-1 py-2.5 text-xs font-bold rounded-lg relative z-10 transition-colors ${
            mode === 'login' ? 'text-white lg:text-slate-900' : 'text-slate-400 lg:text-slate-600 hover:text-slate-200'
          }`}
        >
          Sign In
        </button>
        <button
          type="button"
          onClick={() => setMode('register')}
          className={`flex-1 py-2.5 text-xs font-bold rounded-lg relative z-10 transition-colors ${
            mode === 'register' ? 'text-white lg:text-slate-900' : 'text-slate-400 lg:text-slate-600 hover:text-slate-200'
          }`}
        >
          Create Account
        </button>
      </div>

      {/* Form Header */}
      <div className="mb-6 text-center lg:text-left">
        <h2 className="text-2xl font-extrabold text-white lg:text-slate-900 tracking-tight">
          {mode === 'login' ? 'Welcome back' : 'Create an account'}
        </h2>
        <p className="text-xs text-slate-400 lg:text-slate-500 mt-1">
          {mode === 'login'
            ? 'Enter your credentials to access your workspace'
            : 'Join MedAI for AI-assisted clinic management'}
        </p>
      </div>

      {/* Animated Form Container */}
      <AnimatePresence mode="wait">
        {mode === 'login' ? (
          <motion.form
            key="login-form"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={easeOutExpo}
            onSubmit={handleLoginSubmit(onLoginSubmit)}
            className="space-y-4"
          >
            <motion.div variants={staggerContainer} initial="hidden" animate="show" className="space-y-4">
              {/* Email Field */}
              <motion.div variants={fadeSlideUp}>
                <label className="block text-xs font-semibold text-slate-300 lg:text-slate-700 mb-1.5">
                  Email address
                </label>
                <input
                  type="email"
                  placeholder="doctor@clinic.com"
                  {...registerLogin('email')}
                  className="w-full bg-surface-800/80 lg:bg-white border border-white/10 lg:border-slate-300 rounded-xl px-4 py-3 text-white lg:text-slate-900 placeholder-slate-500 lg:placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all shadow-sm"
                  autoComplete="email"
                />
                {loginErrors.email && (
                  <p className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    {loginErrors.email.message}
                  </p>
                )}
              </motion.div>

              {/* Password Field */}
              <motion.div variants={fadeSlideUp}>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-300 lg:text-slate-700">
                    Password
                  </label>
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      toast('Password reset email sent (Demo)', { icon: '📧' })
                    }}
                    className="text-xs font-medium text-primary-400 lg:text-primary-600 hover:underline"
                  >
                    Forgot password?
                  </a>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    {...registerLogin('password')}
                    className="w-full bg-surface-800/80 lg:bg-white border border-white/10 lg:border-slate-300 rounded-xl px-4 py-3 pr-12 text-white lg:text-slate-900 placeholder-slate-500 lg:placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all shadow-sm"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 lg:hover:text-slate-600 transition-colors p-1"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {loginErrors.password && (
                  <p className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    {loginErrors.password.message}
                  </p>
                )}
              </motion.div>

              {/* Submit CTA Button (48px, full width, teal gradient) */}
              <motion.div variants={fadeSlideUp} className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-12 rounded-xl bg-gradient-to-r from-teal-600 via-teal-500 to-cyan-500 hover:from-teal-500 hover:to-cyan-400 text-white font-bold text-sm shadow-glow flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-[0.98]"
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    'Sign In'
                  )}
                </button>
              </motion.div>

              {/* Divider */}
              <motion.div variants={fadeSlideUp} className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10 lg:border-slate-200" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-surface-900 lg:bg-[#fbf9f5] px-3 text-slate-400 lg:text-slate-500 font-medium">
                    or
                  </span>
                </div>
              </motion.div>

              {/* Secondary Google Button */}
              <motion.div variants={fadeSlideUp}>
                <button
                  type="button"
                  onClick={() => toast('Google OAuth coming soon!', { icon: 'ℹ️' })}
                  className="w-full h-12 rounded-xl border border-white/15 lg:border-slate-300 hover:border-teal-500 bg-transparent text-slate-300 lg:text-slate-700 font-semibold text-sm flex items-center justify-center gap-3 transition-all hover:bg-white/5 active:scale-[0.98]"
                >
                  <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  Continue with Google
                </button>
              </motion.div>
            </motion.div>
          </motion.form>
        ) : (
          <motion.form
            key="register-form"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={easeOutExpo}
            onSubmit={handleRegSubmit(onRegisterSubmit)}
            className="space-y-4"
          >
            <motion.div variants={staggerContainer} initial="hidden" animate="show" className="space-y-3">
              {/* Full Name */}
              <motion.div variants={fadeSlideUp}>
                <label className="block text-xs font-semibold text-slate-300 lg:text-slate-700 mb-1.5">
                  Full name
                </label>
                <input
                  type="text"
                  placeholder="Dr. Jane Smith"
                  {...registerReg('full_name')}
                  className="w-full bg-surface-800/80 lg:bg-white border border-white/10 lg:border-slate-300 rounded-xl px-4 py-3 text-white lg:text-slate-900 placeholder-slate-500 lg:placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all shadow-sm"
                />
                {regErrors.full_name && (
                  <p className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    {regErrors.full_name.message}
                  </p>
                )}
              </motion.div>

              {/* Email */}
              <motion.div variants={fadeSlideUp}>
                <label className="block text-xs font-semibold text-slate-300 lg:text-slate-700 mb-1.5">
                  Email address
                </label>
                <input
                  type="email"
                  placeholder="doctor@clinic.com"
                  {...registerReg('email')}
                  className="w-full bg-surface-800/80 lg:bg-white border border-white/10 lg:border-slate-300 rounded-xl px-4 py-3 text-white lg:text-slate-900 placeholder-slate-500 lg:placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all shadow-sm"
                  autoComplete="email"
                />
                {regErrors.email && (
                  <p className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    {regErrors.email.message}
                  </p>
                )}
              </motion.div>

              {/* Password */}
              <motion.div variants={fadeSlideUp}>
                <label className="block text-xs font-semibold text-slate-300 lg:text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Min. 8 characters"
                    {...registerReg('password')}
                    className="w-full bg-surface-800/80 lg:bg-white border border-white/10 lg:border-slate-300 rounded-xl px-4 py-3 pr-12 text-white lg:text-slate-900 placeholder-slate-500 lg:placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all shadow-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 lg:hover:text-slate-600 transition-colors p-1"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {regErrors.password && (
                  <p className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    {regErrors.password.message}
                  </p>
                )}

                {/* Password Strength Bar */}
                {passwordValue && (
                  <div className="mt-2 space-y-1">
                    <div className="flex gap-1 h-1">
                      {[1, 2, 3, 4].map((step) => (
                        <div
                          key={step}
                          className={`flex-1 rounded-full transition-all duration-300 ${
                            passwordStrength >= step
                              ? step === 1
                                ? 'bg-rose-400'
                                : step === 2
                                ? 'bg-amber-400'
                                : step === 3
                                ? 'bg-teal-400'
                                : 'bg-emerald-400'
                              : 'bg-slate-700 lg:bg-slate-200'
                          }`}
                        />
                      ))}
                    </div>
                    <p className="text-[10px] text-slate-400 lg:text-slate-500 font-medium">
                      Strength:{' '}
                      <span className="font-bold">
                        {passwordStrength <= 1
                          ? 'Weak'
                          : passwordStrength === 2
                          ? 'Fair'
                          : passwordStrength === 3
                          ? 'Good'
                          : 'Strong'}
                      </span>
                    </p>
                  </div>
                )}
              </motion.div>

              {/* Confirm Password */}
              <motion.div variants={fadeSlideUp}>
                <label className="block text-xs font-semibold text-slate-300 lg:text-slate-700 mb-1.5">
                  Confirm password
                </label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="Repeat password"
                    {...registerReg('confirm_password')}
                    className="w-full bg-surface-800/80 lg:bg-white border border-white/10 lg:border-slate-300 rounded-xl px-4 py-3 pr-12 text-white lg:text-slate-900 placeholder-slate-500 lg:placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-500 transition-all shadow-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 lg:hover:text-slate-600 transition-colors p-1"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {regErrors.confirm_password && (
                  <p className="flex items-center gap-1 mt-1 text-red-400 text-xs">
                    <AlertCircle className="w-3 h-3 flex-shrink-0" />
                    {regErrors.confirm_password.message}
                  </p>
                )}
              </motion.div>

              {/* Submit CTA */}
              <motion.div variants={fadeSlideUp} className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-12 rounded-xl bg-gradient-to-r from-teal-600 via-teal-500 to-cyan-500 hover:from-teal-500 hover:to-cyan-400 text-white font-bold text-sm shadow-glow flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-[0.98]"
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    'Create Account'
                  )}
                </button>
              </motion.div>

              {/* Divider */}
              <motion.div variants={fadeSlideUp} className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10 lg:border-slate-200" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-surface-900 lg:bg-[#fbf9f5] px-3 text-slate-400 lg:text-slate-500 font-medium">
                    or
                  </span>
                </div>
              </motion.div>

              {/* Secondary Google Button */}
              <motion.div variants={fadeSlideUp}>
                <button
                  type="button"
                  onClick={() => toast('Google OAuth coming soon!', { icon: 'ℹ️' })}
                  className="w-full h-12 rounded-xl border border-white/15 lg:border-slate-300 hover:border-teal-500 bg-transparent text-slate-300 lg:text-slate-700 font-semibold text-sm flex items-center justify-center gap-3 transition-all hover:bg-white/5 active:scale-[0.98]"
                >
                  <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  Continue with Google
                </button>
              </motion.div>
            </motion.div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Trust Footer Note */}
      <p className="text-center text-[11px] text-slate-400 lg:text-slate-500 mt-6 flex items-center justify-center gap-1">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 inline-block" />
        Encrypted & HIPAA-conscious platform
      </p>
    </div>
  )
}

export default function AuthPage() {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-surface-900 overflow-x-hidden">
      {/* ── Desktop Left 45% Visual Panel ────────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[45%] bg-gradient-to-br from-teal-900 via-surface-900 to-slate-900 flex-col justify-between p-12 relative overflow-hidden">
        {/* Animated Background Blobs */}
        <div className="absolute w-96 h-96 rounded-full bg-teal-500/20 blur-3xl -top-20 -left-20 animate-mesh-drift-1" />
        <div className="absolute w-80 h-80 rounded-full bg-cyan-500/15 blur-3xl top-1/2 -right-20 animate-mesh-drift-2" />
        <div className="absolute w-72 h-72 rounded-full bg-emerald-500/15 blur-3xl -bottom-10 left-10 animate-mesh-drift-3" />

        {/* Brand Header */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center shadow-glow">
            <Activity className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <span className="text-xl font-extrabold text-white tracking-wide">MedAI</span>
            <span className="text-[10px] text-teal-300 block font-medium uppercase tracking-wider">
              Clinical Operating System
            </span>
          </div>
        </div>

        {/* Center Hero Copy */}
        <div className="relative z-10 space-y-6 my-auto max-w-md">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-400/20 text-xs font-semibold text-teal-300">
            <Sparkles className="w-3.5 h-3.5 text-teal-400" /> Medical Intelligence Platform
          </div>

          <h1 className="text-4xl font-extrabold text-white leading-tight">
            Intelligent Care, <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-300 via-cyan-200 to-white">
              Powered by AI.
            </span>
          </h1>

          <p className="text-slate-300 text-sm leading-relaxed">
            Streamline patient care, manage doctor availability, and consult our RAG-powered medical assistant in real time.
          </p>

          <div className="space-y-3 pt-4 border-t border-white/10">
            {[
              { icon: BrainCircuit, text: 'RAG-Powered Gemini 2.5 Medical Agent' },
              { icon: ShieldCheck, text: 'HIPAA-Conscious Data Security' },
            ].map(({ icon: Icon, text }, idx) => (
              <div key={idx} className="flex items-center gap-3 text-xs text-slate-200 font-medium">
                <div className="w-6 h-6 rounded-lg bg-teal-500/20 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-3.5 h-3.5 text-teal-400" />
                </div>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Badge */}
        <div className="relative z-10 text-xs text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" /> Encrypted & HIPAA-conscious Platform
        </div>
      </div>

      {/* ── Right 55% Form Area (Desktop: Ivory #fbf9f5; Mobile: Dark Surface) ──── */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 lg:p-12 bg-surface-900 lg:bg-[#fbf9f5] relative min-h-screen lg:min-h-0">
        {/* Mobile Top Brand Header */}
        <div className="lg:hidden w-full max-w-[400px] mb-6 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 shadow-glow mb-2">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">MedAI</h1>
          <p className="text-xs text-slate-400">Intelligent Clinic Management</p>
        </div>

        <Suspense fallback={<div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />}>
          <AuthForm />
        </Suspense>
      </div>
    </div>
  )
}
