'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import {
  Calendar,
  MessageSquare,
  User,
  PlusCircle,
  Clock,
  Stethoscope,
  Sparkles,
  CheckCircle2,
  XCircle,
  Activity,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/lib/auth/context'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'
import { staggerContainer, fadeSlideUp } from '@/lib/motion'

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  loading,
}: {
  label: string
  value: number | string
  icon: typeof Calendar
  color: string
  loading: boolean
}) {
  return (
    <div className={`p-5 rounded-2xl bg-slate-900 border border-slate-800 flex items-center gap-4`}>
      <div className={`w-11 h-11 rounded-xl ${color} flex items-center justify-center shrink-0`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-xs text-slate-400 font-medium">{label}</p>
        {loading ? (
          <div className="h-6 w-14 bg-slate-800 rounded animate-pulse mt-1" />
        ) : (
          <p className="text-2xl font-extrabold text-slate-100 tracking-tight">{value}</p>
        )}
      </div>
    </div>
  )
}

export default function PatientDashboardPage() {
  const { user } = useAuth()
  const searchParams = useSearchParams()
  const [appointments, setAppointments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (searchParams.get('profile_updated') === 'true') {
      toast.success('Personal details have been updated successfully!', { id: 'profile-update' })
    }
  }, [searchParams])

  // Derive a friendly first name — never show an email address as a name
  const firstName = React.useMemo(() => {
    const name = user?.full_name || ''
    // If the name looks like an email address, don't show it
    if (name.includes('@')) return 'there'
    const first = name.trim().split(' ')[0]
    return first || 'there'
  }, [user])

  // Time-based greeting
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get('/medai/appointments')
      setAppointments(res.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch patient appointments', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAppointments()
  }, [])

  // Real-time synchronization when doctor completes visit or updates notes
  useAppointmentSocket((event) => {
    if (
      event.event === 'appointment_updated' ||
      event.event === 'appointment_created' ||
      event.event === 'appointment_cancelled'
    ) {
      fetchAppointments()
    }
  })

  const upcoming = appointments.filter(
    (a) => a.status === 'scheduled' || a.status === 'confirmed'
  )
  const completed = appointments.filter((a) => a.status === 'completed')
  const cancelled = appointments.filter((a) => a.status === 'cancelled')
  const recentCompletedWithNotes = completed.filter((a) => !!a.notes).slice(0, 2)

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="p-6 space-y-7 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-5xl"
    >
      {/* ── Header Greeting ─────────────────────────────────────────────── */}
      <motion.div variants={fadeSlideUp} className="border-b border-slate-800 pb-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              {greeting},{' '}
              <span className="text-teal-400">{firstName}</span> 👋
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Here's your health portal — manage consultations, book specialists, and ask the AI assistant.
            </p>
          </div>
          <Link
            href="/patient/book"
            className="px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-lg shadow-teal-900/30 inline-flex items-center gap-2 transition-colors shrink-0"
          >
            <PlusCircle className="w-4 h-4" />
            Book New Consultation
          </Link>
        </div>
      </motion.div>

      {/* ── Real Stats Row (appointment data only) ──────────────────────── */}
      <motion.div variants={fadeSlideUp} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Upcoming Appointments"
          value={upcoming.length}
          icon={Calendar}
          color="bg-teal-500/10 border border-teal-500/30 text-teal-400"
          loading={loading}
        />
        <StatCard
          label="Completed Visits"
          value={completed.length}
          icon={CheckCircle2}
          color="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
          loading={loading}
        />
        <StatCard
          label="Cancelled"
          value={cancelled.length}
          icon={XCircle}
          color="bg-rose-500/10 border border-rose-500/30 text-rose-400"
          loading={loading}
        />
      </motion.div>

      {/* ── Quick Access Cards ──────────────────────────────────────────── */}
      <motion.div variants={fadeSlideUp} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          href="/patient/book"
          className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-teal-500/40 transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 mb-3">
            <Calendar className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-sm text-slate-100 group-hover:text-teal-300">Book Appointment</h3>
          <p className="text-xs text-slate-400 mt-1">Find specialists & reserve open clinical time slots.</p>
        </Link>

        <Link
          href="/patient/chat"
          className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-indigo-500/40 transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-3">
            <Sparkles className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-sm text-slate-100 group-hover:text-indigo-300">Medical AI Assistant</h3>
          <p className="text-xs text-slate-400 mt-1">Ask health questions grounded in clinical RAG guidelines.</p>
        </Link>

        <Link
          href="/patient/profile"
          className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-600 transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 mb-3">
            <User className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-sm text-slate-100 group-hover:text-slate-200">Medical Profile</h3>
          <p className="text-xs text-slate-400 mt-1">Update blood group, allergies, and emergency contacts.</p>
        </Link>
      </motion.div>

      {/* ── Upcoming Appointments ──────────────────────────────────────── */}
      <motion.div variants={fadeSlideUp} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-teal-400" />
            <h2 className="text-sm font-semibold text-slate-200">Upcoming Appointments</h2>
          </div>
          <Link href="/patient/appointments" className="text-xs text-teal-400 hover:underline flex items-center gap-1">
            <Activity className="w-3.5 h-3.5" />
            View Full History
          </Link>
        </div>

        <div className="space-y-3">
          {loading ? (
            [1, 2].map((i) => (
              <div key={i} className="h-16 bg-slate-800/60 rounded-xl animate-pulse" />
            ))
          ) : upcoming.length === 0 ? (
            <div className="py-10 text-center text-xs text-slate-500 flex flex-col items-center gap-2">
              <Calendar className="w-8 h-8 text-slate-700" />
              <p>No upcoming appointments.</p>
              <Link href="/patient/book" className="text-teal-400 underline hover:text-teal-300">
                Book a consultation →
              </Link>
            </div>
          ) : (
            upcoming.map((appt) => (
              <div
                key={appt.id}
                className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-4 text-xs hover:border-teal-500/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0">
                    <Stethoscope className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-100 capitalize">{appt.appointment_type} Consultation</h4>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                      {new Date(appt.scheduled_at).toLocaleString()}
                    </p>
                    {appt.reason && (
                      <p className="text-[11px] text-slate-500 mt-0.5 italic truncate max-w-xs">{appt.reason}</p>
                    )}
                  </div>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase border shrink-0 ${
                    appt.status === 'confirmed'
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                      : 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                  }`}
                >
                  {appt.status}
                </span>
              </div>
            ))
          )}
        </div>
      </motion.div>

      {/* ── Recent Consultation Notes & Prescriptions ────────────────────── */}
      {recentCompletedWithNotes.length > 0 && (
        <motion.div variants={fadeSlideUp} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-slate-200">Recent Completed Consultation Records</h2>
            </div>
            <Link href="/patient/appointments" className="text-xs text-teal-400 hover:underline flex items-center gap-1">
              View All Records →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recentCompletedWithNotes.map((c) => (
              <Link
                key={c.id}
                href="/patient/appointments"
                className="p-4 rounded-xl bg-slate-950 border border-slate-800 hover:border-teal-500/40 transition-all block group"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-slate-400">
                    {new Date(c.scheduled_at).toLocaleDateString()}
                  </span>
                  <span className="text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Notes Available
                  </span>
                </div>
                <p className="text-xs text-slate-300 line-clamp-2 italic group-hover:text-slate-100">
                  {c.notes}
                </p>
                <div className="mt-3 text-[11px] text-teal-400 group-hover:underline flex items-center gap-1 font-medium">
                  Review Clinical Notes &amp; Prescription →
                </div>
              </Link>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
