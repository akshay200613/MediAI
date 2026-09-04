import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  })
}

export function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function getStatusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'badge-blue',
    confirmed: 'badge-green',
    in_progress: 'badge-yellow',
    completed: 'badge-green',
    cancelled: 'badge-red',
    no_show: 'badge-gray',
    active: 'badge-green',
    inactive: 'badge-red',
  }
  return map[status] ?? 'badge-gray'
}

export function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}

export function extractErrorMessage(err: any): string {
  if (!err) return 'An unexpected error occurred'
  
  // Check structured error payload from backend: err.response?.data?.error
  const apiError = err?.response?.data?.error
  if (apiError) {
    if (typeof apiError === 'string') return apiError
    if (apiError.message && typeof apiError.message === 'string') {
      if (apiError.details && Array.isArray(apiError.details) && apiError.details.length > 0) {
        const detailsStr = apiError.details
          .map((d: any) => d.msg || (d.loc ? `${d.loc.join('.')}: ${d.msg}` : JSON.stringify(d)))
          .join(', ')
        return `${apiError.message}: ${detailsStr}`
      }
      return apiError.message
    }
  }

  // Check direct detail field
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => (typeof d === 'string' ? d : d.msg || d.detail || JSON.stringify(d))).join(', ')
  }
  if (typeof detail === 'object' && detail !== null) {
    return detail.msg || detail.detail || detail.message || JSON.stringify(detail)
  }

  // Check direct message field
  const msg = err?.response?.data?.message
  if (typeof msg === 'string') return msg

  // Check if response data itself is a string
  if (typeof err?.response?.data === 'string' && err.response.data.trim()) {
    return err.response.data
  }

  if (typeof err.message === 'string') return err.message
  return String(err)
}

