'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Calendar, Clock, UserCheck, CheckCircle2, AlertCircle, Loader2, Sunrise, Sun, Moon, ArrowRight, Edit2 } from 'lucide-react'
import apiClient from '@/lib/api/client'

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
  
  const [bookedSlots, setBookedSlots] = useState<string[]>([])
  const [slotsLoading, setSlotsLoading] = useState(false)

  const format12Hr = (time24: string) => {
    if (!time24) return '';
    const [h, m] = time24.split(':');
    let hours = parseInt(h, 10);
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    return `${hours.toString().padStart(2, '0')}:${m} ${ampm}`;
  }

  // Fetch doctors
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

  // Fetch booked slots when doctor and date change
  const fetchBookedSlots = async () => {
    if (!selectedDoctor || !bookingDate) return
    try {
      setSlotsLoading(true)
      const res = await apiClient.get(`/medai/appointments/booked-slots?doctor_id=${selectedDoctor.id}&date=${bookingDate}`)
      const slots = res.data?.data || []
      const formattedSlots = slots.map((iso: string) => {
        const d = new Date(iso)
        return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
      })
      setBookedSlots(formattedSlots)
    } catch (err) {
      console.error('Failed to fetch booked slots', err)
    } finally {
      setSlotsLoading(false)
    }
  }

  useEffect(() => {
    fetchBookedSlots()
  }, [selectedDoctor, bookingDate])

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
      const scheduledDateTime = new Date(`${bookingDate}T${bookingTime}:00`).toISOString()

      const meRes = await apiClient.get('/auth/me')
      const patientId = meRes.data?.data?.patient_id

      if (!patientId) {
        setBookingStatus({
          success: false,
          message: 'No patient profile found for your account. Please complete your registration first.',
        })
        setIsBooking(false)
        setCurrentStep(1)
        return
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
        message: `Appointment confirmed with ${selectedDoctor.full_name} for ${bookingDate} at ${bookingTime}!`,
      })
      setTimeout(() => router.push('/patient/appointments'), 2000)
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || err.message || ''
      if (errorDetail.toLowerCase().includes('double booking')) {
        setBookingStatus({
          success: false,
          message: `This slot is no longer available. Someone else just booked ${bookingTime}. Please choose another available time.`,
        })
        setBookingTime('')
        setCurrentStep(3) // Send back to time selection
        fetchBookedSlots() // Refresh slots immediately
      } else {
        setBookingStatus({
          success: false,
          message: errorDetail || 'Double booking error or availability conflict.',
        })
        setCurrentStep(3)
      }
    } finally {
      setIsBooking(false)
    }
  }

  // Generate dynamic slots based on doctor's working hours
  const generateTimeSlots = () => {
    if (!selectedDoctor) return { morning: [], afternoon: [], evening: [] }
    const startStr = selectedDoctor.working_hours_start || '09:00'
    const endStr = selectedDoctor.working_hours_end || '17:00'
    
    const slots: string[] = []
    let current = new Date(`1970-01-01T${startStr}:00`)
    const end = new Date(`1970-01-01T${endStr}:00`)
    
    while (current < end) {
      slots.push(`${current.getHours().toString().padStart(2, '0')}:${current.getMinutes().toString().padStart(2, '0')}`)
      current.setMinutes(current.getMinutes() + 30) // 30-min intervals
    }

    return {
      morning: slots.filter(s => parseInt(s.split(':')[0]) < 12),
      afternoon: slots.filter(s => parseInt(s.split(':')[0]) >= 12 && parseInt(s.split(':')[0]) < 17),
      evening: slots.filter(s => parseInt(s.split(':')[0]) >= 17)
    }
  }

  const { morning, afternoon, evening } = generateTimeSlots()
  const hasSlots = morning.length > 0 || afternoon.length > 0 || evening.length > 0

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
            const isBooked = bookedSlots.includes(slot)
            const isSelected = bookingTime === slot
            return (
              <button
                key={slot}
                type="button"
                disabled={isBooked}
                onClick={() => {
                  setBookingTime(slot)
                  setCurrentStep(4) // Advance to reason step
                }}
                className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                  isBooked 
                    ? 'bg-slate-900 border border-slate-800 text-slate-600 cursor-not-allowed opacity-60' 
                    : isSelected 
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
        <p className="text-xs text-slate-400 mt-1">Follow the steps below to schedule your consultation.</p>
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
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-slate-100">{doc.full_name}</h3>
                        <span className="text-[10px] font-mono text-teal-300 px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/20">
                          ₹{doc.consultation_fee}
                        </span>
                      </div>
                      <p className="text-[11px] text-teal-400 font-medium mt-0.5">{doc.specialty}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            selectedDoctor && (
              <div className="text-sm font-medium text-slate-300 pl-8">
                {selectedDoctor.full_name} <span className="text-xs text-teal-400">({selectedDoctor.specialty})</span>
              </div>
            )
          )}
        </div>

        {/* Step 2: Select Date */}
        {currentStep >= 2 && (
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
                <div className="flex flex-col gap-3">
                  <div className="flex gap-2">
                    {(() => {
                      const today = new Date();
                      const tomorrow = new Date(today);
                      tomorrow.setDate(today.getDate() + 1);
                      
                      const formatDateStr = (d: Date) => d.toISOString().split('T')[0];
                      const todayStr = formatDateStr(today);
                      const tomorrowStr = formatDateStr(tomorrow);
                      
                      const allowedDays = (selectedDoctor?.available_days || 'Mon,Tue,Wed,Thu,Fri').toLowerCase().split(',').map((d: string) => d.trim());
                      const isTodayAllowed = allowedDays.includes(today.toLocaleDateString('en-US', { weekday: 'short' }).toLowerCase());
                      const isTomorrowAllowed = allowedDays.includes(tomorrow.toLocaleDateString('en-US', { weekday: 'short' }).toLowerCase());
                      
                      return (
                        <>
                          <button
                            type="button"
                            disabled={!isTodayAllowed}
                            onClick={() => { setBookingDate(todayStr); setBookingTime(''); setCurrentStep(3); }}
                            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-all ${!isTodayAllowed ? 'opacity-40 cursor-not-allowed bg-slate-950 border border-slate-800 text-slate-500' : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-teal-500/50'}`}
                          >
                            Today
                          </button>
                          <button
                            type="button"
                            disabled={!isTomorrowAllowed}
                            onClick={() => { setBookingDate(tomorrowStr); setBookingTime(''); setCurrentStep(3); }}
                            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-all ${!isTomorrowAllowed ? 'opacity-40 cursor-not-allowed bg-slate-950 border border-slate-800 text-slate-500' : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-teal-500/50'}`}
                          >
                            Tomorrow
                          </button>
                        </>
                      )
                    })()}
                  </div>

                  <p className="text-xs text-slate-500 text-center font-medium my-1">OR CHOOSE DATE</p>

                  <div className="flex overflow-x-auto pb-2 gap-2 snap-x scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
                    {(() => {
                      const allowedDays = (selectedDoctor?.available_days || 'Mon,Tue,Wed,Thu,Fri').toLowerCase().split(',').map((d: string) => d.trim());
                      const dates = [];
                      const today = new Date();
                      
                      for (let i = 0; i < 14; i++) {
                        const d = new Date(today);
                        d.setDate(today.getDate() + i);
                        const dayName = d.toLocaleDateString('en-US', { weekday: 'short' }).toLowerCase();
                        if (allowedDays.includes(dayName)) {
                          dates.push(d);
                        }
                      }
                      
                      if (dates.length === 0) {
                        return (
                          <div className="text-xs text-slate-500 italic p-2 border border-dashed border-slate-800 rounded-lg w-full text-center">
                            No available dates found matching doctor's schedule.
                          </div>
                        );
                      }

                      return dates.map((d) => {
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
                      });
                    })()}
                  </div>
                </div>
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
        {currentStep >= 3 && (
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
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400">Available Time Slots for {bookingDate}</span>
                  {slotsLoading && <Loader2 className="w-4 h-4 animate-spin text-slate-500" />}
                </div>
                
                {!hasSlots ? (
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-500 text-center">
                    This doctor has no available working hours configured.
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
                <div>
                  <p className="text-xs text-slate-500 mb-1">Doctor</p>
                  <p className="font-semibold text-slate-200">{selectedDoctor.full_name}</p>
                  <p className="text-[10px] text-teal-400">{selectedDoctor.specialty}</p>
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
