'use client'

import React, { useState } from 'react'
import { Clock, Calendar, CheckCircle2 } from 'lucide-react'

export default function DoctorSchedulePage() {
  const [startHour, setStartHour] = useState('09:00')
  const [endHour, setEndHour] = useState('17:00')
  const [savedNotice, setSavedNotice] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSavedNotice(true)
    setTimeout(() => setSavedNotice(false), 3000)
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans max-w-2xl">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Availability & Schedule</h1>
        <p className="text-xs text-slate-400 mt-1">Configure your working hours and consultation availability.</p>
      </div>

      {savedNotice && (
        <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-teal-400" />
          <span>Working hours saved successfully!</span>
        </div>
      )}

      <form onSubmit={handleSave} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-slate-300">Shift Start Time</label>
            <input
              type="time"
              value={startHour}
              onChange={(e) => setStartHour(e.target.value)}
              className="w-full mt-1 p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500/50"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-300">Shift End Time</label>
            <input
              type="time"
              value={endHour}
              onChange={(e) => setEndHour(e.target.value)}
              className="w-full mt-1 p-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-teal-500/50"
            />
          </div>
        </div>

        <button
          type="submit"
          className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-lg shadow-teal-900/20 transition-colors"
        >
          Save Schedule Settings
        </button>
      </form>
    </div>
  )
}
