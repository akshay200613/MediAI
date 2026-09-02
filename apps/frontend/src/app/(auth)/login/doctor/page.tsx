'use client'

import { useState, useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  ShieldCheck,
  Eye,
  EyeOff,
  AlertCircle,
  Stethoscope,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  Clock,
  FileText,
  Phone,
  Briefcase,
  Calendar,
  ArrowRight,
} from 'lucide-react'
import { useAuth } from '@/lib/auth/context'
import { authApi } from '@/lib/api/auth'
import apiClient from '@/lib/api/client'
import { extractErrorMessage } from '@/lib/utils'
import toast from 'react-hot-toast'
import { springSnappy, easeOutExpo } from '@/lib/motion'
import Link from 'next/link'

const loginSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Minimum 8 characters'),
})

const step1Schema = z.object({
  full_name: z.string().min(2, 'Full name required'),
  email: z.string().email('Invalid email'),
  phone: z.string().min(7, 'Valid phone required'),
  password: z.string().min(8, 'Minimum 8 characters'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: "Passwords don't match",
  path: ['confirm_password'],
})

const step2Schema = z.object({
  specialty: z.string().min(2, 'Specialty required'),
  license_number: z.string().min(3, 'License number required'),
  years_of_experience: z.coerce.number().min(0),
  consultation_fee: z.coerce.number().min(0),
  bio: z.string().optional(),
})

const step3Schema = z.object({
  available_days: z.string().min(1, 'Select at least one day'),
  working_hours_start: z.string().min(1, 'Start time required'),
  working_hours_end: z.string().min(1, 'End time required'),
})

type LoginForm = z.infer<typeof loginSchema>
type Step1 = z.infer<typeof step1Schema>
type Step2 = z.infer<typeof step2Schema>
type Step3 = z.infer<typeof step3Schema>

const inputCls = 'w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/20 transition-all shadow-sm'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const SPECIALTIES = [
  'General Medicine', 'Cardiology', 'Dermatology', 'Endocrinology',
  'Gastroenterology', 'Neurology', 'Obstetrics & Gynecology', 'Oncology',
  'Ophthalmology', 'Orthopedics', 'Pediatrics', 'Psychiatry',
  'Pulmonology', 'Radiology', 'Surgery', 'Urology', 'ENT', 'Physiology',
]

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-300 mb-1.5">{label}</label>
      {children}
      {error && (
        <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs">
          <AlertCircle className="w-3 h-3 flex-shrink-0" />{error}
        </p>
      )}
    </div>
  )
}

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

