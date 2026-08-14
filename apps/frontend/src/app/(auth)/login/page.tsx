'use client'

import { useState, useMemo, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  ShieldCheck,
  Sparkles,
  BrainCircuit,
  Eye,
  EyeOff,
  AlertCircle,
  Stethoscope,
  User as UserIcon,
  Calendar,
} from 'lucide-react'
import { useAuth } from '@/lib/auth/context'
import { extractErrorMessage } from '@/lib/utils'
import toast from 'react-hot-toast'
import { springSnappy, easeOutExpo } from '@/lib/motion'
import Link from 'next/link'

// ─── Schemas ─────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

const registerSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
})

type LoginForm = z.infer<typeof loginSchema>
type RegisterForm = z.infer<typeof registerSchema>

const inputCls = 'w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:border-teal-500 transition-all shadow-sm'

function PasswordStrength({ value }: { value: string }) {
  const score = useMemo(() => {
    if (!value) return 0
    let s = 0
    if (value.length >= 8) s++
    if (/[A-Z]/.test(value)) s++
    if (/[0-9]/.test(value)) s++
    if (/[^A-Za-z0-9]/.test(value)) s++
    return s
  }, [value])
  if (!value) return null
  const colors = ['bg-rose-500', 'bg-amber-500', 'bg-yellow-400', 'bg-emerald-500']
  const labels = ['Weak', 'Fair', 'Good', 'Strong']
  return (
    <div className="flex items-center gap-2 mt-1.5">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className={`h-1 flex-1 rounded-full transition-all ${i < score ? colors[score - 1] : 'bg-slate-800'}`} />
      ))}
      <span className="text-[10px] text-slate-400">{labels[Math.max(0, score - 1)]}</span>
    </div>
  )
}

// ─── Auth Form (Patient / General User) ──────────────────────────────────────

