'use client'
import { useEffect, useState, use } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Edit, Phone, Mail, MapPin, Heart, AlertTriangle, Calendar, Bot } from 'lucide-react'
import { patientsApi } from '@/lib/api/patients'
import { formatDate } from '@/lib/utils'
import type { Patient } from '@/types'
import Link from 'next/link'
import toast from 'react-hot-toast'

export default function PatientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [patient, setPatient] = useState<Patient | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    patientsApi.get(id).then(r => setPatient(r.data)).catch(() => toast.error('Patient not found')).finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="space-y-4 animate-pulse">
      <div className="shimmer h-10 w-40 rounded-xl" />
      <div className="shimmer h-64 rounded-2xl" />
    </div>
  )

  if (!patient) return (
    <div className="text-center py-20">
      <p className="text-slate-400">Patient not found.</p>
      <button onClick={() => router.push('/patients')} className="btn-primary mt-4">Back to Patients</button>
    </div>
  )

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in">
      {/* Back + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="btn-secondary py-2 px-3"><ArrowLeft className="w-4 h-4" /></button>
          <h1 className="text-2xl font-bold text-white">{patient.full_name}</h1>
        </div>
        <div className="flex gap-2">
          <Link href={`/ai-chat?patient_id=${patient.id}`} className="btn-secondary py-2 px-4 text-sm">
            <Bot className="w-4 h-4" /> AI Consult
          </Link>
          <Link href={`/patient/book?patient_id=${patient.id}`} className="btn-secondary py-2 px-4 text-sm">
            <Calendar className="w-4 h-4" /> Book Appointment
          </Link>
        </div>
      </div>

      {/* Profile card */}
      <div className="glass-card p-6">
        <div className="flex items-start gap-6">
          <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 text-2xl font-bold text-white flex-shrink-0">
            {patient.first_name[0]}{patient.last_name[0]}
          </div>
          <div className="flex-1 grid grid-cols-2 md:grid-cols-3 gap-4">
            {patient.phone && <div className="flex items-center gap-2 text-sm"><Phone className="w-4 h-4 text-slate-500" /><span className="text-slate-300">{patient.phone}</span></div>}
            {patient.email && <div className="flex items-center gap-2 text-sm"><Mail className="w-4 h-4 text-slate-500" /><span className="text-slate-300">{patient.email}</span></div>}
            {patient.city && <div className="flex items-center gap-2 text-sm"><MapPin className="w-4 h-4 text-slate-500" /><span className="text-slate-300">{patient.city}</span></div>}
            {patient.date_of_birth && <div><p className="text-xs text-slate-500">Date of Birth</p><p className="text-slate-200 text-sm">{formatDate(patient.date_of_birth)}</p></div>}
            {patient.gender && <div><p className="text-xs text-slate-500">Gender</p><p className="text-slate-200 text-sm capitalize">{patient.gender}</p></div>}
            {patient.blood_group && (
              <div className="flex items-center gap-2">
                <Heart className="w-4 h-4 text-red-400" />
                <span className="badge-red">{patient.blood_group}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Medical info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {patient.allergies && (
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="font-semibold text-white">Known Allergies</h3>
            </div>
            <p className="text-slate-300 text-sm">{patient.allergies}</p>
          </div>
        )}
        {patient.chronic_conditions && (
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-3">
              <Heart className="w-4 h-4 text-red-400" />
              <h3 className="font-semibold text-white">Chronic Conditions</h3>
            </div>
            <p className="text-slate-300 text-sm">{patient.chronic_conditions}</p>
          </div>
        )}
        {patient.emergency_contact_name && (
          <div className="glass-card p-5">
            <h3 className="font-semibold text-white mb-3">Emergency Contact</h3>
            <p className="text-slate-300 text-sm">{patient.emergency_contact_name}</p>
            <p className="text-slate-400 text-xs mt-1">{patient.emergency_contact_phone}</p>
          </div>
        )}
        <div className="glass-card p-5">
          <h3 className="font-semibold text-white mb-3">Record Info</h3>
          <p className="text-xs text-slate-400">Registered: {formatDate(patient.created_at)}</p>
          <p className="text-xs text-slate-400 mt-1">Last updated: {formatDate(patient.updated_at)}</p>
          <p className="text-xs text-slate-500 mt-1 font-mono">ID: {patient.id.slice(0,8)}...</p>
        </div>
      </div>
    </div>
  )
}
