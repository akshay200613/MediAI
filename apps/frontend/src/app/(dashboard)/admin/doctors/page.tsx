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
  Edit2,
  Save,
  Bell,
  Clock,
  Calendar,
  AlertCircle,
  Key,
  EyeOff
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { doctorsApi } from '@/lib/api/doctors'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

const SPECIALTIES = [
  'General Practice', 'General Medicine', 'Cardiology', 'Dermatology', 'Endocrinology',
  'Gastroenterology', 'Neurology', 'Obstetrics & Gynecology', 'Oncology',
  'Ophthalmology', 'Orthopedics', 'Pediatrics', 'Psychiatry',
  'Pulmonology', 'Radiology', 'Surgery', 'Urology', 'ENT', 'Physiology',
]

export default function AdminDoctorsPage() {
  const [doctors, setDoctors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedDoctor, setSelectedDoctor] = useState<any | null>(null)
  const [editingDoctor, setEditingDoctor] = useState<any | null>(null)
  const [resetPwdDoctor, setResetPwdDoctor] = useState<any | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [pwResetRequestAlert, setPwResetRequestAlert] = useState<{ email: string; name: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)

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

  // Listen to real-time doctor password reset requests from WebSocket
  useAppointmentSocket((event) => {
    if (event.event === 'doctor_password_reset_requested') {
      const { email, full_name } = event.data || {}
      setPwResetRequestAlert({ email, name: full_name || email })
    }
  })

  const handleDeleteDoctor = async (doctorId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete Dr. ${name}? This will revoke their platform access and remove them from the system.`)) {
      return
    }
    try {
      await apiClient.delete(`/medai/admin/doctors/${doctorId}`)
      setActionMessage({ type: 'success', text: `Deleted Dr. ${name} successfully` })
      setSelectedDoctor(null)
      fetchDoctors()
    } catch (err: any) {
      setActionMessage({ type: 'error', text: `Failed to delete: ${err.message || err}` })
    }
  }

  const handleAdminResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resetPwdDoctor || !newPassword) return
    if (newPassword.length < 8) {
      setActionMessage({ type: 'error', text: 'Password must be at least 8 characters long.' })
      return
    }

    try {
      setSubmitting(true)
      await apiClient.post('/auth/admin-reset-password', {
        email: resetPwdDoctor.email,
        new_password: newPassword,
      })
      setActionMessage({
        type: 'success',
        text: `Password for Dr. ${resetPwdDoctor.full_name} (${resetPwdDoctor.email}) reset successfully. Notification sent to doctor.`,
      })
      setResetPwdDoctor(null)
      setNewPassword('')
      setPwResetRequestAlert(null)
    } catch (err: any) {
      setActionMessage({
        type: 'error',
        text: `Failed to reset password: ${err.response?.data?.detail || err.message}`,
      })
    } finally {
      setSubmitting(false)
    }
  }

  const filtered = doctors.filter(
    (d) =>
      d.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      d.specialty?.toLowerCase().includes(search.toLowerCase()) ||
      d.license_number?.toLowerCase().includes(search.toLowerCase()) ||
      d.email?.toLowerCase().includes(search.toLowerCase())
  )

  const handleAddDoctor = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setSubmitting(true)
    const formData = new FormData(e.currentTarget)
    
    let profileImageUrl: string | undefined = undefined
    const photoFile = formData.get('photo_file') as File | null
    if (photoFile && photoFile.size > 0) {
      try {
        const uploadRes = await doctorsApi.uploadImage(photoFile)
        profileImageUrl = uploadRes.url
      } catch (uploadErr) {
        console.error('Photo upload failed:', uploadErr)
      }
    }

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
      bio: formData.get('bio') || '',
      profile_image_url: profileImageUrl,
    }

    try {
      await apiClient.post('/medai/doctors', payload)
      setActionMessage({ type: 'success', text: `Added Dr. ${payload.first_name} ${payload.last_name} successfully.` })
      setIsAddModalOpen(false)
      fetchDoctors()
    } catch (err: any) {
      setActionMessage({ type: 'error', text: `Failed to add doctor: ${err.response?.data?.detail || err.message || err}` })
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdateDoctor = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editingDoctor) return
    setSubmitting(true)
    const formData = new FormData(e.currentTarget)

    let profileImageUrl: string | undefined = undefined
    const photoFile = formData.get('photo_file') as File | null
    if (photoFile && photoFile.size > 0) {
      try {
        const uploadRes = await doctorsApi.uploadImage(photoFile)
        profileImageUrl = uploadRes.url
      } catch (uploadErr) {
        console.error('Photo upload failed:', uploadErr)
      }
    }

    const payload: any = {
      first_name: formData.get('first_name'),
      last_name: formData.get('last_name'),
      phone: formData.get('phone'),
      specialty: formData.get('specialty'),
      years_of_experience: Number(formData.get('years_of_experience')),
      consultation_fee: Number(formData.get('consultation_fee')),
      available_days: formData.get('available_days'),
      working_hours_start: formData.get('working_hours_start'),
      working_hours_end: formData.get('working_hours_end'),
      is_available: formData.get('is_available') === 'true',
      bio: formData.get('bio'),
    }
    if (profileImageUrl) {
      payload.profile_image_url = profileImageUrl
    }

    try {
      await apiClient.patch(`/medai/doctors/${editingDoctor.id}`, payload)
      setActionMessage({
        type: 'success',
        text: `Successfully updated profile for Dr. ${payload.first_name} ${payload.last_name}. Real-time notification sent to doctor.`
      })
      setEditingDoctor(null)
      if (selectedDoctor && selectedDoctor.id === editingDoctor.id) {
        setSelectedDoctor(null)
      }
      fetchDoctors()
    } catch (err: any) {
      setActionMessage({ type: 'error', text: `Failed to update doctor: ${err.response?.data?.detail || err.message || err}` })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-7xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Doctor Directory & Credentials Management</h1>
          <p className="text-xs text-slate-400 mt-1">Full physician directory, license verification, credentials editing, and admin password reset controls.</p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 text-sm font-semibold rounded-xl flex items-center gap-2 transition-colors shadow-lg shadow-teal-500/10"
        >
          <Plus className="w-4 h-4" /> Add Doctor
        </button>
      </div>

      {/* Password Reset Request Alert Banner */}
      {pwResetRequestAlert && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between shadow-xl animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center shrink-0">
              <Key className="w-4 h-4 text-amber-400 animate-pulse" />
            </div>
            <div>
              <p className="font-bold text-amber-200">Doctor Password Reset Requested</p>
              <p className="text-[11px] text-amber-300/90 mt-0.5">
                Dr. {pwResetRequestAlert.name} ({pwResetRequestAlert.email}) has requested a password reset.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const target = doctors.find((d) => d.email === pwResetRequestAlert.email) || {
                  email: pwResetRequestAlert.email,
                  full_name: pwResetRequestAlert.name,
                }
                setResetPwdDoctor(target)
              }}
              className="px-3.5 py-1.5 bg-amber-500 text-slate-950 hover:bg-amber-400 font-bold text-xs rounded-xl transition-colors shadow-md"
            >
              Reset Password Now
            </button>
            <button onClick={() => setPwResetRequestAlert(null)} className="px-2.5 py-1.5 text-slate-400 hover:text-white text-xs">
              Dismiss
            </button>
          </div>
        </div>
      )}

      {actionMessage && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between gap-2 ${
            actionMessage.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
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
          placeholder="Search by doctor name, email, specialty, or license..."
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
              <th className="p-3.5">Email & Phone</th>
              <th className="p-3.5">Specialty</th>
              <th className="p-3.5">Available Schedule</th>
              <th className="p-3.5">Fee (₹)</th>
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
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  No doctor records found.
                </td>
              </tr>
            ) : (
              filtered.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 font-semibold text-slate-100 flex items-center gap-3">
                    {doc.profile_image_url ? (
                      <div className="w-8 h-8 rounded-full overflow-hidden shrink-0 border border-slate-700">
                        <img 
                          src={doc.profile_image_url.startsWith('http') ? doc.profile_image_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${doc.profile_image_url}`} 
                          alt={doc.full_name} 
                          className="object-cover w-full h-full" 
                        />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 shrink-0 border border-slate-700">
                        <Stethoscope className="w-4 h-4" />
                      </div>
                    )}
                    <span>{doc.full_name}</span>
                  </td>
                  <td className="p-3.5">
                    <p className="text-slate-200">{doc.email}</p>
                    <p className="text-[10px] text-slate-500">{doc.phone}</p>
                  </td>
                  <td className="p-3.5 text-teal-300 font-medium">{doc.specialty}</td>
                  <td className="p-3.5">
                    <span className="text-slate-300">{doc.available_days || 'Mon,Tue,Wed,Thu,Fri'}</span>
                    <span className="text-slate-500 block text-[10px]">{doc.working_hours_start || '09:00'} - {doc.working_hours_end || '17:00'}</span>
                  </td>
                  <td className="p-3.5 font-mono text-teal-300 font-semibold">₹{doc.consultation_fee}</td>
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
                    <button
                      onClick={() => setSelectedDoctor(doc)}
                      className="px-3 py-1.5 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold text-xs transition-colors inline-flex items-center gap-1.5 border border-teal-500/30 shadow-sm"
                      title="View Full Credentials & Actions"
                    >
                      <Eye className="w-3.5 h-3.5" /> Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Admin Reset Doctor Password Modal ─────────────────────────────────────── */}
      <AnimatePresence>
        {resetPwdDoctor && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl relative"
            >
              <button
                onClick={() => setResetPwdDoctor(null)}
                className="absolute right-4 top-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                  <Key className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100">Reset Doctor Password</h3>
                  <p className="text-xs text-slate-400">Set a new password for Dr. {resetPwdDoctor.full_name}.</p>
                </div>
              </div>

              <form onSubmit={handleAdminResetPassword} className="space-y-4 text-xs">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Target Doctor Account</span>
                  <p className="text-slate-200 font-semibold">{resetPwdDoctor.full_name}</p>
                  <p className="text-teal-400 font-mono">{resetPwdDoctor.email}</p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-medium">New Password</label>
                  <div className="relative">
                    <input
                      type={showPwd ? 'text' : 'password'}
                      required
                      minLength={8}
                      placeholder="At least 8 characters..."
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-200 focus:outline-none focus:border-amber-500/50 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd(!showPwd)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                    >
                      {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 flex items-center gap-2">
                  <Bell className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>Submitting will update the password in PostgreSQL and send a real-time notification alert to Dr. {resetPwdDoctor.full_name}.</span>
                </div>

                <div className="pt-3 flex justify-end gap-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setResetPwdDoctor(null)}
                    className="px-4 py-2 rounded-xl text-slate-400 hover:text-white font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold inline-flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Reset & Notify Doctor
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── Doctor Details Modal ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {selectedDoctor && !editingDoctor && !resetPwdDoctor && (
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
                {selectedDoctor.profile_image_url ? (
                  <div className="w-14 h-14 rounded-2xl overflow-hidden shrink-0 border border-teal-500/30">
                    <img 
                      src={selectedDoctor.profile_image_url.startsWith('http') ? selectedDoctor.profile_image_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${selectedDoctor.profile_image_url}`} 
                      alt={selectedDoctor.full_name} 
                      className="object-cover w-full h-full" 
                    />
                  </div>
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0">
                    <Stethoscope className="w-6 h-6" />
                  </div>
                )}
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
              <div className="pt-3 flex items-center justify-between border-t border-slate-800">
                <button
                  onClick={() => {
                    setEditingDoctor(selectedDoctor)
                  }}
                  className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition-colors inline-flex items-center gap-1.5"
                >
                  <Edit2 className="w-3.5 h-3.5" /> Edit Profile Details
                </button>
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

      {/* ── Edit Doctor Modal ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {editingDoctor && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl relative my-8"
            >
              <button
                onClick={() => setEditingDoctor(null)}
                className="absolute right-4 top-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
                <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0">
                  <Edit2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100">Edit Doctor Profile</h3>
                  <p className="text-xs text-slate-400">Modifying details will automatically notify Dr. {editingDoctor.full_name} in real time.</p>
                </div>
              </div>

              <form onSubmit={handleUpdateDoctor} className="space-y-4 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">First Name</label>
                    <input required name="first_name" type="text" defaultValue={editingDoctor.first_name} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Last Name</label>
                    <input required name="last_name" type="text" defaultValue={editingDoctor.last_name} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Phone Number</label>
                    <input required name="phone" type="text" defaultValue={editingDoctor.phone} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Specialty</label>
                    <input required name="specialty" list="admin-specialties" type="text" defaultValue={editingDoctor.specialty} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                    <datalist id="admin-specialties">
                      {SPECIALTIES.map(s => <option key={s} value={s} />)}
                    </datalist>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Years of Experience</label>
                    <input required name="years_of_experience" type="number" min="0" defaultValue={editingDoctor.years_of_experience || 0} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Consultation Fee (₹)</label>
                    <input required name="consultation_fee" type="number" min="0" step="0.01" defaultValue={editingDoctor.consultation_fee || 0} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Status</label>
                    <select name="is_available" defaultValue={editingDoctor.is_available ? 'true' : 'false'} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs">
                      <option value="true">Available</option>
                      <option value="false">Unavailable</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Available Days</label>
                    <input name="available_days" type="text" placeholder="e.g. Mon,Tue,Fri" defaultValue={editingDoctor.available_days || 'Mon,Tue,Wed,Thu,Fri'} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Working Hours Start</label>
                    <input name="working_hours_start" type="time" defaultValue={editingDoctor.working_hours_start || '09:00'} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-slate-300 text-xs font-medium">Working Hours End</label>
                    <input name="working_hours_end" type="time" defaultValue={editingDoctor.working_hours_end || '17:00'} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 text-xs font-medium">Bio</label>
                  <textarea name="bio" rows={3} defaultValue={editingDoctor.bio || ''} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50 text-xs"></textarea>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 text-xs font-medium">Profile Photo (Optional)</label>
                  <input name="photo_file" type="file" accept="image/*" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 text-xs cursor-pointer file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-teal-500/20 file:text-teal-300 hover:file:bg-teal-500/30" />
                </div>

                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-center gap-2">
                  <Bell className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>Saving changes will automatically push an instant notification alert to Dr. {editingDoctor.full_name}'s portal.</span>
                </div>

                <div className="pt-4 flex justify-end gap-3 border-t border-slate-800">
                  <button type="button" onClick={() => setEditingDoctor(null)} disabled={submitting} className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-sm font-semibold transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={submitting} className="px-5 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-sm font-bold inline-flex items-center gap-2 transition-colors disabled:opacity-50">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Changes & Notify Doctor
                  </button>
                </div>
              </form>
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
                    <input required name="specialty" list="admin-specialties" type="text" placeholder="e.g. Physiology" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500/50" />
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

                <div className="space-y-1.5">
                  <label className="text-slate-300 text-xs font-medium">Profile Photo (Optional)</label>
                  <input name="photo_file" type="file" accept="image/*" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 text-xs cursor-pointer file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-teal-500/20 file:text-teal-300 hover:file:bg-teal-500/30" />
                </div>

                <div className="pt-4 flex justify-end gap-3 border-t border-slate-800">
                  <button type="button" onClick={() => setIsAddModalOpen(false)} disabled={submitting} className="px-4 py-2 rounded-xl text-slate-400 hover:text-white text-sm font-semibold transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={submitting} className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-sm font-bold transition-colors disabled:opacity-50">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Add Doctor'}
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
