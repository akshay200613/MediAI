'use client'

import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users,
  UserCheck,
  Calendar,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Activity,
  Eye,
  Trash2,
  X,
  FileText,
  Phone,
  Mail,
  Stethoscope,
  Briefcase,
  DollarSign,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<any>(null)
  const [pendingDoctors, setPendingDoctors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [selectedDoctor, setSelectedDoctor] = useState<any | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [statsResult, pendingResult] = await Promise.allSettled([
        apiClient.get('/medai/admin/stats'),
        apiClient.get('/medai/admin/doctors/pending'),
      ])

      if (statsResult.status === 'fulfilled') {
        setStats(statsResult.value.data?.data)
      } else {
        console.error('Failed to load admin stats:', statsResult.reason)
      }

      if (pendingResult.status === 'fulfilled') {
        setPendingDoctors(pendingResult.value.data?.data || [])
      } else {
        console.error('Failed to load pending doctors:', pendingResult.reason)
      }
    } catch (err: any) {
      console.error('Failed to load admin dashboard data', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Subscribe to real-time tab-isolated WebSocket events
  useAppointmentSocket((event) => {
    setActionMessage(`Real-time update: ${event.event.replace('_', ' ').toUpperCase()}`)
    fetchData()
  })

  const handleApproveDoctor = async (doctorId: string, name: string) => {
    try {
      await apiClient.post(`/medai/admin/doctors/${doctorId}/approve`)
      setActionMessage(`Approved Dr. ${name} successfully!`)
      setSelectedDoctor(null)
      fetchData()
    } catch (err: any) {
      setActionMessage(`Failed to approve: ${err.message || err}`)
    }
  }

  const handleDeleteDoctor = async (doctorId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete Dr. ${name}? This will revoke their platform access and remove them from the system.`)) {
      return
    }
    try {
      await apiClient.delete(`/medai/admin/doctors/${doctorId}`)
      setActionMessage(`Deleted Dr. ${name}`)
      setSelectedDoctor(null)
      fetchData()
    } catch (err: any) {
      setActionMessage(`Failed to delete: ${err.message || err}`)
    }
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-7xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">MediAI Admin Console</h1>
          <p className="text-xs text-slate-400 mt-1">
            System administration, doctor verification queue, and platform analytics.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
          <ShieldCheck className="w-4 h-4" />
          <span>System RBAC: Active</span>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Doctors</span>
            <UserCheck className="w-5 h-5 text-teal-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 mt-2">{stats?.total_doctors ?? '-'}</p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Patients</span>
            <Users className="w-5 h-5 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 mt-2">{stats?.total_patients ?? '-'}</p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Appointments</span>
            <Calendar className="w-5 h-5 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 mt-2">{stats?.total_appointments ?? '-'}</p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Pending Verifications</span>
            <Clock className="w-5 h-5 text-rose-400 animate-pulse" />
          </div>
          <p className="text-2xl font-bold text-rose-400 mt-2">{stats?.pending_doctor_approvals ?? 0}</p>
        </div>
      </div>

      {/* Two Column Layout: Pending Approvals & Doctor Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Approvals Widget */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-semibold text-slate-200">Pending Doctor Sign-ups</h2>
            </div>
            <span className="text-[11px] font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-400">
              {pendingDoctors.length} Pending
            </span>
          </div>

          <div className="space-y-3">
            {pendingDoctors.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">No pending doctor registrations.</p>
            ) : (
              pendingDoctors.map((doc) => (
                <div
                  key={doc.doctor_id}
                  className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold text-slate-100 truncate">{doc.full_name}</h4>
                    <p className="text-[11px] text-slate-400 truncate">{doc.email} • {doc.specialty}</p>
                    <p className="text-[10px] font-mono text-slate-500 mt-0.5">License: {doc.license_number}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setSelectedDoctor(doc)}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-xs transition-colors inline-flex items-center gap-1 border border-slate-700"
                      title="View Doctor Details"
                    >
                      <Eye className="w-3.5 h-3.5" /> Details
                    </button>
                    <button
                      onClick={() => handleApproveDoctor(doc.doctor_id, doc.full_name)}
                      className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs transition-colors shadow-md"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleDeleteDoctor(doc.doctor_id, doc.full_name)}
                      className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 transition-colors"
                      title="Delete / Reject Signup"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Doctor Appointment Breakdown Widget */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-400" />
              <h2 className="text-sm font-semibold text-slate-200">Doctor Appointment Volume</h2>
            </div>
          </div>

          <div className="divide-y divide-slate-800/80">
            {stats?.doctor_breakdown?.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">No doctors registered yet.</p>
            ) : (
              stats?.doctor_breakdown?.map((item: any) => (
                <div key={item.doctor_id} className="py-3 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-medium text-slate-200">{item.doctor_name}</span>
                    <span className="text-slate-500 text-[11px] ml-2">({item.specialty})</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-teal-300 font-semibold">{item.appointment_count} appointments</span>
                    <span
                      className={`w-2 h-2 rounded-full ${
                        item.is_available ? 'bg-emerald-400' : 'bg-rose-400'
                      }`}
                      title={item.is_available ? 'Available' : 'Unavailable'}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── Doctor Details Modal ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedDoctor && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative"
            >
              <button
                onClick={() => setSelectedDoctor(null)}
                className="absolute right-4 top-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0">
                  <Stethoscope className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100">{selectedDoctor.full_name}</h3>
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-300 border border-teal-500/20 mt-1">
                    {selectedDoctor.specialty}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Contact Email</span>
                  <p className="text-slate-200 font-medium truncate flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    {selectedDoctor.email}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Phone Number</span>
                  <p className="text-slate-200 font-medium flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    {selectedDoctor.phone || 'Not provided'}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">License Number</span>
                  <p className="text-teal-400 font-mono font-semibold flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                    {selectedDoctor.license_number}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Experience & Fee</span>
                  <p className="text-slate-200 font-medium">
                    {selectedDoctor.years_of_experience || 0} yrs exp. • ₹{selectedDoctor.consultation_fee || 0}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Available Days</span>
                  <p className="text-slate-200 font-medium">{selectedDoctor.available_days || 'Mon-Fri'}</p>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Working Hours</span>
                  <p className="text-slate-200 font-medium">
                    {selectedDoctor.working_hours_start || '09:00'} - {selectedDoctor.working_hours_end || '17:00'}
                  </p>
                </div>
              </div>

              {selectedDoctor.bio && (
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Professional Bio</span>
                  <p className="text-slate-300 text-[11px] leading-relaxed">{selectedDoctor.bio}</p>
                </div>
              )}

              {/* Action Buttons in Modal */}
              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  onClick={() => handleDeleteDoctor(selectedDoctor.doctor_id, selectedDoctor.full_name)}
                  className="px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-colors inline-flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete Doctor
                </button>
                <button
                  onClick={() => handleApproveDoctor(selectedDoctor.doctor_id, selectedDoctor.full_name)}
                  className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold transition-all shadow-lg shadow-teal-900/30 inline-flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-4 h-4" /> Approve Registration
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