function DoctorLoginForm({ onRegisterClick, onForgotClick }: { onRegisterClick: () => void; onForgotClick: () => void }) {
  const [showPwd, setShowPwd] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const router = useRouter()
  const form = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    try {
      const user = await login(data.email, data.password)
      if (!user.is_verified) {
        toast('Your doctor account is pending administrator approval.', { icon: '⏳', duration: 5000 })
        router.push('/pending-approval')
        return
      }
      if (user.role !== 'doctor' && user.role !== 'admin' && user.role !== 'super_admin') {
        toast.error('This account is not registered as a doctor.')
        return
      }
      toast.success('Welcome to your clinical dashboard!')
      router.push('/doctor')
    } catch (err: any) {
      toast.error(extractErrorMessage(err))
    } finally { setIsLoading(false) }
  }

  return (
    <div className="space-y-4">
      <Field label="Doctor Email" error={form.formState.errors.email?.message}>
        <input type="email" placeholder="dr.name@hospital.com" {...form.register('email')} className={inputCls} autoComplete="email" />
      </Field>
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-slate-300">Password</label>
          <button
            type="button"
            onClick={onForgotClick}
            className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Forgot password?
          </button>
        </div>
        <div className="relative">
          <input type={showPwd ? 'text' : 'password'} placeholder="••••••••"
            {...form.register('password')} className={`${inputCls} pr-12`} autoComplete="current-password" />
          <button type="button" onClick={() => setShowPwd(!showPwd)}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-1">
            {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {form.formState.errors.password && (
          <div className="text-[11px] text-rose-400 mt-1 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            <span>{form.formState.errors.password.message}</span>
          </div>
        )}
      </div>
      <button onClick={form.handleSubmit(onSubmit)} disabled={isLoading}
        className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50">
        {isLoading ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <><Stethoscope className="w-4 h-4" /> Sign In to Doctor Portal</>}
      </button>
      <div className="relative py-1">
        <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-800" /></div>
        <div className="relative flex justify-center text-xs"><span className="bg-slate-950 px-3 text-slate-500">New doctor?</span></div>
      </div>
      <button type="button" onClick={onRegisterClick}
        className="w-full h-10 rounded-xl border border-indigo-500/40 hover:border-indigo-500 text-indigo-400 font-semibold text-xs flex items-center justify-center gap-2 transition-all hover:bg-indigo-500/5">
        Register as a Doctor <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

function DoctorForgotPasswordWizard({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      toast.error('Please enter your doctor email address.')
      return
    }
    setLoading(true)
    try {
      await apiClient.post('/auth/forgot-password', { email })
      toast.success('Password reset request submitted to Admin!')
      setSubmitted(true)
    } catch (err: any) {
      toast.error(extractErrorMessage(err) || 'Failed to process request.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {!submitted ? (
        <form onSubmit={handleRequestReset} className="space-y-4">
          <div className="text-center mb-2">
            <h3 className="text-base font-bold text-slate-100">Forgot Doctor Password?</h3>
            <p className="text-xs text-slate-400 mt-1">Enter your registered doctor email address. Requesting a reset will instantly notify Admin to reset your password.</p>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Doctor Email</label>
            <input
              type="email"
              required
              placeholder="dr.name@hospital.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputCls}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {loading ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : 'Request Reset from Admin'}
          </button>
          <button
            type="button"
            onClick={onBackToLogin}
            className="w-full text-center text-xs text-slate-400 hover:text-slate-200 mt-2 block"
          >
            ← Back to Doctor Sign In
          </button>
        </form>
      ) : (
        <div className="text-center space-y-4 py-4">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-100">Reset Request Submitted!</h3>
          <p className="text-xs text-slate-400">Admin has been notified via real-time alert to reset your credentials. Please contact your system administrator or log in once updated.</p>
          <button
            type="button"
            onClick={onBackToLogin}
            className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-900/30 transition-colors"
          >
            Return to Doctor Sign In
          </button>
        </div>
      )}
    </div>
  )
}

function DoctorRegisterWizard({ onDone, onBack }: { onDone: () => void; onBack: () => void }) {
  const [step, setStep] = useState(1)
  const [step1Data, setStep1Data] = useState<Step1 | null>(null)
  const [step2Data, setStep2Data] = useState<Step2 | null>(null)
  const [selectedDays, setSelectedDays] = useState<string[]>(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showPwd, setShowPwd] = useState(false)
  const [showCPwd, setShowCPwd] = useState(false)

  const f1 = useForm<Step1>({ resolver: zodResolver(step1Schema) })
  const f2 = useForm<Step2>({ resolver: zodResolver(step2Schema) })
  const f3 = useForm<Step3>({
    resolver: zodResolver(step3Schema),
    defaultValues: {
      available_days: 'Mon,Tue,Wed,Thu,Fri',
      working_hours_start: '09:00',
      working_hours_end: '17:00',
    },
  })
  const pwdVal = f1.watch('password', '')

  const toggleDay = (day: string) => {
    const next = selectedDays.includes(day) ? selectedDays.filter((d) => d !== day) : [...selectedDays, day]
    setSelectedDays(next)
    f3.setValue('available_days', next.join(','))
  }

  const handleStep3 = async (data: Step3) => {
    if (!step1Data || !step2Data) return
    setIsSubmitting(true)
    try {
      await authApi.registerDoctor({
        email: step1Data.email,
        password: step1Data.password,
        full_name: step1Data.full_name,
        phone: step1Data.phone,
        specialty: step2Data.specialty,
        license_number: step2Data.license_number,
        years_of_experience: step2Data.years_of_experience,
        bio: step2Data.bio,
        consultation_fee: step2Data.consultation_fee,
        available_days: selectedDays.length > 0 ? selectedDays.join(',') : 'Mon,Tue,Wed,Thu,Fri',
        working_hours_start: data.working_hours_start || '09:00',
        working_hours_end: data.working_hours_end || '17:00',
      })
      toast.success('Doctor registration submitted! Your account is pending administrator approval.', { duration: 6000 })
      onDone()
    } catch (err: any) {
      toast.error(extractErrorMessage(err))
    } finally { setIsSubmitting(false) }
  }

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="flex items-center gap-1">
        {['Personal Info', 'Professional', 'Availability'].map((label, i) => (
          <div key={i} className="flex items-center gap-1 flex-1">
            <div className="flex items-center gap-1.5">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border transition-all flex-shrink-0 ${step > i + 1 ? 'bg-indigo-500 border-indigo-500 text-white' : step === i + 1 ? 'border-indigo-500 text-indigo-400' : 'border-slate-700 text-slate-600'}`}>
                {step > i + 1 ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span className={`text-[10px] hidden sm:block ${step >= i + 1 ? 'text-indigo-300' : 'text-slate-600'}`}>{label}</span>
            </div>
            {i < 2 && <div className={`flex-1 h-px mx-1 ${step > i + 1 ? 'bg-indigo-500' : 'bg-slate-800'}`} />}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {step === 1 && (
          <motion.form key="s1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
            transition={easeOutExpo} onSubmit={f1.handleSubmit((d) => { setStep1Data(d); setStep(2) })} className="space-y-3">
            <p className="text-xs text-slate-400">Step 1 — Personal &amp; login details</p>
            <Field label="Full Name" error={f1.formState.errors.full_name?.message}>
              <input type="text" placeholder="Dr. Full Name" {...f1.register('full_name')} className={inputCls} />
            </Field>
            <Field label="Email Address" error={f1.formState.errors.email?.message}>
              <input type="email" placeholder="dr.name@hospital.com" {...f1.register('email')} className={inputCls} />
            </Field>
            <Field label="Phone Number" error={f1.formState.errors.phone?.message}>
              <div className="relative">
                <Phone className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input type="tel" placeholder="+91 98765 43210" {...f1.register('phone')} className={`${inputCls} pl-9`} />
              </div>
            </Field>
            <Field label="Password" error={f1.formState.errors.password?.message}>
              <div className="relative">
                <input type={showPwd ? 'text' : 'password'} placeholder="Min. 8 characters" {...f1.register('password')} className={`${inputCls} pr-10`} />
                <button type="button" onClick={() => setShowPwd(!showPwd)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200">
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <PasswordStrength value={pwdVal} />
            </Field>
            <Field label="Confirm Password" error={f1.formState.errors.confirm_password?.message}>
              <div className="relative">
                <input type={showCPwd ? 'text' : 'password'} placeholder="Repeat password" {...f1.register('confirm_password')} className={`${inputCls} pr-10`} />
                <button type="button" onClick={() => setShowCPwd(!showCPwd)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200">
                  {showCPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </Field>
            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onBack} className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 hover:text-white text-xs font-medium transition-colors">← Login</button>
              <button type="submit" className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all">
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </motion.form>
        )}

        {step === 2 && (
          <motion.form key="s2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
            transition={easeOutExpo} onSubmit={f2.handleSubmit((d) => { setStep2Data(d); setStep(3) })} className="space-y-3">
            <p className="text-xs text-slate-400">Step 2 — Professional credentials</p>
            <Field label="Medical Specialty" error={f2.formState.errors.specialty?.message}>
              <select {...f2.register('specialty')} className={inputCls}>
                <option value="">Select specialty...</option>
                {SPECIALTIES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Medical License Number" error={f2.formState.errors.license_number?.message}>
              <div className="relative">
                <FileText className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input type="text" placeholder="e.g. MH-12345-2019" {...f2.register('license_number')} className={`${inputCls} pl-9`} />
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Years of Exp." error={f2.formState.errors.years_of_experience?.message}>
                <input type="number" min="0" placeholder="0" {...f2.register('years_of_experience')} className={inputCls} />
              </Field>
              <Field label="Fee (₹)" error={f2.formState.errors.consultation_fee?.message}>
                <input type="number" min="0" placeholder="500" {...f2.register('consultation_fee')} className={inputCls} />
              </Field>
            </div>
            <Field label="Professional Bio (optional)">
              <textarea rows={2} placeholder="Brief expertise summary..." {...f2.register('bio')} className={`${inputCls} resize-none`} />
            </Field>
            <div className="flex gap-3 pt-1">
              <button type="button" onClick={() => setStep(1)} className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 hover:text-white text-xs font-medium transition-colors flex items-center gap-1">
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button type="submit" className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all">
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </motion.form>
        )}

        {step === 3 && (
          <motion.form key="s3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
            transition={easeOutExpo} onSubmit={f3.handleSubmit(handleStep3)} className="space-y-4">
            <p className="text-xs text-slate-400">Step 3 — Availability schedule</p>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">Available Days</label>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((day) => (
                  <button key={day} type="button" onClick={() => toggleDay(day)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${selectedDays.includes(day) ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300' : 'border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-400'}`}>
                    {day}
                  </button>
                ))}
              </div>
              {f3.formState.errors.available_days && (
                <p className="flex items-center gap-1 mt-1 text-rose-400 text-xs"><AlertCircle className="w-3 h-3" /> Select at least one day</p>
              )}
              <input type="hidden" {...f3.register('available_days')} value={selectedDays.join(',')} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start Time" error={f3.formState.errors.working_hours_start?.message}>
                <input type="time" {...f3.register('working_hours_start')} className={inputCls} defaultValue="09:00" />
              </Field>
              <Field label="End Time" error={f3.formState.errors.working_hours_end?.message}>
                <input type="time" {...f3.register('working_hours_end')} className={inputCls} defaultValue="17:00" />
              </Field>
            </div>
            {step1Data && step2Data && (
              <div className="p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-xs space-y-1 text-slate-300">
                <p className="font-semibold text-indigo-300 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Registration Summary</p>
                <p><span className="text-slate-500">Name:</span> {step1Data.full_name}</p>
                <p><span className="text-slate-500">Specialty:</span> {step2Data.specialty}</p>
                <p><span className="text-slate-500">License:</span> {step2Data.license_number}</p>
              </div>
            )}
            <p className="text-[11px] text-amber-400 flex items-start gap-1.5">
              <Clock className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              Admin must approve your account before dashboard access is granted.
            </p>
            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(2)} className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 hover:text-white text-xs font-medium transition-colors flex items-center gap-1">
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button type="submit" disabled={isSubmitting} className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50">
                {isSubmitting ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <><CheckCircle2 className="w-4 h-4" /> Submit Registration</>}
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  )
}

