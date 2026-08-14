'use client'

import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User,
  Stethoscope,
  ShieldCheck,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Phone,
  Mail,
  Calendar,
  Heart,
  FileText,
  Clock,
  Briefcase,
  MapPin,
  Building,
  Save,
  Lock,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { useAuth } from '@/lib/auth/context'
import toast from 'react-hot-toast'
import { easeOutExpo } from '@/lib/motion'

const SPECIALTIES = [
  'General Medicine', 'Cardiology', 'Dermatology', 'Endocrinology',
  'Gastroenterology', 'Neurology', 'Obstetrics & Gynecology', 'Oncology',
  'Ophthalmology', 'Orthopedics', 'Pediatrics', 'Psychiatry',
  'Pulmonology', 'Radiology', 'Surgery', 'Urology', 'ENT',
]

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function AccountSettingsPage() {
  const { user, refreshUser } = useAuth()
  const [activeTab, setActiveTab] = useState<'profile' | 'security'>('profile')

  const [loading, setLoading] = useState(true)
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)

  // Account / User State
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('')

  // Doctor Fields State
  const [phone, setPhone] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [licenseNumber, setLicenseNumber] = useState('')
  const [yearsOfExperience, setYearsOfExperience] = useState<number>(0)
  const [consultationFee, setConsultationFee] = useState<number>(0)
  const [bio, setBio] = useState('')
  const [availableDays, setAvailableDays] = useState<string[]>([])
  const [workingHoursStart, setWorkingHoursStart] = useState('09:00')
  const [workingHoursEnd, setWorkingHoursEnd] = useState('17:00')
  const [isAvailable, setIsAvailable] = useState(true)

  // Patient Fields State
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [gender, setGender] = useState('')
  const [bloodGroup, setBloodGroup] = useState('')
  const [address, setAddress] = useState('')
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [allergies, setAllergies] = useState('')
  const [chronicConditions, setChronicConditions] = useState('')
  const [emergencyName, setEmergencyName] = useState('')
  const [emergencyPhone, setEmergencyPhone] = useState('')

  // Change Password State
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const fetchProfile = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get('/auth/profile')
      const data = res.data?.data
      if (data) {
        const u = data.user
        setFullName(u.full_name || '')
        setEmail(u.email || '')
        setRole(u.role || '')

        if (data.doctor) {
          const d = data.doctor
          setPhone(d.phone || '')
          setSpecialty(d.specialty || 'General Medicine')
          setLicenseNumber(d.license_number || '')
          setYearsOfExperience(d.years_of_experience || 0)
          setConsultationFee(d.consultation_fee || 0)
          setBio(d.bio || '')
          setAvailableDays(d.available_days ? d.available_days.split(',') : [])
          setWorkingHoursStart(d.working_hours_start || '09:00')
          setWorkingHoursEnd(d.working_hours_end || '17:00')
          setIsAvailable(d.is_available ?? true)
        }

        if (data.patient) {
          const p = data.patient
          if (!phone) setPhone(p.phone || '')
          setDateOfBirth(p.date_of_birth || '')
          setGender(p.gender || '')
          setBloodGroup(p.blood_group || '')
          setAddress(p.address || '')
          setCity(p.city || '')
          setState(p.state || '')
          setAllergies(p.allergies || '')
          setChronicConditions(p.chronic_conditions || '')
          setEmergencyName(p.emergency_contact_name || '')
          setEmergencyPhone(p.emergency_contact_phone || '')
        }
      }
    } catch (err: any) {
      console.error('Failed to load profile settings', err)
      toast.error('Failed to load profile details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfile()
  }, [])

  const toggleDay = (day: string) => {
    setAvailableDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSavingProfile(true)
    try {
      const payload: any = {
        full_name: fullName,
        phone: phone,
      }

      if (role === 'doctor') {
        payload.specialty = specialty
        payload.years_of_experience = yearsOfExperience
        payload.consultation_fee = consultationFee
        payload.bio = bio
        payload.available_days = availableDays.join(',')
        payload.working_hours_start = workingHoursStart
        payload.working_hours_end = workingHoursEnd
        payload.is_available = isAvailable
      }

      if (role === 'patient' || role === 'user') {
        payload.date_of_birth = dateOfBirth
        payload.gender = gender
        payload.blood_group = bloodGroup
        payload.address = address
        payload.city = city
        payload.state = state
        payload.allergies = allergies
        payload.chronic_conditions = chronicConditions
        payload.emergency_contact_name = emergencyName
        payload.emergency_contact_phone = emergencyPhone
      }

      await apiClient.patch('/auth/profile', payload)
      toast.success('Account profile updated successfully!')
      if (refreshUser) refreshUser()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSavingProfile(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error("New passwords don't match")
      return
    }
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters long')
      return
    }

    setSavingPassword(true)
    try {
      await apiClient.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      toast.success('Password changed successfully!')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setSavingPassword(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-800 rounded-xl w-64" />
          <div className="h-64 bg-slate-900 rounded-2xl border border-slate-800" />
        </div>
      </div>
    )
  }

  const isDoctor = role === 'doctor'
  const isPatient = role === 'patient' || role === 'user'

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-4xl mx-auto">
      {/* ── Page Header ── */}
      <div className="border-b border-slate-800 pb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
              isDoctor
                ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20'
                : isPatient
                ? 'bg-teal-500/10 text-teal-300 border-teal-500/20'
                : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
            }`}>
              {role || 'User'} Profile
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Account Settings</h1>
          <p className="text-xs text-slate-400 mt-1">Manage your account information, clinical credentials, and security settings.</p>
        </div>
      </div>

      {/* ── Navigation Tabs ── */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'profile'
              ? isDoctor
                ? 'border-indigo-500 text-indigo-400'
                : 'border-teal-500 text-teal-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          {isDoctor ? <Stethoscope className="w-4 h-4" /> : <User className="w-4 h-4" />}
          {isDoctor ? 'Doctor Profile & Practice' : isPatient ? 'Personal & Medical Data' : 'Profile Details'}
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'security'
              ? isDoctor
                ? 'border-indigo-500 text-indigo-400'
                : 'border-teal-500 text-teal-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <KeyRound className="w-4 h-4" />
          Security & Password
        </button>
      </div>

      {/* ── Tab Content ── */}
      <AnimatePresence mode="wait">
        {activeTab === 'profile' && (
          <motion.form
            key="profile-tab"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={easeOutExpo}
            onSubmit={handleSaveProfile}
            className="space-y-6"
          >
            {/* Account Information Card */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 shadow-xl">
              <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <User className="w-4 h-4 text-teal-400" />
                Account Overview
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300">Full Name</label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="John Doe"
                    className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300">Email Address (Read-only)</label>
                  <input
                    type="email"
                    disabled
                    value={email}
                    className="w-full mt-1.5 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs text-slate-400 cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300">Phone Number</label>
                  <div className="relative mt-1.5">
                    <Phone className="w-3.5 h-3.5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full p-3 pl-9 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300">Account Role</label>
                  <input
                    type="text"
                    disabled
                    value={role.toUpperCase()}
                    className="w-full mt-1.5 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs text-slate-400 capitalize cursor-not-allowed font-semibold"
                  />
                </div>
              </div>
            </div>

            {/* Doctor Profile Card */}
            {isDoctor && (
              <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5 shadow-xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Stethoscope className="w-4 h-4 text-indigo-400" />
                    Clinical Practice & Availability
                  </h2>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Available for Appointments:</span>
                    <button
                      type="button"
                      onClick={() => setIsAvailable(!isAvailable)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        isAvailable ? 'bg-emerald-500' : 'bg-slate-700'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        isAvailable ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Medical Specialty</label>
                    <select
                      value={specialty}
                      onChange={(e) => setSpecialty(e.target.value)}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      {SPECIALTIES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">License Number (Read-only)</label>
                    <input
                      type="text"
                      disabled
                      value={licenseNumber}
                      className="w-full mt-1.5 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs text-slate-400 cursor-not-allowed font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Years of Experience</label>
                    <input
                      type="number"
                      min="0"
                      value={yearsOfExperience}
                      onChange={(e) => setYearsOfExperience(Number(e.target.value))}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Consultation Fee (₹)</label>
                    <input
                      type="number"
                      min="0"
                      step="10"
                      value={consultationFee}
                      onChange={(e) => setConsultationFee(Number(e.target.value))}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 mb-2 block">Available Days</label>
                  <div className="flex flex-wrap gap-2">
                    {DAYS.map((day) => (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleDay(day)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                          availableDays.includes(day)
                            ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300'
                            : 'border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-400'
                        }`}
                      >
                        {day}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Working Hours Start</label>
                    <input
                      type="time"
                      value={workingHoursStart}
                      onChange={(e) => setWorkingHoursStart(e.target.value)}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Working Hours End</label>
                    <input
                      type="time"
                      value={workingHoursEnd}
                      onChange={(e) => setWorkingHoursEnd(e.target.value)}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300">Professional Bio & Approach</label>
                  <textarea
                    rows={3}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="Brief description of your expertise, approach to patient care, and sub-specializations..."
                    className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                  />
                </div>
              </div>
            )}

            {/* Patient Profile Card */}
            {isPatient && (
              <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5 shadow-xl">
                <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 border-b border-slate-800 pb-3">
                  <Heart className="w-4 h-4 text-rose-400" />
                  Medical Demographics & Health Profile
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Gender</label>
                    <select
                      value={gender}
                      onChange={(e) => setGender(e.target.value)}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    >
                      <option value="">Select gender...</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                      <option value="Prefer not to say">Prefer not to say</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Date of Birth</label>
                    <input
                      type="date"
                      value={dateOfBirth}
                      onChange={(e) => setDateOfBirth(e.target.value)}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Blood Group</label>
                    <select
                      value={bloodGroup}
                      onChange={(e) => setBloodGroup(e.target.value)}
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500 font-semibold"
                    >
                      <option value="">Select blood group...</option>
                      <option value="A+">A+</option>
                      <option value="A-">A-</option>
                      <option value="B+">B+</option>
                      <option value="B-">B-</option>
                      <option value="O+">O+</option>
                      <option value="O-">O-</option>
                      <option value="AB+">AB+</option>
                      <option value="AB-">AB-</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Street Address</label>
                    <input
                      type="text"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="Flat / House No., Street"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">City</label>
                    <input
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      placeholder="e.g. Mumbai"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">State</label>
                    <input
                      type="text"
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      placeholder="e.g. Maharashtra"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Known Allergies</label>
                    <input
                      type="text"
                      value={allergies}
                      onChange={(e) => setAllergies(e.target.value)}
                      placeholder="e.g. Penicillin, Peanuts, Dust Mites"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Chronic Conditions</label>
                    <input
                      type="text"
                      value={chronicConditions}
                      onChange={(e) => setChronicConditions(e.target.value)}
                      placeholder="e.g. Hypertension, Asthma, Type 2 Diabetes"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Emergency Contact Name</label>
                    <input
                      type="text"
                      value={emergencyName}
                      onChange={(e) => setEmergencyName(e.target.value)}
                      placeholder="e.g. Mary Doe"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300">Emergency Contact Phone</label>
                    <input
                      type="tel"
                      value={emergencyPhone}
                      onChange={(e) => setEmergencyPhone(e.target.value)}
                      placeholder="+91 98765 00000"
                      className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Save Button */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={savingProfile}
                className={`px-6 py-3 rounded-xl text-white font-bold text-xs shadow-lg inline-flex items-center gap-2 transition-all disabled:opacity-50 ${
                  isDoctor
                    ? 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-900/30'
                    : 'bg-teal-600 hover:bg-teal-500 shadow-teal-900/30'
                }`}
              >
                {savingProfile ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save Account Profile
              </button>
            </div>
          </motion.form>
        )}

        {activeTab === 'security' && (
          <motion.form
            key="security-tab"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={easeOutExpo}
            onSubmit={handleChangePassword}
            className="space-y-6 max-w-xl"
          >
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 shadow-xl">
              <div className="border-b border-slate-800 pb-3">
                <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Lock className="w-4 h-4 text-amber-400" />
                  Change Password
                </h2>
                <p className="text-xs text-slate-400 mt-1">Ensure your account is using a long, random password to stay secure.</p>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Current Password</label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">New Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Confirm New Password</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat new password"
                  className="w-full mt-1.5 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={savingPassword}
                  className="w-full py-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-900/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                >
                  {savingPassword ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <KeyRound className="w-4 h-4" />
                  )}
                  Update Password
                </button>
              </div>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  )
}
