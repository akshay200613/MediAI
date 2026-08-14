'use client'

import React from 'react'
import Link from 'next/link'
import { Clock, ShieldAlert, ArrowLeft, CheckCircle2 } from 'lucide-react'

export default function PendingApprovalPage() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 text-slate-100 font-sans">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 text-center shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center mx-auto mb-5 shadow-lg shadow-amber-500/5">
          <Clock className="w-8 h-8 animate-pulse" />
        </div>

        <h1 className="text-xl font-bold text-slate-100">Doctor Verification Pending</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-2 leading-relaxed">
          Your physician account registration has been received and is awaiting license verification by a MediAI System Administrator.
        </p>

        <div className="mt-6 p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-left text-xs text-slate-300 space-y-2">
          <div className="flex items-center gap-2 text-teal-400 font-medium">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-teal-400" />
            <span>Google OAuth Authenticated</span>
          </div>
          <div className="flex items-center gap-2 text-amber-400 font-medium">
            <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
            <span>Medical License Review In-Progress</span>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-2">
          <Link
            href="/login"
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 inline-flex items-center justify-center gap-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Return to Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
