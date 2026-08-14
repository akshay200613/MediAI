'use client'

import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Calendar,
  User,
  Sparkles,
  FileText,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  Heart,
  Phone,
  Mail,
  Activity,
  ChevronDown,
  ChevronUp,
  Pill,
  History,
  X,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

interface PatientHistory {
  id: string
  appointment_type: string
  status: string
  scheduled_at: string
  reason?: string
  notes?: string
  ai_triage_summary?: string
}

interface PatientDetail {
  id: string
  full_name: string
  email?: string
  phone?: string
  date_of_birth?: string
  gender?: string
  blood_group?: string
  address?: string
  allergies?: string
  chronic_conditions?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
}

interface Appointment {
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

const statusConfig: Record<string, { label: string; cls: string }> = {
  scheduled: { label: 'Scheduled', cls: 'bg-teal-500/10 text-teal-300 border-teal-500/20' },
  confirmed: { label: 'Confirmed', cls: 'bg-blue-500/10 text-blue-300 border-blue-500/20' },
  in_progress: { label: 'In Progress', cls: 'bg-amber-500/10 text-amber-300 border-amber-500/20' },
  completed: { label: 'Completed', cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' },
  cancelled: { label: 'Cancelled', cls: 'bg-rose-500/10 text-rose-300 border-rose-500/20' },
  no_show: { label: 'No Show', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
}

function MedicalTag({ value, label, color }: { value?: string; label: string; color: string }) {
  if (!value) return null
  return (
    <div className={`px-2.5 py-1 rounded-lg border text-[11px] flex flex-col gap-0.5 ${color}`}>
      <span className="opacity-60">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export default function DoctorAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null)
  const [loading, setLoading] = useState(true)
  const [patientDetail, setPatientDetail] = useState<PatientDetail | null>(null)
  const [patientHistory, setPatientHistory] = useState<PatientHistory[]>([])
  const [loadingPatient, setLoadingPatient] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)

  // RAG Summary
  const [ragSummary, setRagSummary] = useState<string | null>(null)
  const [loadingSummary, setLoadingSummary] = useState(false)

  // Notes
  const [notesText, setNotesText] = useState('')
  const [prescriptionText, setPrescriptionText] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      // Use today's dashboard endpoint which has patient names
      const res = await apiClient.get('/medai/doctor-dashboard/today')
      const appts: Appointment[] = res.data?.data?.appointments || []
      setAppointments(appts)
      if (appts.length > 0 && !selectedAppt) {
        handleSelectAppt(appts[0])
      }
    } catch {
      // Fallback to general appointments list
      try {
        const res = await apiClient.get('/medai/appointments')
        const appts = (res.data?.data || []).map((a: any) => ({
          ...a,
          patient_name: `Patient #${a.patient_id?.slice(0, 8)}`,
        }))
        setAppointments(appts)
        if (appts.length > 0) handleSelectAppt(appts[0])
      } catch (err) {
        console.error('Failed to fetch appointments', err)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAppointments()
  }, [])

  // Live WebSocket Realtime Patient Queue updates
  useAppointmentSocket(() => {
    fetchAppointments()
  })

  const handleSelectAppt = async (appt: Appointment) => {
    setSelectedAppt(appt)
    setRagSummary(null)
    setSaveStatus(null)
    setNotesText(appt.notes || '')
    setPatientDetail(null)
    setPatientHistory([])
    setHistoryOpen(false)

    // Fetch patient detail + history
    if (appt.patient_id) {
      setLoadingPatient(true)
      try {
        const res = await apiClient.get(`/medai/doctor-dashboard/patients/${appt.patient_id}/history`)
        const d = res.data?.data
        if (d) {
          setPatientDetail(d.patient)
          setPatientHistory(d.appointment_history || [])
        }
      } catch {
        // ignore; patient detail is supplementary
      } finally {
        setLoadingPatient(false)
      }
    }
  }

  const handleGenerateRagSummary = async () => {
    if (!selectedAppt) return
    setLoadingSummary(true)
    setRagSummary(null)
    try {
      const res = await apiClient.post('/medai/rag/query', {
        query: `Summarize medical history and past consultation notes for patient ID ${selectedAppt.patient_id} named ${selectedAppt.patient_name}`,
        top_k: 5,
      })
      setRagSummary(res.data?.data?.answer || 'No previous medical records found for this patient.')
    } catch (err: any) {
      setRagSummary(`Failed to generate RAG summary: ${err.message || 'Check RAG API service.'}`)
    } finally {
      setLoadingSummary(false)
    }
  }

  const handleSaveNotes = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAppt || !notesText.trim()) return
    setSavingNotes(true)
    setSaveStatus(null)
    try {
      await apiClient.post(`/medai/appointments/${selectedAppt.id}/notes`, {
        notes: notesText,
        prescription: prescriptionText,
      })
      setSaveStatus('Consultation notes saved and indexed into RAG knowledge base!')
      await fetchAppointments()
      setSelectedAppt((prev) => prev ? { ...prev, status: 'completed', notes: notesText } : prev)
    } catch (err: any) {
      setSaveStatus(`Failed to save notes: ${err.message}`)
    } finally {
      setSavingNotes(false)
    }
  }

  return (
    <div className="p-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      <div className="border-b border-slate-800 pb-4 mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Patient Roster &amp; Consultation Suite</h1>
        <p className="text-xs text-slate-400 mt-1">
          Select a scheduled appointment to view patient information, medical history, and record clinical notes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left: Appointment List ── */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Today's Queue
            </h2>
            <span className="text-[11px] bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-slate-400 font-mono">
              {appointments.length} visits
            </span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin mx-auto text-indigo-400" />
            </div>
          ) : appointments.length === 0 ? (
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-center">
              <Calendar className="w-8 h-8 text-slate-700 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No appointments scheduled for today.</p>
            </div>
          ) : (
            appointments.map((appt) => {
              const isSelected = selectedAppt?.id === appt.id
              const status = statusConfig[appt.status] || { label: appt.status, cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' }
              return (
                <motion.div
                  key={appt.id}
                  whileHover={{ scale: 1.01 }}
                  onClick={() => handleSelectAppt(appt)}
                  className={`p-4 rounded-xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-slate-900 border-indigo-500/50 shadow-lg shadow-indigo-500/5'
                      : 'bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[11px] text-slate-400">
                      {new Date(appt.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${status.cls}`}>
                      {status.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                      <User className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-200">{appt.patient_name}</h4>
                      <p className="text-[11px] text-slate-400 capitalize">{appt.appointment_type}</p>
                    </div>
                  </div>
                </motion.div>
              )
            })
          )}
        </div>

        {/* ── Right: Clinical Workstation ── */}
        <div className="lg:col-span-8">
          {!selectedAppt ? (
            <div className="h-full flex items-center justify-center p-12 rounded-2xl bg-slate-900 border border-slate-800 text-slate-500 text-xs text-center">
              <div>
                <Calendar className="w-10 h-10 mx-auto mb-3 text-slate-700" />
                <p>Select an appointment from the queue to open the clinical workstation.</p>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {/* ── Patient Header Card ── */}
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                      <User className="w-6 h-6" />
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-slate-100">{selectedAppt.patient_name}</h2>
                      <p className="text-xs text-slate-400">
                        {new Date(selectedAppt.scheduled_at).toLocaleString()} • {selectedAppt.appointment_type}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleGenerateRagSummary}
                    disabled={loadingSummary}
                    className="px-3.5 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-lg shadow-teal-900/20 inline-flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    {loadingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    AI RAG Summary
                  </button>
                </div>

                {/* Medical tags */}
                {loadingPatient ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading patient info...
                  </div>
                ) : patientDetail ? (
                  <div className="space-y-3">
                    {/* Contact info */}
                    <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                      {patientDetail.phone && (
                        <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{patientDetail.phone}</span>
                      )}
                      {patientDetail.email && (
                        <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{patientDetail.email}</span>
                      )}
                      {patientDetail.date_of_birth && (
                        <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />
                          {new Date(patientDetail.date_of_birth).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                        </span>
                      )}
                    </div>

                    {/* Medical data tags */}
                    <div className="flex flex-wrap gap-2">
                      <MedicalTag value={patientDetail.blood_group} label="Blood Group" color="bg-rose-500/10 text-rose-300 border-rose-500/20" />
                      <MedicalTag value={patientDetail.gender} label="Gender" color="bg-slate-800 text-slate-300 border-slate-700" />
                      {patientDetail.allergies && (
                        <div className="px-2.5 py-1 rounded-lg border bg-amber-500/10 text-amber-300 border-amber-500/20 text-[11px] flex flex-col gap-0.5">
                          <span className="opacity-60">Allergies</span>
                          <span className="font-medium">{patientDetail.allergies}</span>
                        </div>
                      )}
                      {patientDetail.chronic_conditions && (
                        <div className="px-2.5 py-1 rounded-lg border bg-orange-500/10 text-orange-300 border-orange-500/20 text-[11px] flex flex-col gap-0.5">
                          <span className="opacity-60">Chronic Conditions</span>
                          <span className="font-medium">{patientDetail.chronic_conditions}</span>
                        </div>
                      )}
                    </div>

                    {/* Emergency contact */}
                    {patientDetail.emergency_contact_name && (
                      <p className="text-[11px] text-slate-500">
                        Emergency Contact: <span className="text-slate-400">{patientDetail.emergency_contact_name}</span>
                        {patientDetail.emergency_contact_phone && <span> — {patientDetail.emergency_contact_phone}</span>}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-600">Patient profile unavailable.</p>
                )}
              </div>

              {/* ── Appointment History Toggle ── */}
              {patientHistory.length > 0 && (
                <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden">
                  <button
                    onClick={() => setHistoryOpen(!historyOpen)}
                    className="w-full flex items-center justify-between p-4 text-xs font-semibold text-slate-200 hover:bg-slate-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <History className="w-4 h-4 text-indigo-400" />
                      Medical History ({patientHistory.length} visits)
                    </div>
                    {historyOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                  </button>
                  <AnimatePresence>
                    {historyOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="px-4 pb-4 space-y-2 border-t border-slate-800">
                          {patientHistory.map((h) => {
                            const st = statusConfig[h.status] || { label: h.status, cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' }
                            return (
                              <div key={h.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <span className="font-mono text-[11px] text-slate-400">
                                    {new Date(h.scheduled_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                                  </span>
                                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${st.cls}`}>
                                    {st.label}
                                  </span>
                                </div>
                                <p className="text-slate-300 font-medium capitalize">{h.appointment_type}</p>
                                {h.reason && <p className="text-slate-500">Reason: {h.reason}</p>}
                                {h.notes && (
                                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800 text-slate-400 leading-relaxed">
                                    {h.notes}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}

              {/* ── RAG Summary Box ── */}
              <AnimatePresence>
                {ragSummary && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
                    className="p-4 rounded-2xl bg-slate-900/90 border border-teal-500/40 text-xs text-slate-200 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-teal-400 font-semibold">
                        <Sparkles className="w-4 h-4" />
                        <span>AI RAG Clinical Synthesis</span>
                      </div>
                      <button onClick={() => setRagSummary(null)} className="text-slate-500 hover:text-slate-300">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-slate-300 leading-relaxed font-sans bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                      {ragSummary}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Consultation Notes Form ── */}
              <form onSubmit={handleSaveNotes} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2 text-slate-200">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold">Consultation &amp; Prescription Notes</h3>
                  </div>
                  <span className="text-[11px] text-slate-500">Auto-indexes into patient RAG pipeline</span>
                </div>

                {saveStatus && (
                  <div className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${saveStatus.startsWith('Failed') ? 'bg-rose-500/10 border-rose-500/20 text-rose-300' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'}`}>
                    {saveStatus.startsWith('Failed') ? <AlertCircle className="w-4 h-4 shrink-0" /> : <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />}
                    {saveStatus}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-slate-500" /> Clinical Observations &amp; Diagnosis
                  </label>
                  <textarea
                    rows={4}
                    value={notesText}
                    onChange={(e) => setNotesText(e.target.value)}
                    placeholder="Enter clinical observations, diagnostic findings, and treatment plan..."
                    className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 resize-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Pill className="w-3.5 h-3.5 text-slate-500" /> Prescription &amp; Medication Instructions
                  </label>
                  <input
                    type="text"
                    value={prescriptionText}
                    onChange={(e) => setPrescriptionText(e.target.value)}
                    placeholder="e.g. Amoxicillin 500mg — 1 tablet 3× daily for 7 days"
                    className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>

                <button
                  type="submit"
                  disabled={savingNotes || !notesText.trim()}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-900/20 inline-flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  {savingNotes ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Complete Visit &amp; Index Notes
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