function AuthForm() {
  const searchParams = useSearchParams()
  const initialMode = searchParams?.get('mode') === 'register' ? 'register' : 'login'

  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPwd, setShowConfirmPwd] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const { login, register: registerUser } = useAuth()
  const router = useRouter()

  const redirectByRole = (user: any) => {
    if (!user.is_verified) { router.push('/pending-approval'); return }
    if (user.role === 'admin' || user.role === 'super_admin') router.push('/admin')
    else if (user.role === 'doctor') router.push('/doctor')
    else if (user.role === 'patient' || user.role === 'user') router.push('/patient')
    else router.push('/dashboard')
  }

  const loginForm = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })
  const regForm = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) })
  const pwdVal = regForm.watch('password', '')

  const onLogin = async (data: LoginForm) => {
    setIsLoading(true)
    try {
      const user = await login(data.email, data.password)
      toast.success('Welcome back!')
      redirectByRole(user)
    } catch (err: any) {
      toast.error(extractErrorMessage(err))
    } finally { setIsLoading(false) }
  }

  const onRegister = async (data: RegisterForm) => {
    setIsLoading(true)
    try {
      const user = await registerUser(data.email, data.password, data.full_name)
      toast.success('Account created!')
      redirectByRole(user)
    } catch (err: any) {
      toast.error(extractErrorMessage(err))
    } finally { setIsLoading(false) }
  }

  return (
    <div className="w-full max-w-[420px]">
      {/* Mode Switcher */}
      <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl mb-6 relative shadow-inner">
        <motion.div layout transition={springSnappy}
          className="absolute top-1 bottom-1 rounded-lg bg-teal-600 shadow-md"
          style={{ left: mode === 'login' ? '4px' : 'calc(50% + 2px)', width: 'calc(50% - 6px)' }}
        />
        {(['login', 'register'] as const).map((m) => (
          <button key={m} type="button" onClick={() => setMode(m)}
            className={`flex-1 py-2.5 text-xs font-bold rounded-lg relative z-10 transition-colors ${mode === m ? 'text-white' : 'text-slate-400 hover:text-slate-200'}`}>
            {m === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        ))}
      </div>

      {/* Header */}
      <div className="mb-6 text-center">
        <h2 className="text-2xl font-extrabold text-slate-100 tracking-tight">
          {mode === 'login' ? 'Welcome back' : 'Create an account'}
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          {mode === 'login' ? 'Sign in to access your MediAI health portal' : 'Join MediAI for AI-powered health support'}
        </p>
      </div>

      <AnimatePresence mode="wait">
        {/* Login */}
        {mode === 'login' && (
          <motion.form key="login" initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 12 }}
            transition={easeOutExpo} onSubmit={loginForm.handleSubmit(onLogin)} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Email Address</label>
              <input type="email" placeholder="you@email.com" {...loginForm.register('email')} className={inputCls} autoComplete="email" />
              {loginForm.formState.errors.email && (
                <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs">
                  <AlertCircle className="w-3 h-3" />{loginForm.formState.errors.email.message}
                </p>
              )}
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300">Password</label>
                <a href="#" onClick={(e) => { e.preventDefault(); toast('Password reset link sent (Demo)', { icon: '📧' }) }}
                  className="text-xs text-teal-400 hover:underline">Forgot password?</a>
              </div>
              <div className="relative">
                <input type={showPassword ? 'text' : 'password'} placeholder="••••••••"
                  {...loginForm.register('password')} className={`${inputCls} pr-12`} autoComplete="current-password" />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-1">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {loginForm.formState.errors.password && (
                <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs">
                  <AlertCircle className="w-3 h-3" />{loginForm.formState.errors.password.message}
                </p>
              )}
            </div>
            <button type="submit" disabled={isLoading}
              className="w-full h-11 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs shadow-lg shadow-teal-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50">
              {isLoading ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : 'Sign In'}
            </button>
          </motion.form>
        )}

        {/* Register */}
        {mode === 'register' && (
          <motion.form key="register" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }}
            transition={easeOutExpo} onSubmit={regForm.handleSubmit(onRegister)} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Full Name</label>
              <input type="text" placeholder="Your full name" {...regForm.register('full_name')} className={inputCls} />
              {regForm.formState.errors.full_name && (
                <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs">
                  <AlertCircle className="w-3 h-3" />{regForm.formState.errors.full_name.message}
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Email Address</label>
              <input type="email" placeholder="you@email.com" {...regForm.register('email')} className={inputCls} autoComplete="email" />
              {regForm.formState.errors.email && (
                <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs">
                  <AlertCircle className="w-3 h-3" />{regForm.formState.errors.email.message}
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <input type={showPassword ? 'text' : 'password'} placeholder="Min. 8 characters"
                  {...regForm.register('password')} className={`${inputCls} pr-10`} />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <PasswordStrength value={pwdVal} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Confirm Password</label>
              <div className="relative">
                <input type={showConfirmPwd ? 'text' : 'password'} placeholder="Repeat password"
                  {...regForm.register('confirm_password')} className={`${inputCls} pr-10`} />
                <button type="button" onClick={() => setShowConfirmPwd(!showConfirmPwd)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200">
                  {showConfirmPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {regForm.formState.errors.confirm_password && (
                <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs">
                  <AlertCircle className="w-3 h-3" />{regForm.formState.errors.confirm_password.message}
                </p>
              )}
            </div>
            <button type="submit" disabled={isLoading}
              className="w-full h-11 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs shadow-lg shadow-teal-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50">
              {isLoading ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : 'Create Account'}
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Other portal links */}
      <div className="mt-6 pt-5 border-t border-slate-800/60 space-y-2">
        <p className="text-[11px] text-slate-500 text-center mb-3">Other portals</p>
        <Link href="/login/doctor"
          className="flex items-center justify-between w-full px-4 py-3 rounded-xl border border-slate-800 hover:border-indigo-500/40 hover:bg-indigo-500/5 text-slate-400 hover:text-indigo-300 transition-all group">
          <div className="flex items-center gap-2.5">
            <Stethoscope className="w-4 h-4 text-indigo-400" />
            <div>
              <p className="text-xs font-semibold">Doctor Portal</p>
              <p className="text-[10px] text-slate-600">Login or register as a physician</p>
            </div>
          </div>
          <span className="text-[10px] text-slate-600 group-hover:text-indigo-400">→</span>
        </Link>
        <Link href="/login/admin"
          className="flex items-center justify-between w-full px-4 py-3 rounded-xl border border-slate-800 hover:border-amber-500/30 hover:bg-amber-500/5 text-slate-400 hover:text-amber-300 transition-all group">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-4 h-4 text-amber-400" />
            <div>
              <p className="text-xs font-semibold">Admin Console</p>
              <p className="text-[10px] text-slate-600">Restricted — administrators only</p>
            </div>
          </div>
          <span className="text-[10px] text-slate-600 group-hover:text-amber-400">→</span>
        </Link>
      </div>

      <p className="text-center text-[11px] text-slate-500 mt-5 flex items-center justify-center gap-1">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 inline-block" />
        Encrypted &amp; HIPAA-conscious platform
      </p>
    </div>
  )
}

// ─── Page Shell ───────────────────────────────────────────────────────────────

export default function AuthPage() {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-slate-950 text-slate-100 font-sans overflow-x-hidden">
      {/* Visual Panel */}
      <div className="hidden lg:flex lg:w-[45%] bg-gradient-to-br from-teal-950 via-slate-950 to-slate-900 flex-col justify-between p-12 relative overflow-hidden border-r border-slate-800/80">
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center shadow-glow">
            <Activity className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <span className="text-xl font-extrabold text-white tracking-wide">MedAI</span>
            <span className="text-[10px] text-teal-300 block font-medium uppercase tracking-wider">Clinical Operating System</span>
          </div>
        </div>

        <div className="relative z-10 space-y-6 my-auto max-w-md">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-400/20 text-xs font-semibold text-teal-300">
            <Sparkles className="w-3.5 h-3.5 text-teal-400" /> Medical Intelligence Platform
          </div>
          <h1 className="text-4xl font-extrabold text-white leading-tight">
            Your Health, <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-300 via-cyan-200 to-white">
              Powered by AI.
            </span>
          </h1>
          <p className="text-slate-300 text-sm leading-relaxed">
            Book appointments, consult our RAG-powered AI health assistant, and manage your medical profile — all in one place.
          </p>
          <div className="space-y-3 pt-4 border-t border-slate-800">
            {[
              { icon: BrainCircuit, text: 'RAG-Powered Gemini 2.5 Medical AI Assistant' },
              { icon: Calendar, text: 'Book & Manage Doctor Appointments' },
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

        <div className="relative z-10 text-xs text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" /> Encrypted &amp; HIPAA-conscious Platform
        </div>
      </div>

      {/* Form Area */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 lg:p-12 bg-slate-950 min-h-screen lg:min-h-0">
        <Suspense fallback={<div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />}>
          <AuthForm />
        </Suspense>
      </div>
    </div>
  )
}
