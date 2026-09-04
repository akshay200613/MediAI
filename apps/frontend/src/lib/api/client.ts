import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'

const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    if (hostname === 'localhost') return 'http://127.0.0.1:8000'
    return `http://${hostname}:8000`
  }
  return 'http://127.0.0.1:8000'
}

const API_BASE_URL = getApiBaseUrl()

const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Request interceptor – attach tab-isolated JWT token from sessionStorage
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = sessionStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor – handle 401 token refresh in tab-isolated sessionStorage
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = typeof window !== 'undefined' ? sessionStorage.getItem('refresh_token') : null

      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })
          const { access_token, refresh_token } = res.data.data
          if (typeof window !== 'undefined') {
            sessionStorage.setItem('access_token', access_token)
            sessionStorage.setItem('refresh_token', refresh_token)
          }
          original.headers.Authorization = `Bearer ${access_token}`
          return apiClient(original)
        } catch {
          if (typeof window !== 'undefined') {
            sessionStorage.removeItem('access_token')
            sessionStorage.removeItem('refresh_token')
            sessionStorage.removeItem('user')
            window.location.href = '/login'
          }
        }
      } else if (typeof window !== 'undefined') {
        sessionStorage.removeItem('access_token')
        sessionStorage.removeItem('refresh_token')
        sessionStorage.removeItem('user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
