'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth/context'

export default function HomePage() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login')
      } else if (user?.role === 'admin' || user?.role === 'super_admin') {
        router.replace('/admin')
      } else if (user?.role === 'doctor') {
        router.replace(user.is_verified ? '/doctor' : '/pending-approval')
      } else if (user?.role === 'patient' || user?.role === 'user') {
        router.replace('/patient')
      } else {
        router.replace('/dashboard')
      }
    }
  }, [isAuthenticated, isLoading, user, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 font-sans">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-xs">Loading MediAI Clinical Operating System...</p>
      </div>
    </div>
  )
}