function PendingScreen({ onLoginClick }: { onLoginClick: () => void }) {
  return (
    <div className="text-center space-y-4 py-4">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mx-auto shadow-lg shadow-amber-900/20">
        <Clock className="w-8 h-8 animate-pulse" />
      </div>
      <div>
        <h3 className="text-xl font-extrabold text-slate-100">Doctor Application Received</h3>
        <p className="text-xs text-slate-400 mt-1 leading-relaxed">
          Thank you for registering! Your clinical credentials have been recorded.
        </p>
      </div>

      <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 text-left space-y-2">
        <div className="flex items-center gap-2 font-bold text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Status: Pending Administrative Verification</span>
        </div>
        <p className="text-slate-300 text-[11px] leading-relaxed">
          Our clinical administration team will verify your medical license number and professional credentials before activating full physician dashboard privileges.
        </p>
      </div>

      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 text-left space-y-1.5">
        <p className="font-semibold text-slate-200">What to expect:</p>
        <p className="flex items-center gap-1.5">• <span>License &amp; specialty verification</span></p>
        <p className="flex items-center gap-1.5">• <span>Automatic activation upon admin sign-off</span></p>
        <p className="flex items-center gap-1.5">• <span>Instant access to patient rosters &amp; AI assistant</span></p>
      </div>

      <button
        onClick={onLoginClick}
        className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-900/30 transition-all flex items-center justify-center gap-2"
      >
        <Stethoscope className="w-4 h-4" /> Return to Doctor Sign In
      </button>
    </div>
  )
}

