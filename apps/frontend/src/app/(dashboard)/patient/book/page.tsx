'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Calendar, Clock, UserCheck, CheckCircle2, AlertCircle, Loader2, Sunrise, Sun, Moon, ArrowRight, Edit2 } from 'lucide-react'
import apiClient from '@/lib/api/client'
import { extractErrorMessage } from '@/lib/utils'
import { useAppointmentSocket } from '@/lib/hooks/useAppointmentSocket'

export default function PatientBookPage() {
  const router = useRouter()
  const [doctors, setDoctors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedDoctor, setSelectedDoctor] = useState<any | null>(null)
  
  // Wizard state
  const [currentStep, setCurrentStep] = useState<number>(1)
  
  const [bookingDate, setBookingDate] = useState('')
  const [bookingTime, setBookingTime] = useState('')
  const [reason, setReason] = useState('')
  const [isBooking, setIsBooking] = useState(false)
  const [bookingStatus, setBookingStatus] = useState<{ success: boolean; message: string } | null>(null)
  
  // ISO datetimes of booked appointments for next 14 days
  const [bookedSlots, setBookedSlots] = useState<string[]>([])
  const [slotsLoading, setSlotsLoading] = useState(false)

  const format12Hr = (time24: string) => {
    if (!time24) return '';
    const clean = time24.slice(0, 5)
    const [h, m] = clean.split(':');
    let hours = parseInt(h, 10);
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    return `${hours.toString().padStart(2, '0')}:${m} ${ampm}`;
  }

  // Active appointments limit tracking (max 2)
  const [activeAppointmentsCount, setActiveAppointmentsCount] = useState<number>(0)

  const fetchActiveAppointmentsCount = async () => {
    try {
      const res = await apiClient.get('/medai/appointments?upcoming_only=true')
      const list = Array.isArray(res.data?.data) ? res.data.data : []
      const active = list.filter((a: any) =>
        ['scheduled', 'confirmed', 'in_progress'].includes(String(a?.status || '').toLowerCase())
      )
      setActiveAppointmentsCount(active.length)
    } catch (err) {
      console.warn('Failed to fetch active appointments count', err)
    }
  }

  // Fetch available doctors
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
    fetchProfileStatus()
    fetchActiveAppointmentsCount()
  }, [])

  // Patient Profile Completeness State
  const [profileStatus, setProfileStatus] = useState<{
    is_complete: boolean
    missing_fields: string[]
    message: string
    patient: any
  } | null>(null)
  const [showProfileCard, setShowProfileCard] = useState(false)
  const [savingProfile, setSavingProfile] = useState(false)

  const [profPhone, setProfPhone] = useState('')
  const [profGender, setProfGender] = useState('male')
  const [profDob, setProfDob] = useState('')
  const [profBloodGroup, setProfBloodGroup] = useState('')
  const [profAllergies, setProfAllergies] = useState('')
  const [profChronicConditions, setProfChronicConditions] = useState('')

  const fetchProfileStatus = async () => {
    try {
      const res = await apiClient.get('/medai/patients/me/profile-status')
      const data = res.data?.data
      if (data) {
        setProfileStatus(data)
        const pat = data.patient
        if (pat) {
          if (pat.phone && pat.phone !== '000-000-0000') setProfPhone(pat.phone)
          if (pat.gender) setProfGender(pat.gender)
          if (pat.date_of_birth) setProfDob(pat.date_of_birth)
          if (pat.blood_group) setProfBloodGroup(pat.blood_group)
          if (pat.allergies) setProfAllergies(pat.allergies)
          if (pat.chronic_conditions) setProfChronicConditions(pat.chronic_conditions)
        }
        if (!data.is_complete) {
          setShowProfileCard(true)
        }
      }
    } catch (err) {
      console.error('Failed to fetch profile status', err)
    }
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!profPhone || profPhone.trim() === '000-000-0000' || !profGender || !profDob) {
      setBookingStatus({
        success: false,
        message: 'Please fill in all mandatory profile fields: Phone Number, Gender, and Date of Birth.',
      })
      return
    }

    try {
      setSavingProfile(true)
      await apiClient.patch('/medai/patients/me', {
        phone: profPhone,
        gender: profGender,
        date_of_birth: profDob,
        blood_group: profBloodGroup || undefined,
        allergies: profAllergies || undefined,
        chronic_conditions: profChronicConditions || undefined,
      })
      setBookingStatus({
        success: true,
        message: 'Medical profile saved successfully! You may now proceed with booking.',
      })
      setShowProfileCard(false)
      await fetchProfileStatus()
    } catch (err: any) {
      console.error('Failed to save profile', err)
      setBookingStatus({
        success: false,
        message: err.response?.data?.detail || 'Failed to save profile details.',
      })
    } finally {
      setSavingProfile(false)
    }
  }

  // Fetch booked slots for the selected doctor across the next 14 days
  const fetchBookedSlots = async () => {
    if (!selectedDoctor) return
    try {
      setSlotsLoading(true)
      const now = new Date()
      const todayStr = now.toISOString().split('T')[0]
      const future = new Date(now)
      future.setDate(now.getDate() + 14)
      const futureStr = future.toISOString().split('T')[0]

      const res = await apiClient.get(`/medai/appointments/booked-slots?doctor_id=${selectedDoctor.id}&date=${todayStr}&end_date=${futureStr}`)
      setBookedSlots(res.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch booked slots', err)
    } finally {
      setSlotsLoading(false)
    }
  }

  useEffect(() => {
    fetchBookedSlots()
  }, [selectedDoctor])

  // Real-time slot synchronization: update booked slots and active appointments instantly on WebSocket events
  useAppointmentSocket(() => {
    if (selectedDoctor) {
      fetchBookedSlots()
    }
    fetchActiveAppointmentsCount()
  })

  const parseAllowedDays = (daysStr?: string): string[] => {
    if (!daysStr) return ['mon', 'tue', 'wed', 'thu', 'fri']
    const allDays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    const dayMap: Record<string, string> = {
      monday: 'mon', mon: 'mon',
      tuesday: 'tue', tue: 'tue',
      wednesday: 'wed', wed: 'wed',
      thursday: 'thu', thu: 'thu',
      friday: 'fri', fri: 'fri',
      saturday: 'sat', sat: 'sat',
      sunday: 'sun', sun: 'sun',
    }
    const clean = daysStr.toLowerCase().trim()
    if (clean.includes('-') && !clean.includes(',')) {
      const parts = clean.split('-')
      const s = dayMap[parts[0].trim()] || 'mon'
      const e = dayMap[parts[1].trim()] || 'fri'
      const sIdx = allDays.indexOf(s)
      const eIdx = allDays.indexOf(e)
      if (sIdx !== -1 && eIdx !== -1) {
        return sIdx <= eIdx ? allDays.slice(sIdx, eIdx + 1) : [...allDays.slice(sIdx), ...allDays.slice(0, eIdx + 1)]
      }
    }
    const result = new Set<string>()
    clean.replace(';', ',').split(',').forEach((t) => {
      const item = t.trim()
      if (dayMap[item]) result.add(dayMap[item])
    })
    return result.size > 0 ? Array.from(result) : ['mon', 'tue', 'wed', 'thu', 'fri']
  }

  const getLocalDateStr = (d: Date) => {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  // Compute available dates (next 14 days) that match doctor's schedule and have AT LEAST 1 open slot
  const getAvailableDates = () => {
    if (!selectedDoctor) return []
    const allowedDays = parseAllowedDays(selectedDoctor.available_days)

    const startStr = (selectedDoctor.working_hours_start || '09:00').slice(0, 5)
    const endStr = (selectedDoctor.working_hours_end || '17:00').slice(0, 5)

    // Candidate 30-min time slots strictly within doctor's working hours
    const baseSlots: string[] = []
    let curr = new Date(`1970-01-01T${startStr}:00`)
    const end = new Date(`1970-01-01T${endStr}:00`)
    while (curr.getTime() + 30 * 60 * 1000 <= end.getTime()) {
      baseSlots.push(`${curr.getHours().toString().padStart(2, '0')}:${curr.getMinutes().toString().padStart(2, '0')}`)
      curr.setMinutes(curr.getMinutes() + 30)
    }

    const now = new Date()
    const todayStr = getLocalDateStr(now)
    const currentMins = now.getHours() * 60 + now.getMinutes()

    const bookedSet = new Set(
      bookedSlots.map((iso: string) => {
        const d = new Date(iso)
        const datePart = getLocalDateStr(d)
        const timePart = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
        return `${datePart}T${timePart}`
      })
    )

    const available: Date[] = []

    for (let i = 0; i < 14; i++) {
      const d = new Date(now)
      d.setDate(now.getDate() + i)
      const dayName = d.toLocaleDateString('en-US', { weekday: 'short' }).toLowerCase()

      // 1. Must match doctor's specific available days
      if (!allowedDays.includes(dayName)) continue

      const dateStr = getLocalDateStr(d)

      // 2. Count remaining unbooked future slots for this date
      const openSlots = baseSlots.filter(slot => {
        if (bookedSet.has(`${dateStr}T${slot}`)) return false
        if (dateStr === todayStr) {
          const [h, m] = slot.split(':').map(Number)
          if (h * 60 + m <= currentMins) return false
        }
        return true
      })

      // ONLY include date if it has open slots available
      if (openSlots.length > 0) {
        available.push(d)
      }
    }

    return available
  }

  const availableDates = getAvailableDates()

  // Auto-select first available date if current date selection is invalid or empty
  useEffect(() => {
    if (selectedDoctor && availableDates.length > 0) {
      const dateStrs = availableDates.map(d => getLocalDateStr(d))
      if (!bookingDate || !dateStrs.includes(bookingDate)) {
        setBookingDate(dateStrs[0])
      }
    }
  }, [selectedDoctor, bookedSlots])

  // Generate open, unbooked time slots strictly within selected doctor's working hours
  const generateTimeSlots = () => {
    if (!selectedDoctor || !bookingDate) return { morning: [], afternoon: [], evening: [] }
    const startStr = (selectedDoctor.working_hours_start || '09:00').slice(0, 5)
    const endStr = (selectedDoctor.working_hours_end || '17:00').slice(0, 5)
    
    const slots: string[] = []
    let current = new Date(`1970-01-01T${startStr}:00`)
    const end = new Date(`1970-01-01T${endStr}:00`)
    
    while (current.getTime() + 30 * 60 * 1000 <= end.getTime()) {
      slots.push(`${current.getHours().toString().padStart(2, '0')}:${current.getMinutes().toString().padStart(2, '0')}`)
      current.setMinutes(current.getMinutes() + 30)
    }

    const now = new Date()
    const todayStr = getLocalDateStr(now)
    const currentMins = now.getHours() * 60 + now.getMinutes()

    const bookedSet = new Set(
      bookedSlots.map((iso: string) => {
        const d = new Date(iso)
        const datePart = getLocalDateStr(d)
        const timePart = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
        return `${datePart}T${timePart}`
      })
    )

    // Exclude booked slots and past time slots
    const availableSlots = slots.filter(slot => {
      if (bookedSet.has(`${bookingDate}T${slot}`)) return false
      if (bookingDate === todayStr) {
        const [h, m] = slot.split(':').map(Number)
        if (h * 60 + m <= currentMins) return false
      }
      return true
    })

    return {
      morning: availableSlots.filter(s => parseInt(s.split(':')[0]) < 12),
      afternoon: availableSlots.filter(s => parseInt(s.split(':')[0]) >= 12 && parseInt(s.split(':')[0]) < 17),
      evening: availableSlots.filter(s => parseInt(s.split(':')[0]) >= 17)
    }
  }

  const { morning, afternoon, evening } = generateTimeSlots()
  const hasSlots = morning.length > 0 || afternoon.length > 0 || evening.length > 0

  const filteredDoctors = doctors.filter(
    (d) =>
      d.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      d.specialty?.toLowerCase().includes(search.toLowerCase())
  )

  const handleConfirmBooking = async () => {
    if (!selectedDoctor || !bookingDate || !bookingTime) return

    setIsBooking(true)
    setBookingStatus(null)

    try {
      const scheduledDateTime = `${bookingDate}T${bookingTime}:00`

      let patientId: string | null = null
      try {
        const meRes = await apiClient.get('/auth/me')
        patientId = meRes.data?.data?.patient_id || meRes.data?.data?.id
      } catch (err) {
        console.error('Failed to get /auth/me', err)
      }

      await apiClient.post('/medai/appointments/book', {
        patient_id: patientId,
        doctor_id: selectedDoctor.id,
        scheduled_at: scheduledDateTime,
        duration_minutes: 30,
        appointment_type: 'consultation',
        reason: reason || 'General checkup',
      })

      setBookingStatus({
        success: true,
        message: `Appointment confirmed with ${selectedDoctor.full_name} for ${bookingDate} at ${format12Hr(bookingTime)}!`,
      })
      setTimeout(() => router.push('/patient/appointments'), 2000)
    } catch (err: any) {
      const errorMsg = extractErrorMessage(err)
      const lowerErr = errorMsg.toLowerCase()
      if (lowerErr.includes('slot booking limit') || lowerErr.includes('maximum capacity')) {
        setBookingStatus({
          success: false,
          message: errorMsg || 'This slot has reached maximum capacity (2 bookings). Please choose another available time slot.',
        })
        setBookingTime('')
        setCurrentStep(3)
        fetchBookedSlots()
      } else if (lowerErr.includes('already have an active appointment') || lowerErr.includes('already have another appointment')) {
        setBookingStatus({
          success: false,
          message: errorMsg,
        })
        setBookingTime('')
        setCurrentStep(3)
        fetchBookedSlots()
        fetchActiveAppointmentsCount()
      } else if (lowerErr.includes('booking limit reached') || lowerErr.includes('maximum of 2 active') || lowerErr.includes('maximum of')) {
        setBookingStatus({
          success: false,
          message: errorMsg,
        })
        fetchActiveAppointmentsCount()
      } else {
        setBookingStatus({
          success: false,
          message: errorMsg || 'Booking failed due to an availability conflict.',
        })
        setCurrentStep(3)
      }
    } finally {
      setIsBooking(false)
    }

  }

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-teal-400" />
      </div>
    )
  }

  const renderSlotButtons = (slots: string[], icon: React.ReactNode, title: string) => {
    if (slots.length === 0) return null
    return (
      <div className="space-y-3 mt-4">
        <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          {icon} {title}
        </h4>
        <div className="flex flex-wrap gap-2">
          {slots.map(slot => {
            const isSelected = bookingTime === slot
            return (
              <button
                key={slot}
                type="button"
                onClick={() => {
                  setBookingTime(slot)
                  setCurrentStep(4)
                }}
                className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                  isSelected 
                    ? 'bg-teal-600 text-white shadow-lg shadow-teal-900/40' 
                    : 'bg-slate-950 border border-slate-700 text-slate-300 hover:border-teal-500/50 hover:bg-slate-900'
                }`}
              >
                {format12Hr(slot)}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-3xl mx-auto">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Book Doctor Appointment</h1>
        <p className="text-xs text-slate-400 mt-1">Select a doctor to view their specific available days and working hours.</p>
      </div>

      {activeAppointmentsCount >= 2 && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-start justify-between gap-3 shadow-lg">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-amber-300">Active Booking Limit Reached (2/2)</p>
              <p className="text-[11px] text-amber-200/80 mt-0.5">
                You already have {activeAppointmentsCount} active appointments scheduled. Hospital policy allows a maximum of 2 active bookings per patient. Please complete or cancel an existing appointment before booking a new one.
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push('/patient/appointments')}
            className="px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-semibold border border-amber-500/30 shrink-0 transition-colors"
          >
            My Appointments
          </button>
        </div>
      )}

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

      {showProfileCard && (
        <form onSubmit={handleSaveProfile} className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 to-teal-950/40 border border-teal-500/40 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-teal-400 shrink-0" />
              <div>
                <h3 className="text-sm font-bold text-slate-100">Complete Your Medical Profile</h3>
                <p className="text-[11px] text-teal-300">Mandatory details (Phone, Gender, Date of Birth) are required before booking.</p>
              </div>
            </div>
            <span className="text-[10px] uppercase tracking-wider font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20">
              Required
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-300 mb-1 block">Phone Number *</label>
              <input
                type="tel"
                required
                placeholder="e.g. +91 9876543210"
                value={profPhone}
                onChange={(e) => setProfPhone(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-300 mb-1 block">Gender *</label>
              <select
                value={profGender}
                onChange={(e) => setProfGender(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-300 mb-1 block">Date of Birth *</label>
              <input
                type="date"
                required
                value={profDob}
                onChange={(e) => setProfDob(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            <div>
              <label className="text-[11px] font-medium text-slate-400 mb-1 block">Blood Group (Optional)</label>
              <input
                type="text"
                placeholder="e.g. O+, A+"
                value={profBloodGroup}
                onChange={(e) => setProfBloodGroup(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-[11px] font-medium text-slate-400 mb-1 block">Allergies / Relevant History (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Penicillin allergy, Hypertension"
                value={profAllergies}
                onChange={(e) => setProfAllergies(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="submit"
              disabled={savingProfile}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-teal-900/30 flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {savingProfile ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              Save Medical Profile
            </button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {/* Step 1: Select Specialist */}
        <div className={`p-5 rounded-2xl border transition-all ${currentStep === 1 ? 'bg-slate-900 border-teal-500/50 shadow-xl shadow-teal-900/10' : 'bg-slate-900/40 border-slate-800 opacity-60 hover:opacity-100'}`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs ${currentStep === 1 ? 'bg-teal-600 text-white' : 'bg-slate-800 text-slate-400'}`}>1</span>
              Select Specialist
            </h2>
            {currentStep > 1 && (
              <button onClick={() => setCurrentStep(1)} className="text-[10px] flex items-center gap-1 text-teal-400 hover:text-teal-300">
                <Edit2 className="w-3 h-3" /> Change
              </button>
            )}
          </div>
          
          {currentStep === 1 ? (
            <div className="space-y-4">
              <div className="relative max-w-md">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Search by doctor name or specialty..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {filteredDoctors.length === 0 ? (
                  <div className="col-span-2 p-4 rounded-xl border border-dashed border-slate-800 text-center text-xs text-slate-500">
                    No available doctors match your search criteria.
                  </div>
                ) : (
                  filteredDoctors.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => {
                        setSelectedDoctor(doc)
                        setBookingDate('')
                        setBookingTime('')
                        setCurrentStep(2)
                      }}
                      className="p-4 rounded-xl border border-slate-800 bg-slate-950 hover:border-teal-500/50 text-xs cursor-pointer transition-all hover:bg-slate-900"
                    >
                      <div className="flex items-center gap-3 mb-2">
                        {doc.profile_image_url ? (
                          <div className="w-10 h-10 rounded-full overflow-hidden shrink-0 border border-slate-700">
                            <img src={doc.profile_image_url.startsWith('http') ? doc.profile_image_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${doc.profile_image_url}`} alt={doc.full_name} className="object-cover w-full h-full" />
                          </div>
                        ) : (
                          <div className="w-10 h-10 rounded-full shrink-0 bg-slate-800 flex items-center justify-center text-slate-400 border border-slate-700">
                            <UserCheck className="w-4 h-4" />
                          </div>
                        )}
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h3 className="font-semibold text-slate-100">{doc.full_name}</h3>
                            <span className="text-[10px] font-mono text-teal-300 px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/20">
                              ₹{doc.consultation_fee}
                            </span>
                          </div>
                          <p className="text-[11px] text-teal-400 font-medium mt-0.5">{doc.specialty}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 mt-2.5 pt-2 border-t border-slate-800 text-[10px] text-slate-400">
                        <Clock className="w-3 h-3 text-teal-400 shrink-0" />
                        <span>
                          Days: <strong className="text-slate-200">{doc.available_days || 'Mon,Tue,Wed,Thu,Fri'}</strong> | Hours: <strong className="text-slate-200">{format12Hr(doc.working_hours_start || '09:00')} - {format12Hr(doc.working_hours_end || '17:00')}</strong>
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            selectedDoctor && (
              <div className="text-sm font-medium text-slate-300 pl-8 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {selectedDoctor.profile_image_url ? (
                    <div className="w-6 h-6 rounded-full overflow-hidden shrink-0 border border-slate-700">
                      <img 
                        src={selectedDoctor.profile_image_url.startsWith('http') ? selectedDoctor.profile_image_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${selectedDoctor.profile_image_url}`} 
                        alt={selectedDoctor.full_name} 
                        className="object-cover w-full h-full" 
                      />
                    </div>
                  ) : null}
                  <span>{selectedDoctor.full_name}</span> <span className="text-xs text-teal-400">({selectedDoctor.specialty})</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  {selectedDoctor.available_days || 'Mon,Tue,Wed,Thu,Fri'} • {format12Hr(selectedDoctor.working_hours_start || '09:00')} to {format12Hr(selectedDoctor.working_hours_end || '17:00')}
                </div>
              </div>
            )
          )}
        </div>

        {/* Step 2: Select Date */}
        {currentStep >= 2 && selectedDoctor && (
          <div className={`p-5 rounded-2xl border transition-all ${currentStep === 2 ? 'bg-slate-900 border-teal-500/50 shadow-xl shadow-teal-900/10' : 'bg-slate-900/40 border-slate-800 opacity-60 hover:opacity-100'}`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs ${currentStep === 2 ? 'bg-teal-600 text-white' : 'bg-slate-800 text-slate-400'}`}>2</span>
                Choose Date
              </h2>
              {currentStep > 2 && (
                <button onClick={() => setCurrentStep(2)} className="text-[10px] flex items-center gap-1 text-teal-400 hover:text-teal-300">
                  <Edit2 className="w-3 h-3" /> Change
                </button>
              )}
            </div>
            
            {currentStep === 2 ? (
              <div className="space-y-4">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-teal-400 shrink-0" />
                    <div>
                      <p className="font-semibold text-slate-200">Schedule for {selectedDoctor.full_name}</p>
                      <p className="text-[11px] text-slate-400">
                        Available Days: <strong className="text-teal-300">{selectedDoctor.available_days || 'Mon,Tue,Wed,Thu,Fri'}</strong> | Working Hours: <strong className="text-teal-300">{format12Hr(selectedDoctor.working_hours_start || '09:00')} - {format12Hr(selectedDoctor.working_hours_end || '17:00')}</strong>
                      </p>
                    </div>
                  </div>
                </div>

                {slotsLoading ? (
                  <div className="flex items-center justify-center py-6 gap-2 text-xs text-slate-400">
                    <Loader2 className="w-4 h-4 animate-spin text-teal-400" />
                    <span>Checking Dr. {selectedDoctor.last_name}'s schedule & open slots...</span>
                  </div>
                ) : availableDates.length === 0 ? (
                  <div className="p-4 bg-slate-950 border border-dashed border-slate-800 rounded-xl text-xs text-slate-400 text-center">
                    Dr. {selectedDoctor?.full_name} has no available booking slots for the next 14 days. All slots are either fully booked or outside working hours ({selectedDoctor.available_days || 'Mon,Tue,Wed,Thu,Fri'}).
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    <div className="flex gap-2">
                      {(() => {
                        const now = new Date();
                        const todayStr = now.toISOString().split('T')[0];
                        const tomorrow = new Date(now);
                        tomorrow.setDate(now.getDate() + 1);
                        const tomorrowStr = tomorrow.toISOString().split('T')[0];

                        const isTodayAvailable = availableDates.some(d => d.toISOString().split('T')[0] === todayStr);
                        const isTomorrowAvailable = availableDates.some(d => d.toISOString().split('T')[0] === tomorrowStr);

                        if (!isTodayAvailable && !isTomorrowAvailable) return null;

                        return (
                          <>
                            {isTodayAvailable && (
                              <button
                                type="button"
                                onClick={() => { setBookingDate(todayStr); setBookingTime(''); setCurrentStep(3); }}
                                className={`flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all ${bookingDate === todayStr ? 'bg-teal-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-teal-500/50'}`}
                              >
                                Today
                              </button>
                            )}
                            {isTomorrowAvailable && (
                              <button
                                type="button"
                                onClick={() => { setBookingDate(tomorrowStr); setBookingTime(''); setCurrentStep(3); }}
                                className={`flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all ${bookingDate === tomorrowStr ? 'bg-teal-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-teal-500/50'}`}
                              >
                                Tomorrow
                              </button>
                            )}
                          </>
                        )
                      })()}
                    </div>

                    <p className="text-[10px] text-slate-500 uppercase tracking-wider text-center font-medium my-1">
                      Available Dates for Dr. {selectedDoctor.last_name}
                    </p>

                    <div className="flex overflow-x-auto pb-2 gap-2 snap-x scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
                      {availableDates.map((d) => {
                        const dateStr = d.toISOString().split('T')[0];
                        const isSelected = bookingDate === dateStr;
                        const dayName = d.toLocaleDateString('en-US', { weekday: 'short' });
                        const monthName = d.toLocaleDateString('en-US', { month: 'short' });
                        const dayNum = d.getDate();
                        
                        return (
                          <button
                            key={dateStr}
                            type="button"
                            onClick={() => { setBookingDate(dateStr); setBookingTime(''); setCurrentStep(3); }}
                            className={`flex-shrink-0 snap-center flex flex-col items-center justify-center w-16 h-20 rounded-2xl border transition-all ${
                              isSelected
                                ? 'bg-teal-600 border-teal-500 text-white shadow-lg shadow-teal-900/40'
                                : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-teal-500/50 hover:bg-slate-900'
                            }`}
                          >
                            <span className={`text-[10px] font-medium uppercase ${isSelected ? 'text-teal-100' : 'text-slate-500'}`}>
                              {dayName}
                            </span>
                            <span className="text-xl font-bold mt-0.5">{dayNum}</span>
                            <span className={`text-[10px] ${isSelected ? 'text-teal-200' : 'text-slate-500'}`}>
                              {monthName}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              bookingDate && (
                <div className="text-sm font-medium text-slate-300 pl-8">
                  {bookingDate}
                </div>
              )
            )}
          </div>
        )}

        {/* Step 3: Select Time */}
        {currentStep >= 3 && selectedDoctor && (
          <div className={`p-5 rounded-2xl border transition-all ${currentStep === 3 ? 'bg-slate-900 border-teal-500/50 shadow-xl shadow-teal-900/10' : 'bg-slate-900/40 border-slate-800 opacity-60 hover:opacity-100'}`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs ${currentStep === 3 ? 'bg-teal-600 text-white' : 'bg-slate-800 text-slate-400'}`}>3</span>
                Select Time
              </h2>
              {currentStep > 3 && (
                <button onClick={() => setCurrentStep(3)} className="text-[10px] flex items-center gap-1 text-teal-400 hover:text-teal-300">
                  <Edit2 className="w-3 h-3" /> Change
                </button>
              )}
            </div>
            
            {currentStep === 3 ? (
              <div className="space-y-4">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-teal-400 shrink-0" />
                    <div>
                      <p className="font-semibold text-slate-200">Doctor Working Hours on {bookingDate}</p>
                      <p className="text-[11px] text-slate-400">
                        Dr. {selectedDoctor.full_name} is available from <strong className="text-teal-300">{format12Hr(selectedDoctor.working_hours_start || '09:00')}</strong> to <strong className="text-teal-300">{format12Hr(selectedDoctor.working_hours_end || '17:00')}</strong>.
                      </p>
                    </div>
                  </div>
                  {slotsLoading && <Loader2 className="w-4 h-4 animate-spin text-teal-400 shrink-0" />}
                </div>
                
                {!hasSlots ? (
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-400 text-center">
                    No open time slots for {bookingDate} within Dr. {selectedDoctor.last_name}'s working hours ({format12Hr(selectedDoctor.working_hours_start || '09:00')} - {format12Hr(selectedDoctor.working_hours_end || '17:00')}). All slots are either booked or past.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {renderSlotButtons(morning, <Sunrise className="w-3.5 h-3.5 text-amber-400" />, 'Morning')}
                    {renderSlotButtons(afternoon, <Sun className="w-3.5 h-3.5 text-orange-400" />, 'Afternoon')}
                    {renderSlotButtons(evening, <Moon className="w-3.5 h-3.5 text-indigo-400" />, 'Evening')}
                  </div>
                )}
              </div>
            ) : (
              bookingTime && (
                <div className="text-sm font-medium text-slate-300 pl-8">
                  {format12Hr(bookingTime)}
                </div>
              )
            )}
          </div>
        )}

        {/* Step 4: Reason */}
        {currentStep >= 4 && (
          <div className={`p-5 rounded-2xl border transition-all ${currentStep === 4 ? 'bg-slate-900 border-teal-500/50 shadow-xl shadow-teal-900/10' : 'bg-slate-900/40 border-slate-800 opacity-60 hover:opacity-100'}`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs ${currentStep === 4 ? 'bg-teal-600 text-white' : 'bg-slate-800 text-slate-400'}`}>4</span>
                Reason for Visit <span className="text-xs font-normal text-slate-500">(Optional)</span>
              </h2>
              {currentStep > 4 && (
                <button onClick={() => setCurrentStep(4)} className="text-[10px] flex items-center gap-1 text-teal-400 hover:text-teal-300">
                  <Edit2 className="w-3 h-3" /> Change
                </button>
              )}
            </div>
            
            {currentStep === 4 ? (
              <div className="space-y-4 pl-8">
                <div className="flex flex-wrap gap-2">
                  {['General checkup', 'Follow-up', 'New symptoms', 'Other'].map(opt => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setReason(opt)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                        reason === opt 
                          ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30' 
                          : 'bg-slate-950 border border-slate-800 hover:border-slate-600 text-slate-300 hover:bg-slate-900'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
                <textarea
                  rows={2}
                  placeholder="Additional details... (Optional)"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500/50 resize-none"
                />
                <button
                  type="button"
                  onClick={() => setCurrentStep(5)}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs shadow-lg shadow-teal-900/30 transition-colors"
                >
                  Review Booking <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <div className="text-sm font-medium text-slate-300 pl-8">
                {reason || 'Not specified'}
              </div>
            )}
          </div>
        )}

        {/* Step 5: Confirmation */}
        {currentStep === 5 && selectedDoctor && (
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-700 space-y-6 shadow-2xl mt-8">
            <div className="border-b border-slate-800 pb-4 text-center">
              <div className="w-12 h-12 rounded-full bg-teal-500/10 flex items-center justify-center mx-auto mb-3 border border-teal-500/20">
                <Calendar className="w-5 h-5 text-teal-400" />
              </div>
              <h2 className="text-lg font-bold text-slate-100">Final Confirmation</h2>
              <p className="text-xs text-slate-400 mt-1">Please review the details and confirm your appointment.</p>
            </div>

            <div className="bg-slate-950 rounded-xl p-5 border border-slate-800 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-3">
                  {selectedDoctor.profile_image_url ? (
                    <div className="w-10 h-10 rounded-full overflow-hidden shrink-0 border border-slate-700">
                      <img 
                        src={selectedDoctor.profile_image_url.startsWith('http') ? selectedDoctor.profile_image_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${selectedDoctor.profile_image_url}`} 
                        alt={selectedDoctor.full_name} 
                        className="object-cover w-full h-full" 
                      />
                    </div>
                  ) : null}
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Doctor</p>
                    <p className="font-semibold text-slate-200">{selectedDoctor.full_name}</p>
                    <p className="text-[10px] text-teal-400">{selectedDoctor.specialty}</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Date & Time</p>
                  <p className="font-semibold text-slate-200">{bookingDate}</p>
                  <p className="text-xs text-slate-400">{format12Hr(bookingTime)}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-xs text-slate-500 mb-1">Reason for Visit</p>
                  <p className="text-sm text-slate-300">{reason || 'Not specified'}</p>
                </div>
                <div className="col-span-2 pt-3 border-t border-slate-800 flex justify-between items-center">
                  <p className="text-xs text-slate-500">Consultation Fee</p>
                  <p className="font-bold text-teal-300 text-lg">₹{selectedDoctor.consultation_fee}</p>
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setCurrentStep(1)}
                disabled={isBooking}
                className="flex-1 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-sm transition-colors"
              >
                Change Details
              </button>
              <button
                onClick={handleConfirmBooking}
                disabled={isBooking}
                className="flex-1 py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-sm shadow-lg shadow-teal-900/30 inline-flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                {isBooking ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Confirm Appointment
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
