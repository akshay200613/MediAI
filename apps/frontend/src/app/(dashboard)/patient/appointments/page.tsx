'use client'

import React, { useEffect, useState } from 'react'
import {
  Calendar,
  Clock,
  CheckCircle2,
  Loader2,
  XCircle,
  FileText,
  Pill,
  Sparkles,
  Stethoscope,
  Activity,
  X,
  User,
  ExternalLink,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

interface AppointmentModalData {
  appt: any
  docName: string
  docSpecialty: string
  dateFormatted: string
  timeFormatted: string
  observations: string
  prescription: string
}

export default function PatientAppointmentsPage() {
  const [appointments, setAppointments] = useState<any[]>([])
  const [doctorsMap, setDoctorsMap] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<string | null>(null)
  const [filterTab, setFilterTab] = useState<'all' | 'upcoming' | 'completed'>('all')
  const [selectedConsultation, setSelectedConsultation] = useState<AppointmentModalData | null>(null)

  const fetchAppointmentsAndDoctors = async () => {
    try {
      setLoading(true)

      // Fetch appointments and doctors independently with fallbacks so one failure doesn't block the other
      const [apptResult, docResult] = await Promise.allSettled([
        apiClient.get('/medai/appointments'),
        apiClient.get('/medai/doctors?page_size=100'),
      ])

      if (apptResult.status === 'fulfilled') {
        const apptData = apptResult.value.data
        const apptsList = Array.isArray(apptData?.data)
          ? apptData.data
          : Array.isArray(apptData)
          ? apptData
          : []
        setAppointments(apptsList)
      } else {
        console.error('Failed to fetch appointments:', apptResult.reason)
        setAppointments([])
      }

      if (docResult.status === 'fulfilled') {
        const docData = docResult.value.data
        const docsList = Array.isArray(docData?.data)
          ? docData.data
          : Array.isArray(docData)
          ? docData
          : []

        const dMap: Record<string, any> = {}
        docsList.forEach((d: any) => {
          if (d?.id) dMap[String(d.id)] = d
          if (d?.user_id) dMap[String(d.user_id)] = d
        })
        setDoctorsMap(dMap)
      } else {
        console.warn('Failed to fetch doctors list:', docResult.reason)
      }
    } catch (err) {
      console.error('Failed to fetch patient appointments or doctors', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAppointmentsAndDoctors()
  }, [])

  // Subscribe to real-time tab-isolated WebSocket events
  useAppointmentSocket((event) => {
    if (event.event === 'appointment_updated') {
      setNotice('Your consultation notes and visit status have been updated in real time!')
    } else {
      setNotice(`Real-time update: ${event.event.replace('_', ' ').toUpperCase()}`)
    }
    fetchAppointmentsAndDoctors()
  })

  const handleCancel = async (appt: any) => {
    const scheduledTime = new Date(appt.scheduled_at).getTime()
    const nowTime = new Date().getTime()
    const diffHours = (scheduledTime - nowTime) / (1000 * 60 * 60)

    // 2-hour cutoff rule enforcement (only for upcoming appointments scheduled less than 2 hours in advance)
    if (diffHours > 0 && diffHours < 2) {
      alert('Cancellation Cutoff Rule: Appointments cannot be cancelled less than 2 hours before the scheduled time.')
      return
    }

    if (!confirm('Are you sure you want to cancel this appointment?')) return

    try {
      await apiClient.post(`/medai/appointments/${appt.id}/cancel`)
      setNotice('Appointment cancelled successfully.')
      fetchAppointmentsAndDoctors()
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Failed to cancel appointment'
      setNotice(`Failed to cancel: ${errMsg}`)
    }
  }

  const parseNotes = (notes?: string) => {
    if (!notes) return { observations: 'No detailed clinical notes recorded.', prescription: '' }
    if (notes.includes('Consultation Notes:')) {
      const parts = notes.split('\nPrescription:')
      const obs = parts[0].replace('Consultation Notes:', '').trim()
      const rx = parts[1] ? parts[1].trim() : ''
      return { observations: obs || 'Clinical observations recorded.', prescription: rx }
    }
    return { observations: notes, prescription: '' }
  }

  const openConsultationModal = (appt: any) => {
    const doc = doctorsMap[appt.doctor_id] || doctorsMap[String(appt.doctor_id)]
    const docName = doc
      ? (doc.full_name || `${doc.first_name || ''} ${doc.last_name || ''}`.trim() || 'Dr. Specialist')
      : 'Dr. Specialist'
    const docSpecialty = doc?.specialty || 'General Practitioner'

    let dateFormatted = 'Scheduled'
    let timeFormatted = ''
    try {
      const d = new Date(appt.scheduled_at)
      if (!isNaN(d.getTime())) {
        dateFormatted = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
        timeFormatted = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      }
    } catch {
      dateFormatted = String(appt.scheduled_at || '')
    }

    const { observations, prescription } = parseNotes(appt.notes)

    setSelectedConsultation({
      appt,
      docName,
      docSpecialty,
      dateFormatted,
      timeFormatted,
      observations,
      prescription,
    })
  }

  const filteredAppointments = appointments.filter((appt) => {
    if (filterTab === 'upcoming') {
      return appt.status === 'scheduled' || appt.status === 'confirmed'
    }
    if (filterTab === 'completed') {
      return appt.status === 'completed'
    }
    return true
  })

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-5xl">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">My Appointments &amp; Medical Visits</h1>
        <p className="text-xs text-slate-400 mt-1">Review upcoming consultations, past completed visits, clinical notes, and active prescriptions.</p>
      </div>

      {notice && (
        <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
            <span>{notice}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        {(['all', 'upcoming', 'completed'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilterTab(tab)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
              filterTab === tab
                ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {tab === 'all' ? `All Visits (${appointments.length})` : tab === 'upcoming' ? `Upcoming (${appointments.filter(a => a.status === 'scheduled' || a.status === 'confirmed').length})` : `Completed Visits (${appointments.filter(a => a.status === 'completed').length})`}
          </button>
        ))}
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5">Scheduled Slot</th>
              <th className="p-3.5">Doctor &amp; Specialty</th>
              <th className="p-3.5">Consultation Type</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5 text-right">Actions &amp; Clinical Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : filteredAppointments.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No appointments found for this filter.
                </td>
              </tr>
            ) : (
              filteredAppointments.map((appt) => {
                const doc = doctorsMap[appt.doctor_id] || doctorsMap[String(appt.doctor_id)]
                const docName = doc
                  ? (doc.full_name || `${doc.first_name || ''} ${doc.last_name || ''}`.trim() || 'Dr. Specialist')
                  : 'Dr. Specialist'
                const docSpecialty = doc?.specialty || 'General Consultation'

                let dateFormatted = 'Scheduled'
                let timeFormatted = ''
                try {
                  const d = new Date(appt.scheduled_at)
                  if (!isNaN(d.getTime())) {
                    dateFormatted = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
                    timeFormatted = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                  }
                } catch {
                  dateFormatted = String(appt.scheduled_at || '')
                }

                const isCompleted = appt.status === 'completed'
                const hasNotes = !!appt.notes

                return (
                  <tr key={appt.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3.5 font-medium text-slate-100">
                      {dateFormatted}
                      {timeFormatted && (
                        <span className="ml-2 text-teal-400 font-mono text-xs bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20">
                          {timeFormatted}
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 font-medium text-slate-200">
                      <div className="font-semibold text-slate-100">{docName}</div>
                      <div className="text-[10px] text-teal-400 font-normal">
                        {docSpecialty}
                      </div>
                    </td>
                    <td className="p-3.5 capitalize">
                      <span className="font-medium text-slate-200">{appt.appointment_type}</span>
                      {appt.reason && (
                        <div className="text-[11px] text-slate-500 truncate max-w-xs italic">
                          {appt.reason}
                        </div>
                      )}
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${
                          isCompleted
                            ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                            : appt.status === 'cancelled'
                            ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                            : appt.status === 'incomplete'
                            ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                            : 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                        }`}
                      >
                        {isCompleted && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                        {appt.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-right space-x-2">
                      {isCompleted && (
                        <button
                          onClick={() => openConsultationModal(appt)}
                          className="px-3 py-1 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 text-[11px] font-medium border border-teal-500/30 transition-all inline-flex items-center gap-1.5 shadow-sm"
                        >
                          <FileText className="w-3.5 h-3.5 text-teal-400" />
                          View Notes &amp; Rx
                        </button>
                      )}

                      {!isCompleted && appt.status !== 'cancelled' && appt.status !== 'incomplete' && (
                        <button
                          onClick={() => handleCancel(appt)}
                          className="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-[11px] font-medium border border-rose-500/20 transition-colors"
                        >
                          Cancel Visit
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── Consultation Notes & Prescription Modal ── */}
      {selectedConsultation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                    <Stethoscope className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-100">Consultation &amp; Prescription Summary</h3>
                    <p className="text-xs text-teal-400 font-medium">{selectedConsultation.docName} • {selectedConsultation.docSpecialty}</p>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400 font-mono mt-1">
                  Visit Date: {selectedConsultation.dateFormatted} {selectedConsultation.timeFormatted ? `at ${selectedConsultation.timeFormatted}` : ''}
                </p>
              </div>
              <button
                onClick={() => setSelectedConsultation(null)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* RAG Verification Badge */}
            <div className="p-3 rounded-xl bg-slate-950 border border-indigo-500/30 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-indigo-300">
                <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Indexed in Medical Knowledge Pipeline for clinical tracking</span>
              </div>
              <span className="text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded font-mono">
                Verified Record
              </span>
            </div>

            {/* Clinical Observations */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-indigo-400" /> Clinical Observations &amp; Diagnosis
              </label>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-line">
                {selectedConsultation.observations}
              </div>
            </div>

            {/* Prescription & Medication */}
            {selectedConsultation.prescription ? (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Pill className="w-3.5 h-3.5 text-emerald-400" /> Prescription &amp; Medication Instructions
                </label>
                <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 text-xs text-emerald-200 leading-relaxed font-sans flex items-start gap-2.5">
                  <Pill className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div className="whitespace-pre-line">
                    {selectedConsultation.prescription}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-500 flex items-center gap-2">
                <Pill className="w-3.5 h-3.5 text-slate-600" />
                <span>No specific medication prescribed during this visit.</span>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-end border-t border-slate-800 pt-4">
              <button
                onClick={() => setSelectedConsultation(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
              >
                Close Summary
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