import { Suspense } from 'react'

function DoctorLoginContent() {
  const searchParams = useSearchParams()
  const initialMode = searchParams?.get('mode') === 'register' ? 'register' : 'login'
  const [view, setView] = useState<'login' | 'register' | 'pending' | 'forgot'>(initialMode)

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between font-sans relative overflow-hidden">
      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Left Branding Panel */}
        <div className="hidden lg:flex flex-1 flex-col justify-between p-12 bg-gradient-to-br from-indigo-950/60 via-slate-900 to-slate-950 border-r border-slate-800 relative">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-900/50">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-white text-lg tracking-tight">MediAI</span>
              <span className="text-[10px] uppercase font-bold text-indigo-400 block tracking-widest -mt-1">Clinical Portal</span>
            </div>
          </div>

          <div className="space-y-6 max-w-md">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" /> Professional Provider Suite
            </div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight leading-tight">
              Streamline consultations, patient records, & AI diagnostics.
            </h1>
            <p className="text-xs text-slate-400 leading-relaxed">
              Empowering healthcare providers with real-time patient history, automated intake summary, and seamless scheduling.
            </p>
          </div>

          <div className="text-xs text-slate-500">
            © MediAI Health Technologies. Encrypted & HIPAA compliant.
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="flex-1 flex flex-col justify-center items-center p-6 lg:p-12 bg-slate-950 min-h-screen lg:min-h-0">
          <div className="w-full max-w-[420px]">
            {view !== 'pending' && view !== 'forgot' && (
              <>
                <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl mb-5 relative shadow-inner">
                  <motion.div layout transition={springSnappy}
                    className="absolute top-1 bottom-1 rounded-lg bg-indigo-600 shadow-md"
                    style={{ left: view === 'login' ? '4px' : 'calc(50% + 2px)', width: 'calc(50% - 6px)' }}
                  />
                  {(['login', 'register'] as const).map((v) => (
                    <button key={v} type="button" onClick={() => setView(v)}
                      className={`flex-1 py-2.5 text-xs font-bold rounded-lg relative z-10 transition-colors ${view === v ? 'text-white' : 'text-slate-400 hover:text-slate-200'}`}>
                      {v === 'login' ? 'Doctor Sign In' : 'Register as Doctor'}
                    </button>
                  ))}
                </div>
                <div className="mb-5 text-center">
                  <h2 className="text-xl font-extrabold text-slate-100 tracking-tight">
                    {view === 'login' ? 'Doctor Portal Login' : 'Doctor Registration'}
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    {view === 'login' ? 'Access your clinical dashboard' : '3-step professional registration'}
                  </p>
                </div>
              </>
            )}

            <AnimatePresence mode="wait">
              {view === 'login' && (
                <motion.div key="login" initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 12 }} transition={easeOutExpo}>
                  <DoctorLoginForm onRegisterClick={() => setView('register')} onForgotClick={() => setView('forgot')} />
                </motion.div>
              )}
              {view === 'forgot' && (
                <motion.div key="forgot" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={easeOutExpo}>
                  <DoctorForgotPasswordWizard onBackToLogin={() => setView('login')} />
                </motion.div>
              )}
              {view === 'register' && (
                <motion.div key="register" initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} transition={easeOutExpo}>
                  <DoctorRegisterWizard onDone={() => setView('pending')} onBack={() => setView('login')} />
                </motion.div>
              )}
              {view === 'pending' && (
                <motion.div key="pending" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={easeOutExpo}>
                  <PendingScreen onLoginClick={() => setView('login')} />
                </motion.div>
              )}
            </AnimatePresence>

            <div className="mt-6 pt-4 border-t border-slate-800/60 text-center">
              <Link href="/login" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                ← Back to Patient Portal
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DoctorLoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500 text-xs">Loading...</div>}>
      <DoctorLoginContent />
    </Suspense>
  )
}
