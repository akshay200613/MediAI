'use client'

import React from 'react'
import Link from 'next/link'
import { ShieldX, ArrowLeft } from 'lucide-react'

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 text-slate-100 font-sans">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 text-center shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center mx-auto mb-5">
          <ShieldX className="w-8 h-8" />
        </div>

        <h1 className="text-xl font-bold text-slate-100">Access Denied</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-2 leading-relaxed">
          You do not have the required RBAC permissions to access this role interface.
        </p>

        <div className="mt-8">
          <Link
            href="/login"
            className="w-full py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium inline-flex items-center justify-center gap-2 transition-colors shadow-lg shadow-teal-900/30"
          >
            <ArrowLeft className="w-4 h-4" />
            Return to Login
          </Link>
        </div>
      </div>
    </div>
  )
}
