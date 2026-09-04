import apiClient from './client'
import type { ApiResponse, PaginatedResponse, Appointment } from '@/types'

export const appointmentsApi = {
  list: async (page = 1, pageSize = 20, upcomingOnly?: boolean, patientId?: string): Promise<PaginatedResponse<Appointment>> => {
    const params: Record<string, unknown> = { page, page_size: pageSize }
    if (upcomingOnly) params.upcoming_only = true
    if (patientId) params.patient_id = patientId
    const res = await apiClient.get('/medai/appointments', { params })
    return res.data
  },

  get: async (id: string): Promise<ApiResponse<Appointment>> => {
    const res = await apiClient.get(`/medai/appointments/${id}`)
    return res.data
  },

  create: async (data: {
    patient_id: string
    doctor_id: string
    appointment_type?: string
    scheduled_at: string
    duration_minutes?: number
    reason?: string
  }): Promise<ApiResponse<Appointment>> => {
    const res = await apiClient.post('/medai/appointments', data)
    return res.data
  },

  update: async (id: string, data: Partial<Appointment>): Promise<ApiResponse<Appointment>> => {
    const res = await apiClient.patch(`/medai/appointments/${id}`, data)
    return res.data
  },

  cancel: async (id: string): Promise<ApiResponse<Appointment>> => {
    const res = await apiClient.post(`/medai/appointments/${id}/cancel`)
    return res.data
  },
}
