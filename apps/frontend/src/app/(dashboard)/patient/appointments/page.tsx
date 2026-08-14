'use client'

import React, { useEffect, useState } from 'react'
import { Calendar, Clock, AlertTriangle, CheckCircle2, Loader2, XCircle } from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

export default function PatientAppointmentsPage() {
  const [appointments, setAppointments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<string | null>(null)

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

  // Subscribe to real-time tab-isolated WebSocket events
  useAppointmentSocket((event) => {
    setNotice(`Real-time update: ${event.event.replace('_', ' ').toUpperCase()}`)
    fetchAppointments()
  })

  const handleCancel = async (appt: any) => {
    const scheduledTime = new Date(appt.scheduled_at).getTime()
    const nowTime = new Date().getTime()
    const diffHours = (scheduledTime - nowTime) / (1000 * 60 * 60)

    // 2-hour cutoff rule enforcement
    if (diffHours < 2) {
      alert('Cancellation Cutoff Rule: Appointments cannot be cancelled less than 2 hours before the scheduled time.')
      return
    }

    if (!confirm('Are you sure you want to cancel this appointment?')) return

    try {
      await apiClient.post(`/medai/appointments/${appt.id}/cancel`)
      setNotice('Appointment cancelled successfully.')
      fetchAppointments()
    } catch (err: any) {
      setNotice(`Failed to cancel: ${err.message}`)
    }
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-4xl">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">My Appointments History</h1>
        <p className="text-xs text-slate-400 mt-1">Review upcoming consultations, past medical visits, and status history.</p>
      </div>

      {notice && (
        <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center justify-between">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5">Scheduled Date & Time</th>
              <th className="p-3.5">Doctor ID</th>
              <th className="p-3.5">Type</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : appointments.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No appointment history found.
                </td>
              </tr>
            ) : (
              appointments.map((appt) => (
                <tr key={appt.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 font-mono text-slate-100">
                    {new Date(appt.scheduled_at).toLocaleString()}
                  </td>
                  <td className="p-3.5 font-mono text-slate-400">{appt.doctor_id?.slice(0, 8)}...</td>
                  <td className="p-3.5 capitalize">{appt.appointment_type}</td>
                  <td className="p-3.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${
                        appt.status === 'completed'
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                          : appt.status === 'cancelled'
                          ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                          : 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                      }`}
                    >
                      {appt.status}
                    </span>
                  </td>
                  <td className="p-3.5">
                    {appt.status !== 'completed' && appt.status !== 'cancelled' && (
                      <button
                        onClick={() => handleCancel(appt)}
                        className="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-[11px] font-medium border border-rose-500/20 transition-colors"
                      >
                        Cancel Visit
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
