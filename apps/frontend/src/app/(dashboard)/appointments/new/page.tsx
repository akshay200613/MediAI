'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function AppointmentsNewRedirectPage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/patient/book')
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 font-sans">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-xs">Redirecting to appointment booking portal...</p>
      </div>
    </div>
  )
}
