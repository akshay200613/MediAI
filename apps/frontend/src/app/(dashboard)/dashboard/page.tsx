'use client'
import { useEffect, useState } from 'react'
import { Users, Stethoscope, Calendar, TrendingUp, ArrowRight, Clock, Activity } from 'lucide-react'
import Link from 'next/link'
import { patientsApi } from '@/lib/api/patients'
import { doctorsApi } from '@/lib/api/doctors'
import { appointmentsApi } from '@/lib/api/appointments'
import { formatDateTime, getStatusBadgeClass } from '@/lib/utils'
import type { Appointment } from '@/types'

interface Stats { patients: number; doctors: number; appointments: number; upcoming: number }

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({ patients: 0, doctors: 0, appointments: 0, upcoming: 0 })
  const [upcoming, setUpcoming] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [pRes, dRes, aRes, uRes] = await Promise.all([
          patientsApi.list(1, 1),
          doctorsApi.list(1, 1),
          appointmentsApi.list(1, 1),
          appointmentsApi.list(1, 5, true),
        ])
        setStats({
          patients: pRes.total,
          doctors: dRes.total,
          appointments: aRes.total,
          upcoming: uRes.total,
        })
        setUpcoming(uRes.data)
      } catch { /* silent */ }
      finally { setLoading(false) }
    }
    load()
  }, [])

  const statCards = [
    { label: 'Total Patients', value: stats.patients, icon: Users,      color: 'from-primary-500 to-primary-600', href: '/patients' },
    { label: 'Doctors',        value: stats.doctors,  icon: Stethoscope, color: 'from-accent-500 to-accent-600',   href: '/doctors' },
    { label: 'Appointments',   value: stats.appointments, icon: Calendar, color: 'from-violet-500 to-violet-600',  href: '/appointments' },
    { label: 'Upcoming Today', value: stats.upcoming, icon: Clock,       color: 'from-emerald-500 to-emerald-600', href: '/appointments?upcoming=true' },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">Welcome back to MedAI Clinic Management</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon: Icon, color, href }) => (
          <Link key={label} href={href}>
            <div className="stat-card group cursor-pointer hover:scale-[1.02] transition-transform duration-200">
              <div className={`flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex-shrink-0`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-slate-400 text-sm">{label}</p>
                {loading ? (
                  <div className="shimmer h-7 w-16 mt-1 rounded" />
                ) : (
                  <p className="text-2xl font-bold text-white">{value.toLocaleString()}</p>
                )}
              </div>
              <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors flex-shrink-0" />
            </div>
          </Link>
        ))}
      </div>

      {/* Quick actions + Upcoming */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick actions */}
        <div className="glass-card p-6">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary-400" /> Quick Actions
          </h2>
          <div className="space-y-2">
            {[
              { label: 'Register Patient', href: '/patients/new', color: 'text-primary-400' },
              { label: 'Add Doctor',       href: '/doctors/new',  color: 'text-accent-400' },
              { label: 'Book Appointment', href: '/appointments/new', color: 'text-violet-400' },
              { label: 'AI Consultation', href: '/ai-chat', color: 'text-emerald-400' },
            ].map(({ label, href, color }) => (
              <Link key={href} href={href}
                className="flex items-center justify-between px-4 py-3 rounded-xl bg-surface-600/40 hover:bg-surface-500/40 border border-white/5 hover:border-white/10 transition-all duration-200 group"
              >
                <span className={`text-sm font-medium ${color}`}>{label}</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-slate-300 group-hover:translate-x-0.5 transition-all" />
              </Link>
            ))}
          </div>
        </div>

        {/* Upcoming appointments */}
        <div className="glass-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-accent-400" /> Upcoming Appointments
            </h2>
            <Link href="/appointments" className="text-xs text-primary-400 hover:text-primary-300 transition-colors">View all →</Link>
          </div>
          {loading ? (
            <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="shimmer h-14 rounded-xl" />)}</div>
          ) : upcoming.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-slate-500">
              <Calendar className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-sm">No upcoming appointments</p>
            </div>
          ) : (
            <div className="space-y-2">
              {upcoming.map(appt => (
                <div key={appt.id} className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-600/40 border border-white/5">
                  <div className="w-2 h-2 rounded-full bg-primary-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate capitalize">{appt.appointment_type} Appointment</p>
                    <p className="text-xs text-slate-400">{formatDateTime(appt.scheduled_at)}</p>
                  </div>
                  <span className={getStatusBadgeClass(appt.status)}>{appt.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
