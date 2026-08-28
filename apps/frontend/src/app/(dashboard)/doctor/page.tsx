'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Calendar,
  CheckCircle2,
  Clock,
  User,
  ArrowRight,
  Activity,
  FileText,
  Sparkles,
  Stethoscope,
  TrendingUp,
  Users,
  AlertCircle,
  ChevronRight,
  Bell,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/lib/auth/context'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

interface TodayAppointment {
  id: string
  patient_id: string
  patient_name: string
  patient_phone?: string
  appointment_type: string
  status: string
  scheduled_at: string
  duration_minutes: number
  reason?: string
  notes?: string
}

interface DashboardData {
  count: number
  appointments: TodayAppointment[]
  doctor_name: string
  doctor_specialty: string
}

const statusConfig: Record<string, { label: string; cls: string }> = {
  scheduled: { label: 'Scheduled', cls: 'bg-teal-500/10 text-teal-300 border-teal-500/20' },
  confirmed: { label: 'Confirmed', cls: 'bg-blue-500/10 text-blue-300 border-blue-500/20' },
  in_progress: { label: 'In Progress', cls: 'bg-amber-500/10 text-amber-300 border-amber-500/20' },
  completed: { label: 'Completed', cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' },
  cancelled: { label: 'Cancelled', cls: 'bg-rose-500/10 text-rose-300 border-rose-500/20' },
  no_show: { label: 'No Show', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number | string; icon: typeof Calendar; color: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl"
    >
      <div className="flex items-center justify-between text-slate-400 mb-2">
        <span className="text-xs font-medium">{label}</span>
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className={`text-3xl font-bold ${color.includes('teal') ? 'text-teal-300' : color.includes('emerald') ? 'text-emerald-400' : color.includes('amber') ? 'text-amber-400' : 'text-slate-100'}`}>
        {value}
      </p>
    </motion.div>
  )
}

export default function DoctorDashboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [allAppointments, setAllAppointments] = useState<TodayAppointment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [adminNotice, setAdminNotice] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [todayRes, allRes] = await Promise.allSettled([
        apiClient.get('/medai/doctor-dashboard/today'),
        apiClient.get('/medai/appointments'),
      ])

      if (todayRes.status === 'fulfilled') {
        setData(todayRes.value.data?.data || null)
      }
      if (allRes.status === 'fulfilled') {
        setAllAppointments(allRes.value.data?.data || [])
      }
    } catch (err: any) {
      setError('Failed to load dashboard data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useAppointmentSocket((event) => {
    if (event.event === 'doctor_updated') {
      setAdminNotice(event.message || 'Admin has updated your profile details and working schedule.')
      fetchData()
    } else if (
      event.event === 'appointment_updated' ||
      event.event === 'appointment_created' ||
      event.event === 'appointment_cancelled'
    ) {
      fetchData()
    }
  })

  useEffect(() => {
    fetchData()
  }, [])

  const completed = allAppointments.filter((a) => a.status === 'completed').length
  const upcoming = allAppointments.filter((a) => a.status === 'scheduled' || a.status === 'confirmed').length
  const todayCount = data?.count ?? 0
  const todayAppointments = data?.appointments ?? []
  const doctorName = data?.doctor_name || user?.full_name || 'Doctor'
  const specialty = data?.doctor_specialty || ''

  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening'

  if (loading) {
    return (
      <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-800 rounded-xl w-64" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => <div key={i} className="h-28 bg-slate-900 rounded-2xl border border-slate-800" />)}
          </div>
          <div className="h-64 bg-slate-900 rounded-2xl border border-slate-800" />
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      {/* ── Admin Profile Update Alert Banner ── */}
      {adminNotice && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between shadow-xl animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center shrink-0">
              <Bell className="w-4 h-4 text-amber-400 animate-bounce" />
            </div>
            <div>
              <p className="font-bold text-amber-200">Admin Profile Update Alert</p>
              <p className="text-[11px] text-amber-300/90 mt-0.5">{adminNotice}</p>
            </div>
          </div>
          <button
            onClick={() => setAdminNotice(null)}
            className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 rounded-xl font-semibold text-xs transition-colors shrink-0"
          >
            Dismiss Alert
          </button>
        </div>
      )}

      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Stethoscope className="w-4 h-4 text-indigo-400" />
            </div>
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wide">{specialty || 'Physician'}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            {greeting}, {doctorName.replace(/^Dr\.\s*/i, 'Dr. ')}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            {' '}• Clinical dashboard overview
          </p>
        </div>
        <Link
          href="/doctor/appointments"
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-900/30 flex items-center gap-2 transition-colors"
        >
          Open Clinical Roster
          <ArrowRight className="w-4 h-4" />
        </Link>
      </motion.div>

      {/* ── Metric Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Today's Appointments" value={todayCount} icon={Calendar} color="bg-teal-500/10 text-teal-400" />
        <StatCard label="Completed Consultations" value={completed} icon={CheckCircle2} color="bg-emerald-500/10 text-emerald-400" />
        <StatCard label="Upcoming Visits" value={upcoming} icon={Clock} color="bg-amber-500/10 text-amber-400" />
      </div>

      {/* ── Today's Patient Queue + RAG Widget ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Today's Queue (full patient names) */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-slate-200">Today's Patient Queue</h2>
            </div>
            <span className="text-[11px] font-mono bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-slate-400">
              {todayCount} scheduled
            </span>
          </div>

          <div className="space-y-2.5">
            {todayAppointments.length === 0 ? (
              <div className="py-10 text-center">
                <Calendar className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                <p className="text-xs text-slate-500">No appointments scheduled for today.</p>
                <p className="text-[11px] text-slate-600 mt-1">Check your full roster for upcoming visits.</p>
              </div>
            ) : (
              todayAppointments.slice(0, 6).map((appt, idx) => {
                const status = statusConfig[appt.status] || { label: appt.status, cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' }
                return (
                  <motion.div
                    key={appt.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.06 }}
                    className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-3 text-xs hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                        <User className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-100">{appt.patient_name}</p>
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {new Date(appt.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          {' '}• {appt.appointment_type}
                          {appt.patient_phone && <span className="text-slate-600"> • {appt.patient_phone}</span>}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase border ${status.cls}`}>
                        {status.label}
                      </span>
                      <Link href="/doctor/appointments" className="text-slate-600 hover:text-indigo-400 transition-colors">
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </motion.div>
                )
              })
            )}
            {todayAppointments.length > 6 && (
              <Link href="/doctor/appointments" className="flex items-center justify-center gap-1 text-xs text-indigo-400 hover:underline py-1">
                View {todayAppointments.length - 6} more appointments <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </div>

        {/* Right Column: Quick Actions */}
        <div className="space-y-4">
          {/* Clinical RAG Widget */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col">
            <div>
              <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 mb-3">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-slate-100">Clinical RAG Summary</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Synthesize past consultation notes for any patient before entering the consultation room.
              </p>
            </div>
            <Link
              href="/doctor/appointments"
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-teal-300 border border-slate-700 text-xs font-medium inline-flex items-center justify-center gap-2 transition-colors"
            >
              <FileText className="w-4 h-4 text-teal-400" />
              Open Consultation Suite
            </Link>
          </div>

          {/* Patient Roster Quick Link */}
          <Link
            href="/doctor/appointments"
            className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-indigo-500/40 transition-all group flex flex-col gap-3"
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">Patient Roster</h3>
              <p className="text-xs text-slate-400 mt-1">View all patients, medical history, and add consultation notes.</p>
            </div>
            <div className="flex items-center gap-1 text-xs text-indigo-400">
              Open roster <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>
        </div>
      </div>

      {/* ── All-Time Stats Summary ── */}
      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-4 h-4 text-teal-400" />
          <h2 className="text-sm font-semibold text-slate-200">All-Time Practice Statistics</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Appointments', value: allAppointments.length, color: 'text-slate-100' },
            { label: 'Completed', value: completed, color: 'text-emerald-400' },
            { label: 'Upcoming', value: upcoming, color: 'text-amber-400' },
            { label: 'Today', value: todayCount, color: 'text-indigo-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="text-center p-3 rounded-xl bg-slate-950 border border-slate-800">
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
              <p className="text-[11px] text-slate-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
