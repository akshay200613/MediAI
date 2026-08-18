'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Calendar, Clock, UserCheck, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import apiClient from '@/lib/api/client'

export default function PatientBookPage() {
  const router = useRouter()
  const [doctors, setDoctors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedDoctor, setSelectedDoctor] = useState<any | null>(null)
  const [bookingDate, setBookingDate] = useState('')
  const [bookingTime, setBookingTime] = useState('10:00')
  const [reason, setReason] = useState('')
  const [isBooking, setIsBooking] = useState(false)
  const [bookingStatus, setBookingStatus] = useState<{ success: boolean; message: string } | null>(null)

  const [patientProfile, setPatientProfile] = useState<any | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setProfileLoading(true)
        const res = await apiClient.get('/auth/profile')
        const data = res.data?.data
        if (data?.patient) {
          setPatientProfile(data.patient)
        }
      } catch (err) {
        console.error('Failed to fetch patient profile', err)
      } finally {
        setProfileLoading(false)
      }
    }
    fetchProfile()
  }, [])

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        setLoading(true)
        const res = await apiClient.get('/medai/doctors?available_only=true')
        setDoctors(res.data?.data || [])
      } catch (err) {
        console.error('Failed to fetch available doctors', err)
      } finally {
        setLoading(false)
      }
    }
    fetchDoctors()
  }, [])

  const filteredDoctors = doctors.filter(
    (d) =>
      d.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      d.specialty?.toLowerCase().includes(search.toLowerCase())
  )

  const handleConfirmBooking = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedDoctor || !bookingDate || !bookingTime) return

    setIsBooking(true)
    setBookingStatus(null)

    try {
      const scheduledDateTime = new Date(`${bookingDate}T${bookingTime}:00`).toISOString()

      // /auth/me returns patient_id (the medai_patients UUID) for patient-role users
      const meRes = await apiClient.get('/auth/me')
      const patientId = meRes.data?.data?.patient_id

      if (!patientId) {
        setBookingStatus({
          success: false,
          message: 'No patient profile found for your account. Please complete your medical profile first or contact support.',
        })
        setIsBooking(false)
        return
      }

      await apiClient.post('/medai/appointments/book', {
        patient_id: patientId,
        doctor_id: selectedDoctor.id,
        scheduled_at: scheduledDateTime,
        duration_minutes: 30,
        appointment_type: 'consultation',
        reason,
      })

      setBookingStatus({
        success: true,
        message: `Appointment confirmed with ${selectedDoctor.full_name} for ${bookingDate} at ${bookingTime}!`,
      })
      setTimeout(() => router.push('/patient/appointments'), 2000)
    } catch (err: any) {
      setBookingStatus({
        success: false,
        message: err.response?.data?.detail || err.message || 'Double booking error or availability conflict.',
      })
    } finally {
      setIsBooking(false)
    }
  }

  const missingFieldsList = []
  if (!patientProfile?.date_of_birth) missingFieldsList.push('Date of Birth')
  if (!patientProfile?.gender) missingFieldsList.push('Gender')
  if (!patientProfile?.blood_group) missingFieldsList.push('Blood Group')
  if (!patientProfile?.address) missingFieldsList.push('Street Address')
  if (!patientProfile?.emergency_contact_name) missingFieldsList.push('Emergency Contact Name')
  if (!patientProfile?.emergency_contact_phone) missingFieldsList.push('Emergency Contact Phone')

  const isIncomplete = missingFieldsList.length > 0

  if (profileLoading || loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-teal-400" />
      </div>
    )
  }

  if (isIncomplete) {
    return (
      <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-4xl">
        <div className="border-b border-slate-800 pb-4">
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Book Doctor Appointment</h1>
          <p className="text-xs text-slate-400 mt-1">Select a specialist, choose an available time slot, and confirm your booking.</p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6 shadow-xl max-w-2xl mx-auto mt-10">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100">Complete Medical Profile Required</h2>
              <p className="text-[11px] text-slate-400 mt-0.5">To ensure clinical safety, you must complete your personal details first.</p>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Missing Required Information:</h3>
            <div className="flex flex-wrap gap-2">
              {missingFieldsList.map((field) => (
                <span key={field} className="px-2.5 py-1 rounded-lg text-[10px] font-medium bg-rose-500/10 border border-rose-500/20 text-rose-300">
                  ⚠️ {field}
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 hover:border-teal-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 mb-2">
                  <span className="text-xs">🤖</span>
                </div>
                <h4 className="font-semibold text-xs text-slate-200">Complete via AI Chatbot</h4>
                <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                  Let our RAG-powered chatbot collect your details conversationally and update them for you automatically.
                </p>
              </div>
              <button
                onClick={() => router.push('/patient/chat?collect_profile=true')}
                className="mt-4 w-full py-2 bg-teal-600 hover:bg-teal-500 text-white font-bold text-[11px] rounded-lg transition-colors"
              >
                Talk to AI Assistant
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/40 transition-all flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-2">
                  <UserCheck className="w-4 h-4" />
                </div>
                <h4 className="font-semibold text-xs text-slate-200">Enter Details Manually</h4>
                <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                  Fill out the standard form in your account settings manually to complete your profile records.
                </p>
              </div>
              <button
                onClick={() => router.push('/patient/profile')}
                className="mt-4 w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] rounded-lg transition-colors"
              >
                Go to Profile Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-4xl">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Book Doctor Appointment</h1>
        <p className="text-xs text-slate-400 mt-1">Select a specialist, choose an available time slot, and confirm your booking.</p>
      </div>

      {bookingStatus && (
        <div
          className={`p-4 rounded-xl text-xs flex items-center gap-2 ${
            bookingStatus.success
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          {bookingStatus.success ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <span>{bookingStatus.message}</span>
        </div>
      )}

      {/* Doctor Directory Search */}
      <div className="space-y-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">1. Select Specialist</h2>
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by doctor name or specialty..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {loading ? (
            <div className="col-span-2 py-8 text-center text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
            </div>
          ) : filteredDoctors.length === 0 ? (
            <div className="col-span-2 p-6 rounded-2xl bg-slate-900 border border-slate-800 text-center text-xs text-slate-500">
              No available doctors match your search criteria.
            </div>
          ) : (
            filteredDoctors.map((doc) => {
              const isSelected = selectedDoctor?.id === doc.id
              return (
                <div
                  key={doc.id}
                  onClick={() => setSelectedDoctor(doc)}
                  className={`p-4 rounded-xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-slate-900 border-teal-500/60 shadow-lg shadow-teal-500/10'
                      : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-slate-100">{doc.full_name}</h3>
                    <span className="text-[10px] font-mono text-teal-300 px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/20">
                      ${doc.consultation_fee}
                    </span>
                  </div>
                  <p className="text-[11px] text-teal-400 font-medium mt-0.5">{doc.specialty}</p>
                  <p className="text-[11px] text-slate-400 mt-1">{doc.years_of_experience} yrs experience</p>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Date & Slot Picker Form */}
      {selectedDoctor && (
        <form onSubmit={handleConfirmBooking} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            2. Choose Date & Time Slot for {selectedDoctor.full_name}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300">Consultation Date</label>
              <input
                type="date"
                required
                min={new Date().toISOString().split('T')[0]}
                value={bookingDate}
                onChange={(e) => setBookingDate(e.target.value)}
                className="w-full mt-1 p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500/50"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300">Time Slot</label>
              <select
                value={bookingTime}
                onChange={(e) => setBookingTime(e.target.value)}
                className="w-full mt-1 p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500/50"
              >
                <option value="09:00">09:00 AM</option>
                <option value="10:00">10:00 AM</option>
                <option value="11:30">11:30 AM</option>
                <option value="14:00">02:00 PM</option>
                <option value="15:30">03:30 PM</option>
                <option value="16:30">04:30 PM</option>
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-300">Reason for Visit / Symptoms</label>
            <input
              type="text"
              placeholder="e.g. Annual health checkup, persistent cough, follow-up"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500/50"
            />
          </div>

          <button
            type="submit"
            disabled={isBooking || !bookingDate}
            className="w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-lg shadow-teal-900/30 inline-flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            {isBooking ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Confirm Appointment Booking
          </button>
        </form>
      )}
    </div>
  )
}
