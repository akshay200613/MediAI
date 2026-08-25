'use client'

import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Search,
  ShieldCheck,
  CheckCircle2,
  Trash2,
  Eye,
  Loader2,
  X,
  Stethoscope,
  Mail,
  Phone,
  FileText,
} from 'lucide-react'
import apiClient from '@/lib/api/client'

export default function AdminDoctorsPage() {
  const [doctors, setDoctors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedDoctor, setSelectedDoctor] = useState<any | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const fetchDoctors = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get('/medai/doctors')
      setDoctors(res.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch doctors', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDoctors()
  }, [])

  const handleDeleteDoctor = async (doctorId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete Dr. ${name}? This will revoke their platform access and remove them from the system.`)) {
      return
    }
    try {
      await apiClient.delete(`/medai/admin/doctors/${doctorId}`)
      setActionMessage(`Deleted Dr. ${name} successfully`)
      setSelectedDoctor(null)
      fetchDoctors()
    } catch (err: any) {
      setActionMessage(`Failed to delete: ${err.message || err}`)
    }
  }

  const filtered = doctors.filter(
    (d) =>
      d.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      d.specialty?.toLowerCase().includes(search.toLowerCase()) ||
      d.license_number?.toLowerCase().includes(search.toLowerCase())
  )

  const handleAddDoctor = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const payload = {
      first_name: formData.get('first_name'),
      last_name: formData.get('last_name'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      specialty: formData.get('specialty'),
      license_number: formData.get('license_number'),
      years_of_experience: Number(formData.get('years_of_experience')),
      consultation_fee: Number(formData.get('consultation_fee')),
      available_days: formData.get('available_days') || 'Mon,Tue,Wed,Thu,Fri',
      working_hours_start: formData.get('working_hours_start') || '09:00',
      working_hours_end: formData.get('working_hours_end') || '17:00',
      bio: formData.get('bio') || ''
    }

    try {
      await apiClient.post('/medai/doctors', payload)
      setActionMessage(`Added Dr. ${payload.first_name} ${payload.last_name} successfully`)
      setIsAddModalOpen(false)
      fetchDoctors()
    } catch (err: any) {
      setActionMessage(`Failed to add doctor: ${err.message || err}`)
    }
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-7xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Doctor Directory & Management</h1>
          <p className="text-xs text-slate-400 mt-1">Full physician directory, license verification, credentials, and delete management.</p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 text-sm font-semibold rounded-xl flex items-center gap-2 transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Doctor
        </button>
      </div>

      {actionMessage && (
        <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        <input
          type="text"
          placeholder="Search by doctor name, specialty, or license number..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
        />
      </div>

      {/* Doctors Table */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5">Doctor Name</th>
              <th className="p-3.5">Specialty</th>
              <th className="p-3.5">License Number</th>
              <th className="p-3.5">Fee (₹)</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No doctor records found.
                </td>
              </tr>
            ) : (
              filtered.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 font-semibold text-slate-100">{doc.full_name}</td>
                  <td className="p-3.5 text-teal-300">{doc.specialty}</td>
                  <td className="p-3.5 font-mono text-slate-400">{doc.license_number}</td>
                  <td className="p-3.5 font-mono">₹{doc.consultation_fee}</td>
                  <td className="p-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                        doc.is_available
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${doc.is_available ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                      {doc.is_available ? 'Available' : 'Unavailable'}
                    </span>
                  </td>
                  <td className="p-3.5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setSelectedDoctor(doc)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-xs transition-colors inline-flex items-center gap-1 border border-slate-700"
                        title="View Full Credentials"
                      >
                        <Eye className="w-3.5 h-3.5" /> Details
                      </button>
                      <button
                        onClick={() => handleDeleteDoctor(doc.id, doc.full_name)}
                        className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 transition-colors"
                        title="Delete Doctor"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
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

              {/* Modal Actions */}
              <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  onClick={() => handleDeleteDoctor(selectedDoctor.id, selectedDoctor.full_name)}
                  className="px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-colors inline-flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete Doctor
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── Add Doctor Modal ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {isAddModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl relative my-8"
            >
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="absolute right-4 top-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
                <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0">
                  <Plus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100">Add New Doctor</h3>
                  <p className="text-xs text-slate-400">Enter physician details to create a new profile.</p>
                </div>
              </div>

              <form onSubmit={handleAddDoctor} className="space-y-4 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">First Name</label>
                    <input required name="first_name" type="text" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Last Name</label>
                    <input required name="last_name" type="text" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Email</label>
                    <input required name="email" type="email" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Phone</label>
                    <input required name="phone" type="text" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Specialty</label>
                    <input required name="specialty" type="text" placeholder="e.g. Cardiology" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">License Number</label>
                    <input required name="license_number" type="text" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Years of Experience</label>
                    <input required name="years_of_experience" type="number" min="0" defaultValue="0" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Consultation Fee (₹)</label>
                    <input required name="consultation_fee" type="number" min="0" step="0.01" defaultValue="0" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Available Days</label>
                    <input name="available_days" type="text" placeholder="Mon,Tue,Wed..." defaultValue="Mon,Tue,Wed,Thu,Fri" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Start Time</label>
                    <input name="working_hours_start" type="time" defaultValue="09:00" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">End Time</label>
                    <input name="working_hours_end" type="time" defaultValue="17:00" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 text-xs font-medium">Bio (Optional)</label>
                  <textarea name="bio" rows={3} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs"></textarea>
                </div>

                <div className="pt-4 flex justify-end gap-3 border-t border-slate-800">
                  <button type="button" onClick={() => setIsAddModalOpen(false)} className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-sm font-semibold transition-colors">
                    Cancel
                  </button>
                  <button type="submit" className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-sm font-bold transition-colors">
                    Add Doctor
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
