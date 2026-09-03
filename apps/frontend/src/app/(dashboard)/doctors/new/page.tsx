'use client'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Save, Upload } from 'lucide-react'
import { doctorsApi } from '@/lib/api/doctors'
import toast from 'react-hot-toast'

const schema = z.object({
  first_name: z.string().min(1, 'Required'),
  last_name: z.string().min(1, 'Required'),
  email: z.string().email('Invalid email'),
  phone: z.string().min(7, 'Invalid phone'),
  specialty: z.string().min(2, 'Required'),
  license_number: z.string().min(3, 'Required'),
  years_of_experience: z.coerce.number().min(0).max(60),
  consultation_fee: z.coerce.number().min(0),
  bio: z.string().optional(),
  available_days: z.string().optional(),
  working_hours_start: z.string().optional(),
  working_hours_start: z.string().optional(),
  working_hours_end: z.string().optional(),
  profile_image_url: z.string().optional(),
})
type FormData = z.infer<typeof schema> & { profileImageFile?: FileList | null }

const SPECIALTIES = ['General Practice','Cardiology','Dermatology','Endocrinology','Gastroenterology','Neurology','Orthopedics','Pediatrics','Psychiatry','Radiology','Surgery','Urology','Physiology']

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="form-label">{label}</label>
      {children}
      {error && <p className="mt-1 text-red-400 text-xs">{error}</p>}
    </div>
  )
}

export default function NewDoctorPage() {
  const router = useRouter()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { years_of_experience: 0, consultation_fee: 100 },
  })

  const onSubmit = async (data: FormData) => {
    try {
      if (data.profileImageFile && data.profileImageFile.length > 0) {
        const uploadRes = await doctorsApi.uploadImage(data.profileImageFile[0])
        data.profile_image_url = uploadRes.url
      }
      delete data.profileImageFile // Remove it before sending to backend

      await doctorsApi.create(data)
      toast.success('Doctor added successfully')
      router.push('/doctors')
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to add doctor')
    }
  }

  return (
    <div className="max-w-3xl space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="btn-secondary py-2 px-3"><ArrowLeft className="w-4 h-4" /></button>
        <div>
          <h1 className="text-2xl font-bold text-white">Add Doctor</h1>
          <p className="text-slate-400 text-sm mt-0.5">Register a new doctor to the clinic</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="glass-card p-6 space-y-4">
          <h2 className="text-base font-semibold text-white border-b border-white/5 pb-3">Personal Details</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="First Name *" error={errors.first_name?.message}>
              <input {...register('first_name')} className="input-field" placeholder="Jane" />
            </Field>
            <Field label="Last Name *" error={errors.last_name?.message}>
              <input {...register('last_name')} className="input-field" placeholder="Smith" />
            </Field>
            <Field label="Email *" error={errors.email?.message}>
              <input {...register('email')} type="email" className="input-field" placeholder="dr.smith@clinic.com" />
            </Field>
            <Field label="Phone *" error={errors.phone?.message}>
              <input {...register('phone')} className="input-field" placeholder="+1 234 567 8900" />
            </Field>
          </div>
          <Field label="Profile Photo (Optional)">
            <input 
              type="file" 
              accept="image/*" 
              className="input-field cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-500/10 file:text-indigo-400 hover:file:bg-indigo-500/20"
              {...register('profileImageFile')} 
            />
          </Field>
        </div>

        <div className="glass-card p-6 space-y-4">
          <h2 className="text-base font-semibold text-white border-b border-white/5 pb-3">Professional Details</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Specialty *" error={errors.specialty?.message}>
              <select {...register('specialty')} className="input-field">
                <option value="">Select specialty</option>
                {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="License Number *" error={errors.license_number?.message}>
              <input {...register('license_number')} className="input-field" placeholder="LIC-12345" />
            </Field>
            <Field label="Years of Experience" error={errors.years_of_experience?.message}>
              <input {...register('years_of_experience')} type="number" min={0} className="input-field" />
            </Field>
            <Field label="Consultation Fee (₹)" error={errors.consultation_fee?.message}>
              <input {...register('consultation_fee')} type="number" min={0} step={0.01} className="input-field" />
            </Field>
            <Field label="Working Hours Start">
              <input {...register('working_hours_start')} type="time" className="input-field" defaultValue="09:00" />
            </Field>
            <Field label="Working Hours End">
              <input {...register('working_hours_end')} type="time" className="input-field" defaultValue="17:00" />
            </Field>
            <Field label="Available Days" error={errors.available_days?.message}>
              <input {...register('available_days')} className="input-field" placeholder="Mon,Tue,Wed,Thu,Fri" />
            </Field>
          </div>
          <Field label="Bio / Description">
            <textarea {...register('bio')} className="input-field resize-none" rows={3} placeholder="Brief description about the doctor..." />
          </Field>
        </div>

        <div className="flex gap-3">
          <button type="button" onClick={() => router.back()} className="btn-secondary">Cancel</button>
          <button type="submit" disabled={isSubmitting} className="btn-primary">
            {isSubmitting ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Saving...</> : <><Save className="w-4 h-4" />Add Doctor</>}
          </button>
        </div>
      </form>
    </div>
  )
}
