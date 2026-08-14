'use client'

import React, { useEffect, useState } from 'react'
import { Calendar, Search, Loader2 } from 'lucide-react'
import apiClient from '@/lib/api/client'

export default function AdminAppointmentsPage() {
  const [appointments, setAppointments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<string>('all')

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get('/medai/appointments')
      setAppointments(res.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch appointments', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAppointments()
  }, [])

  const filtered = appointments.filter(
    (a) => filterStatus === 'all' || a.status.toLowerCase() === filterStatus.toLowerCase()
  )

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Master Appointment Matrix</h1>
          <p className="text-xs text-slate-400 mt-1">Cross-clinic scheduling overview and admin overrides.</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        {['all', 'scheduled', 'confirmed', 'completed', 'cancelled'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
              filterStatus === st
                ? 'bg-teal-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5">Scheduled Date & Time</th>
              <th className="p-3.5">Patient ID</th>
              <th className="p-3.5">Doctor ID</th>
              <th className="p-3.5">Type</th>
              <th className="p-3.5">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No appointments match the filter criteria.
                </td>
              </tr>
            ) : (
              filtered.map((appt) => (
                <tr key={appt.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 font-mono text-slate-100">
                    {new Date(appt.scheduled_at).toLocaleString()}
                  </td>
                  <td className="p-3.5 font-mono text-slate-400">{appt.patient_id?.slice(0, 8)}...</td>
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
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
