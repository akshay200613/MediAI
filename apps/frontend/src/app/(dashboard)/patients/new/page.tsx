'use client'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Save } from 'lucide-react'
import { patientsApi } from '@/lib/api/patients'
import toast from 'react-hot-toast'

const schema = z.object({
  first_name: z.string().min(1, 'Required'),
  last_name: z.string().min(1, 'Required'),
  phone: z.string().min(7, 'Invalid phone'),
  email: z.string().email().optional().or(z.literal('')),
  date_of_birth: z.string().optional(),
  gender: z.enum(['male', 'female', 'other', '']).optional(),
  blood_group: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  allergies: z.string().optional(),
  chronic_conditions: z.string().optional(),
  emergency_contact_name: z.string().optional(),
  emergency_contact_phone: z.string().optional(),
})
type FormData = z.infer<typeof schema>

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="form-label">{label}</label>
      {children}
      {error && <p className="mt-1 text-red-400 text-xs">{error}</p>}
    </div>
  )
}

export default function NewPatientPage() {
  const router = useRouter()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      const payload = { ...data, email: data.email || undefined, gender: data.gender || undefined }
      await patientsApi.create(payload)
      toast.success('Patient registered successfully')
      router.push('/patients')
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create patient')
    }
  }

  return (
    <div className="max-w-3xl space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="btn-secondary py-2 px-3"><ArrowLeft className="w-4 h-4" /></button>
        <div>
          <h1 className="text-2xl font-bold text-white">Register Patient</h1>
          <p className="text-slate-400 text-sm mt-0.5">Add a new patient to the system</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Personal Info */}
        <div className="glass-card p-6 space-y-4">
          <h2 className="text-base font-semibold text-white border-b border-white/5 pb-3">Personal Information</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="First Name *" error={errors.first_name?.message}>
              <input {...register('first_name')} className="input-field" placeholder="John" />
            </Field>
            <Field label="Last Name *" error={errors.last_name?.message}>
              <input {...register('last_name')} className="input-field" placeholder="Doe" />
            </Field>
            <Field label="Phone *" error={errors.phone?.message}>
              <input {...register('phone')} className="input-field" placeholder="+1 234 567 8900" />
            </Field>
            <Field label="Email" error={errors.email?.message}>
              <input {...register('email')} type="email" className="input-field" placeholder="patient@email.com" />
            </Field>
            <Field label="Date of Birth">
              <input {...register('date_of_birth')} type="date" className="input-field" />
            </Field>
            <Field label="Gender">
              <select {...register('gender')} className="input-field">
                <option value="">Select gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </Field>
            <Field label="Blood Group">
              <select {...register('blood_group')} className="input-field">
                <option value="">Select blood group</option>
                {['A+','A-','B+','B-','O+','O-','AB+','AB-'].map(bg => <option key={bg} value={bg}>{bg}</option>)}
              </select>
            </Field>
          </div>
        </div>

        {/* Address */}
        <div className="glass-card p-6 space-y-4">
          <h2 className="text-base font-semibold text-white border-b border-white/5 pb-3">Address</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Address" error={errors.address?.message}>
              <input {...register('address')} className="input-field" placeholder="123 Main St" />
            </Field>
            <Field label="City">
              <input {...register('city')} className="input-field" placeholder="New York" />
            </Field>
            <Field label="State">
              <input {...register('state')} className="input-field" placeholder="NY" />
            </Field>
          </div>
        </div>

        {/* Medical Info */}
        <div className="glass-card p-6 space-y-4">
          <h2 className="text-base font-semibold text-white border-b border-white/5 pb-3">Medical Information</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Known Allergies">
              <textarea {...register('allergies')} className="input-field resize-none" rows={2} placeholder="Penicillin, Peanuts..." />
            </Field>
            <Field label="Chronic Conditions">
              <textarea {...register('chronic_conditions')} className="input-field resize-none" rows={2} placeholder="Diabetes, Hypertension..." />
            </Field>
            <Field label="Emergency Contact Name">
              <input {...register('emergency_contact_name')} className="input-field" placeholder="Jane Doe" />
            </Field>
            <Field label="Emergency Contact Phone">
              <input {...register('emergency_contact_phone')} className="input-field" placeholder="+1 234 567 8900" />
            </Field>
          </div>
        </div>

        <div className="flex gap-3">
          <button type="button" onClick={() => router.back()} className="btn-secondary">Cancel</button>
          <button type="submit" disabled={isSubmitting} className="btn-primary">
            {isSubmitting ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Saving...</> : <><Save className="w-4 h-4" />Register Patient</>}
          </button>
        </div>
      </form>
    </div>
  )
}
