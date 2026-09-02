/** Global TypeScript types for MedAI */

export interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  success: boolean
  message: string
  data: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface User {
  id: string
  email: string
  full_name: string
  role: string
  domain: string
  is_active: boolean
  is_verified: boolean
  avatar_url?: string
}

export interface Patient {
  id: string
  first_name: string
  last_name: string
  full_name: string
  email?: string
  phone: string
  date_of_birth?: string
  gender?: string
  blood_group?: string
  address?: string
  city?: string
  state?: string
  allergies?: string
  chronic_conditions?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface Doctor {
  id: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  specialty: string
  license_number: string
  years_of_experience: number
  bio?: string
  consultation_fee: number
  available_days?: string
  working_hours_start?: string
  working_hours_end?: string
  is_available: boolean
  profile_image_url?: string | null
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface Appointment {
  id: string
  patient_id: string
  doctor_id: string
  appointment_type: string
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show'
  scheduled_at: string
  duration_minutes: number
  reason?: string
  notes?: string
  ai_triage_summary?: string
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: RAGSource[]
  timestamp: Date
}

export interface RAGSource {
  text: string
  score: number
  title?: string
  category?: string
}

export interface DashboardStats {
  total_patients: number
  total_doctors: number
  today_appointments: number
  upcoming_appointments: number
}
