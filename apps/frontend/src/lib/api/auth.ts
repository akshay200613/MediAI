import apiClient from './client'
import type { ApiResponse, TokenResponse, User } from '@/types'

export const authApi = {
  login: async (email: string, password: string): Promise<ApiResponse<TokenResponse>> => {
    const res = await apiClient.post('/auth/login', { email, password })
    return res.data
  },

  register: async (email: string, password: string, full_name: string): Promise<ApiResponse<{ id: string; email: string }>> => {
    const res = await apiClient.post('/auth/register', { email, password, full_name })
    return res.data
  },

  refresh: async (refresh_token: string): Promise<ApiResponse<TokenResponse>> => {
    const res = await apiClient.post('/auth/refresh', { refresh_token })
    return res.data
  },

  registerDoctor: async (data: {
    email: string
    password: string
    full_name: string
    phone: string
    specialty: string
    license_number: string
    years_of_experience: number
    bio?: string
    consultation_fee?: number
    available_days?: string
    working_hours_start?: string
    working_hours_end?: string
  }): Promise<ApiResponse<{ id: string; email: string; doctor_id: string; status: string }>> => {
    const res = await apiClient.post('/auth/register-doctor', data)
    return res.data
  },
}
