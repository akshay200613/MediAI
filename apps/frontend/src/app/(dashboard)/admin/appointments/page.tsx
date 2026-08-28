'use client'

import React, { useEffect, useState } from 'react'
import {
  Calendar,
  Search,
  Loader2,
  XCircle,
  ArrowUpDown,
  Filter,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  User,
  CheckSquare,
  Square,
  FileText,
  Pill,
  Sparkles,
  Stethoscope,
  Activity,
  X,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

export default function AdminAppointmentsPage() {
  const [appointments, setAppointments] = useState<any[]>([])
  const [doctors, setDoctors] = useState<any[]>([])
  const [patients, setPatients] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Selection & Bulk Action State
  const [selectedApptIds, setSelectedApptIds] = useState<string[]>([])
  const [bulkCancelling, setBulkCancelling] = useState(false)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [selectedNotesAppt, setSelectedNotesAppt] = useState<any | null>(null)

  // Filtering & Sorting State
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>('all')
  const [selectedPatientId, setSelectedPatientId] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'doctor_asc' | 'doctor_desc' | 'patient_asc'>('date_desc')

  const fetchData = async () => {
    try {
      setLoading(true)
      const [apptsRes, docsRes, patsRes] = await Promise.all([
        apiClient.get('/medai/appointments?page_size=100'),
        apiClient.get('/medai/doctors?page_size=100'),
        apiClient.get('/medai/patients?page_size=100'),
      ])
      setAppointments(apptsRes.data?.data || [])
      setDoctors(docsRes.data?.data || [])
      setPatients(patsRes.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch admin data', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Real-time updates via WebSocket
  useAppointmentSocket(() => {
    fetchData()
  })

  // Map IDs to Doctor / Patient models for fast lookup
  const doctorMap = new Map<string, any>(doctors.map((d) => [d.id, d]))
  const patientMap = new Map<string, any>(patients.map((p) => [p.id, p]))

  // Handle Single Admin Cancel
  const handleAdminCancel = async (apptId: string) => {
    if (!confirm('Are you sure you want to cancel this appointment as Admin?')) return

    try {
      setCancellingId(apptId)
      setNotice(null)
      await apiClient.post(`/medai/appointments/${apptId}/cancel`)
      setNotice({ type: 'success', message: 'Appointment successfully cancelled.' })
      setSelectedApptIds((prev) => prev.filter((id) => id !== apptId))
      fetchData()
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Failed to cancel appointment'
      setNotice({ type: 'error', message: `Cancel error: ${errMsg}` })
    } finally {
      setCancellingId(null)
    }
  }

  // Handle Bulk Cancel
  const handleBulkCancel = async () => {
    if (selectedApptIds.length === 0) return
    if (!confirm(`Are you sure you want to cancel ${selectedApptIds.length} selected appointment(s)?`)) return

    try {
      setBulkCancelling(true)
      setNotice(null)
      await Promise.all(
        selectedApptIds.map((id) => apiClient.post(`/medai/appointments/${id}/cancel`))
      )
      setNotice({
        type: 'success',
        message: `Successfully cancelled ${selectedApptIds.length} selected appointment(s).`,
      })
      setSelectedApptIds([])
      fetchData()
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Failed to cancel selected appointments'
      setNotice({ type: 'error', message: `Bulk cancel error: ${errMsg}` })
    } finally {
      setBulkCancelling(false)
    }
  }

  // Filter & Sort Logic
  const filteredAndSorted = appointments
    .filter((a) => {
      // Status filter
      if (filterStatus !== 'all' && a.status.toLowerCase() !== filterStatus.toLowerCase()) {
        return false
      }
      // Doctor filter
      if (selectedDoctorId !== 'all' && a.doctor_id !== selectedDoctorId) {
        return false
      }
      // Patient filter
      if (selectedPatientId !== 'all' && a.patient_id !== selectedPatientId) {
        return false
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const doc = doctorMap.get(a.doctor_id)
        const pat = patientMap.get(a.patient_id)
        const docName = doc ? `${doc.first_name} ${doc.last_name}`.toLowerCase() : ''
        const patName = pat ? `${pat.full_name || `${pat.first_name} ${pat.last_name}`}`.toLowerCase() : ''
        const spec = doc?.specialty?.toLowerCase() || ''
        const patId = (a.patient_id || '').toLowerCase()
        const apptType = (a.appointment_type || '').toLowerCase()
        const reason = (a.reason || '').toLowerCase()

        return (
          docName.includes(q) ||
          patName.includes(q) ||
          spec.includes(q) ||
          patId.includes(q) ||
          apptType.includes(q) ||
          reason.includes(q)
        )
      }
      return true
    })
    .sort((a, b) => {
      if (sortBy === 'date_desc') {
        return new Date(b.scheduled_at).getTime() - new Date(a.scheduled_at).getTime()
      }
      if (sortBy === 'date_asc') {
        return new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime()
      }
      if (sortBy === 'doctor_asc' || sortBy === 'doctor_desc') {
        const docA = doctorMap.get(a.doctor_id)
        const nameA = docA ? `${docA.last_name} ${docA.first_name}` : a.doctor_id
        const docB = doctorMap.get(b.doctor_id)
        const nameB = docB ? `${docB.last_name} ${docB.first_name}` : b.doctor_id
        const comp = nameA.localeCompare(nameB)
        return sortBy === 'doctor_asc' ? comp : -comp
      }
      if (sortBy === 'patient_asc') {
        const patA = patientMap.get(a.patient_id)
        const nameA = patA ? patA.full_name || patA.last_name : a.patient_id
        const patB = patientMap.get(b.patient_id)
        const nameB = patB ? patB.full_name || patB.last_name : b.patient_id
        return nameA.localeCompare(nameB)
      }
      return 0
    })

  // Cancellable appointments among visible list
  const visibleCancellable = filteredAndSorted.filter(
    (a) => a.status.toLowerCase() !== 'cancelled' && a.status.toLowerCase() !== 'completed'
  )

  const isAllSelected =
    visibleCancellable.length > 0 &&
    visibleCancellable.every((a) => selectedApptIds.includes(a.id))

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedApptIds([])
    } else {
      setSelectedApptIds(visibleCancellable.map((a) => a.id))
    }
  }

  const toggleSelectAppt = (id: string) => {
    setSelectedApptIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Master Appointment Matrix</h1>
          <p className="text-xs text-slate-400 mt-1">Cross-clinic scheduling overview, patient/doctor filtering, sorting, and bulk cancellation overrides.</p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center gap-2 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-teal-400' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between gap-2 ${
            notice.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {notice.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{notice.message}</span>
          </div>
          <button onClick={() => setNotice(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Bulk Action Bar (when rows are selected) */}
      {selectedApptIds.length > 0 && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-2 text-rose-300 text-xs font-medium">
            <CheckSquare className="w-4 h-4 text-rose-400 shrink-0" />
            <span>Selected {selectedApptIds.length} appointment(s) for bulk cancellation</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedApptIds([])}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-medium"
            >
              Clear Selection
            </button>
            <button
              onClick={handleBulkCancel}
              disabled={bulkCancelling}
              className="px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs inline-flex items-center gap-1.5 shadow-lg shadow-rose-900/30 transition-colors disabled:opacity-50"
            >
              {bulkCancelling ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <XCircle className="w-3.5 h-3.5" />
              )}
              Cancel Selected ({selectedApptIds.length})
            </button>
          </div>
        </div>
      )}

      {/* Controls Bar: Search, Patient Filter, Doctor Filter, Sorting */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search patient, doctor, reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
          />
        </div>

        {/* Patient Filter Dropdown */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
          <User className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-xs text-slate-400 font-medium shrink-0">Patient:</span>
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="bg-transparent text-xs text-slate-200 focus:outline-none w-full cursor-pointer"
          >
            <option value="all" className="bg-slate-900 text-slate-200">All Patients ({patients.length})</option>
            {patients.map((pat) => (
              <option key={pat.id} value={pat.id} className="bg-slate-900 text-slate-200">
                {pat.full_name || `${pat.first_name || ''} ${pat.last_name || ''}`.trim() || pat.email || pat.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>

        {/* Doctor Filter Dropdown */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-xs text-slate-400 font-medium shrink-0">Doctor:</span>
          <select
            value={selectedDoctorId}
            onChange={(e) => setSelectedDoctorId(e.target.value)}
            className="bg-transparent text-xs text-slate-200 focus:outline-none w-full cursor-pointer"
          >
            <option value="all" className="bg-slate-900 text-slate-200">All Doctors ({doctors.length})</option>
            {doctors.map((doc) => (
              <option key={doc.id} value={doc.id} className="bg-slate-900 text-slate-200">
                Dr. {doc.first_name} {doc.last_name} ({doc.specialty})
              </option>
            ))}
          </select>
        </div>

        {/* Sort By Dropdown */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
          <ArrowUpDown className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="text-xs text-slate-400 font-medium shrink-0">Sort By:</span>
          <select
            value={sortBy}
            onChange={(e: any) => setSortBy(e.target.value)}
            className="bg-transparent text-xs text-slate-200 focus:outline-none w-full cursor-pointer font-medium"
          >
            <option value="date_desc" className="bg-slate-900 text-slate-200">Date: Newest First</option>
            <option value="date_asc" className="bg-slate-900 text-slate-200">Date: Oldest First</option>
            <option value="doctor_asc" className="bg-slate-900 text-slate-200">Doctor: A to Z</option>
            <option value="doctor_desc" className="bg-slate-900 text-slate-200">Doctor: Z to A</option>
            <option value="patient_asc" className="bg-slate-900 text-slate-200">Patient Name: A to Z</option>
          </select>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {['all', 'scheduled', 'confirmed', 'completed', 'cancelled', 'incomplete'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
              filterStatus === st
                ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Master Appointments Table */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5 w-10 text-center">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  onChange={toggleSelectAll}
                  disabled={visibleCancellable.length === 0}
                  className="rounded border-slate-700 bg-slate-900 text-teal-500 focus:ring-0 cursor-pointer disabled:opacity-30"
                />
              </th>
              <th className="p-3.5">Scheduled Date & Time</th>
              <th className="p-3.5">Patient</th>
              <th className="p-3.5">Doctor</th>
              <th className="p-3.5">Type & Reason</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : filteredAndSorted.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  No appointments match the filter criteria.
                </td>
              </tr>
            ) : (
              filteredAndSorted.map((appt) => {
                const doc = doctorMap.get(appt.doctor_id)
                const pat = patientMap.get(appt.patient_id)
                const isCancelled = appt.status.toLowerCase() === 'cancelled'
                const isCompleted = appt.status.toLowerCase() === 'completed'
                const isIncomplete = appt.status.toLowerCase() === 'incomplete'
                const canCancel = !isCancelled && !isCompleted && !isIncomplete
                const isChecked = selectedApptIds.includes(appt.id)

                return (
                  <tr
                    key={appt.id}
                    className={`transition-colors ${
                      isChecked ? 'bg-slate-800/60' : 'hover:bg-slate-800/40'
                    }`}
                  >
                    <td className="p-3.5 text-center">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        disabled={!canCancel}
                        onChange={() => toggleSelectAppt(appt.id)}
                        className="rounded border-slate-700 bg-slate-900 text-teal-500 focus:ring-0 cursor-pointer disabled:opacity-30"
                      />
                    </td>
                    <td className="p-3.5 font-mono text-slate-100">
                      {new Date(appt.scheduled_at).toLocaleString()}
                    </td>
                    <td className="p-3.5">
                      {pat ? (
                        <div>
                          <p className="font-semibold text-slate-200">
                            {pat.full_name || `${pat.first_name || ''} ${pat.last_name || ''}`.trim() || 'Patient'}
                          </p>
                          <p className="text-[10px] text-slate-400">{pat.email || pat.phone || appt.patient_id.slice(0, 8)}</p>
                        </div>
                      ) : (
                        <span className="font-mono text-slate-400">{appt.patient_id?.slice(0, 8)}...</span>
                      )}
                    </td>
                    <td className="p-3.5">
                      {doc ? (
                        <div>
                          <p className="font-semibold text-slate-200">Dr. {doc.first_name} {doc.last_name}</p>
                          <p className="text-[10px] text-teal-400">{doc.specialty}</p>
                        </div>
                      ) : (
                        <span className="font-mono text-slate-500">{appt.doctor_id?.slice(0, 8)}...</span>
                      )}
                    </td>
                    <td className="p-3.5">
                      <p className="font-medium text-slate-200 capitalize">{appt.appointment_type}</p>
                      <p className="text-[11px] text-slate-400 truncate max-w-[200px]">{appt.reason || 'General Checkup'}</p>
                    </td>
                    <td className="p-3.5">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${
                          isCompleted
                            ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                            : isCancelled
                            ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                            : isIncomplete
                            ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                            : 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                        }`}
                      >
                        {isCompleted && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                        {appt.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-right space-x-2">
                      {isCompleted && appt.notes && (
                        <button
                          onClick={() => setSelectedNotesAppt({
                            ...appt,
                            doctor_name: doc ? `Dr. ${doc.first_name} ${doc.last_name}` : 'Specialist',
                            doctor_specialty: doc?.specialty || 'General',
                            patient_name: pat ? (pat.full_name || `${pat.first_name || ''} ${pat.last_name || ''}`.trim()) : 'Patient',
                            patient_email: pat?.email || pat?.phone || '',
                          })}
                          className="px-2.5 py-1 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 font-medium text-[11px] inline-flex items-center gap-1 transition-colors"
                        >
                          <FileText className="w-3.5 h-3.5 text-teal-400" />
                          View Notes
                        </button>
                      )}

                      {canCancel ? (
                        <button
                          onClick={() => handleAdminCancel(appt.id)}
                          disabled={cancellingId === appt.id || bulkCancelling}
                          className="px-3 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 font-medium text-[11px] inline-flex items-center gap-1 transition-colors disabled:opacity-50"
                        >
                          {cancellingId === appt.id ? (
                            <Loader2 className="w-3 h-3 animate-spin text-rose-400" />
                          ) : (
                            <XCircle className="w-3 h-3 text-rose-400" />
                          )}
                          Cancel
                        </button>
                      ) : !isCompleted ? (
                        <span className="text-[11px] text-slate-600 italic">No actions</span>
                      ) : null}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── Admin Consultation Notes View Modal ── */}
      {selectedNotesAppt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-5">
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                    <Stethoscope className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-100">Consultation Notes &amp; Clinical Summary</h3>
                    <p className="text-xs text-teal-400 font-medium">{selectedNotesAppt.doctor_name} ({selectedNotesAppt.doctor_specialty})</p>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400">
                  Patient: <span className="font-semibold text-slate-200">{selectedNotesAppt.patient_name}</span> ({selectedNotesAppt.patient_email})
                </p>
                <p className="text-[11px] text-slate-400 font-mono">
                  Scheduled: {new Date(selectedNotesAppt.scheduled_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => setSelectedNotesAppt(null)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-indigo-500/30 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-indigo-300">
                <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Indexed in RAG Knowledge Base</span>
              </div>
              <span className="text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded font-mono">
                Status: Completed
              </span>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-indigo-400" /> Recorded Notes &amp; Prescription
              </label>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-line">
                {selectedNotesAppt.notes}
              </div>
            </div>

            <div className="flex items-center justify-end border-t border-slate-800 pt-4">
              <button
                onClick={() => setSelectedNotesAppt(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
