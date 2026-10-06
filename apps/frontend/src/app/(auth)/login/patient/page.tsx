'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function PatientLoginRedirect() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/login')
  }, [router])

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-100 font-sans">
      <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}
