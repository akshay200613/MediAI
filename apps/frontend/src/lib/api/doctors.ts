import apiClient from './client'
import type { ApiResponse, PaginatedResponse, Doctor } from '@/types'

export const doctorsApi = {
  list: async (page = 1, pageSize = 20, search?: string, availableOnly?: boolean): Promise<PaginatedResponse<Doctor>> => {
    const params: Record<string, unknown> = { page, page_size: pageSize }
    if (search) params.search = search
    if (availableOnly) params.available_only = true
    const res = await apiClient.get('/medai/doctors', { params })
    return res.data
  },

  get: async (id: string): Promise<ApiResponse<Doctor>> => {
    const res = await apiClient.get(`/medai/doctors/${id}`)
    return res.data
  },

  create: async (data: Partial<Doctor>): Promise<ApiResponse<Doctor>> => {
    const res = await apiClient.post('/medai/doctors', data)
    return res.data
  },

  update: async (id: string, data: Partial<Doctor>): Promise<ApiResponse<Doctor>> => {
    const res = await apiClient.patch(`/medai/doctors/${id}`, data)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/medai/doctors/${id}`)
  },

  uploadImage: async (file: File): Promise<{ url: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await apiClient.post('/medai/uploads/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return res.data
  },
}
