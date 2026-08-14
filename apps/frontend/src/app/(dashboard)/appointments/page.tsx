'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { Plus, Calendar, Clock, ChevronLeft, ChevronRight, XCircle, User } from 'lucide-react'
import { appointmentsApi } from '@/lib/api/appointments'
import { formatDateTime, getStatusBadgeClass } from '@/lib/utils'
import type { Appointment } from '@/types'
import toast from 'react-hot-toast'

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-primary-500/20 border-primary-500/30',
  confirmed: 'bg-emerald-500/20 border-emerald-500/30',
  in_progress: 'bg-amber-500/20 border-amber-500/30',
  completed: 'bg-slate-500/20 border-slate-500/30',
  cancelled: 'bg-red-500/20 border-red-500/30',
}

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<'all' | 'upcoming'>('upcoming')
  const [loading, setLoading] = useState(true)
  const pageSize = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await appointmentsApi.list(page, pageSize, filter === 'upcoming')
      setAppointments(res.data)
      setTotal(res.total)
    } catch { toast.error('Failed to load appointments') }
    finally { setLoading(false) }
  }, [page, filter])

  useEffect(() => { load() }, [load])

  const handleCancel = async (id: string) => {
    if (!confirm('Cancel this appointment?')) return
    try { await appointmentsApi.cancel(id); toast.success('Appointment cancelled'); load() }
    catch { toast.error('Failed to cancel') }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="text-2xl font-bold text-white">Appointments</h1>
          <p className="text-slate-400 mt-1">{total} appointments</p>
        </div>
        <Link href="/patient/book" className="btn-primary"><Plus className="w-4 h-4" /> Book Appointment</Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 p-1 bg-surface-700/60 rounded-xl w-fit">
        {(['upcoming', 'all'] as const).map(f => (
          <button key={f} onClick={() => { setFilter(f); setPage(1) }}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${filter === f ? 'bg-primary-500 text-white shadow-glow' : 'text-slate-400 hover:text-white'}`}>
            {f === 'upcoming' ? 'Upcoming' : 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="shimmer h-24 rounded-2xl" />)}</div>
      ) : appointments.length === 0 ? (
        <div className="glass-card flex flex-col items-center justify-center py-20 text-slate-500">
          <Calendar className="w-12 h-12 mb-3 opacity-30" />
          <p className="font-medium">No appointments found</p>
          <Link href="/patient/book" className="btn-primary mt-4"><Plus className="w-4 h-4" /> Book Appointment</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {appointments.map(appt => (
            <div key={appt.id} className={`glass-card p-5 border ${STATUS_COLORS[appt.status] || 'border-white/5'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary-500/20 flex-shrink-0 mt-0.5">
                    <Calendar className="w-5 h-5 text-primary-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-white capitalize">{appt.appointment_type} Appointment</p>
                      <span className={getStatusBadgeClass(appt.status)}>{appt.status}</span>
                    </div>
                    {appt.reason && <p className="text-slate-400 text-sm mt-0.5">{appt.reason}</p>}
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{formatDateTime(appt.scheduled_at)}</span>
                      <span className="flex items-center gap-1"><User className="w-3 h-3" />{appt.duration_minutes} min</span>
                    </div>
                  </div>
                </div>
                {['scheduled', 'confirmed'].includes(appt.status) && (
                  <button onClick={() => handleCancel(appt.id)} className="btn-danger flex-shrink-0">
                    <XCircle className="w-3.5 h-3.5" /> Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {Math.ceil(total / pageSize) > 1 && (
        <div className="flex items-center justify-center gap-4">
          <button onClick={() => setPage(p => p-1)} disabled={page === 1} className="btn-secondary py-2 px-3 disabled:opacity-40"><ChevronLeft className="w-4 h-4" /></button>
          <span className="text-sm text-slate-400">{page} of {Math.ceil(total / pageSize)}</span>
          <button onClick={() => setPage(p => p+1)} disabled={page >= Math.ceil(total/pageSize)} className="btn-secondary py-2 px-3 disabled:opacity-40"><ChevronRight className="w-4 h-4" /></button>
        </div>
      )}
    </div>
  )
}
