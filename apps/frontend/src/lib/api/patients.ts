import apiClient from './client'
import type { ApiResponse, PaginatedResponse, Patient } from '@/types'

export const patientsApi = {
  list: async (page = 1, pageSize = 20, search?: string): Promise<PaginatedResponse<Patient>> => {
    const params: Record<string, unknown> = { page, page_size: pageSize }
    if (search) params.search = search
    const res = await apiClient.get('/medai/patients', { params })
    return res.data
  },

  get: async (id: string): Promise<ApiResponse<Patient>> => {
    const res = await apiClient.get(`/medai/patients/${id}`)
    return res.data
  },

  create: async (data: Partial<Patient>): Promise<ApiResponse<Patient>> => {
    const res = await apiClient.post('/medai/patients', data)
    return res.data
  },

  update: async (id: string, data: Partial<Patient>): Promise<ApiResponse<Patient>> => {
    const res = await apiClient.patch(`/medai/patients/${id}`, data)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/medai/patients/${id}`)
  },
}
