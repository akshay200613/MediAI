'use client'

import React from 'react'
import { Calendar, Clock, User, CheckCircle, Activity, Info, XCircle } from 'lucide-react'

interface ActionCardsProps {
  actionData: any
  onAction: (message: string) => void
}

export const ActionCards: React.FC<ActionCardsProps> = ({ actionData, onAction }) => {
  if (!actionData || !actionData.action) return null

  switch (actionData.action) {
    case 'available_slots':
      return (
        <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 mt-2 max-w-sm">
          <div className="flex items-center gap-2 mb-3 text-teal-400">
            <Calendar className="w-4 h-4" />
            <h4 className="font-semibold text-sm">Available Slots</h4>
          </div>
          <div className="text-xs text-slate-300 mb-3">
            <span className="font-medium text-slate-200">{actionData.doctor}</span> - {actionData.date}
          </div>
          <div className="flex flex-wrap gap-2">
            {actionData.slots?.map((slot: string) => (
              <button
                key={slot}
                onClick={() => onAction(`I'd like to book ${slot} on ${actionData.date}`)}
                className="px-3 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 text-xs border border-teal-500/30 transition-colors"
              >
                {slot}
              </button>
            ))}
          </div>
          {(!actionData.slots || actionData.slots.length === 0) && (
            <div className="text-xs text-rose-400 mt-2">No slots available on this date.</div>
          )}
        </div>
      )

    case 'booking_confirmation':
      return (
        <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 mt-2 max-w-sm">
          <div className="flex items-center gap-2 mb-3 text-amber-400">
            <Info className="w-4 h-4" />
            <h4 className="font-semibold text-sm">Confirm Booking</h4>
          </div>
          <div className="space-y-2 text-xs text-slate-300 mb-4 bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
            <div className="flex justify-between">
              <span className="text-slate-400">Doctor</span>
              <span className="font-medium text-slate-200">{actionData.doctor} ({actionData.specialty})</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Date</span>
              <span className="font-medium text-slate-200">{actionData.date}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Time</span>
              <span className="font-medium text-slate-200">{actionData.time}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Type</span>
              <span className="font-medium text-slate-200">{actionData.type}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => onAction("Yes, confirm booking.")}
              className="px-3 py-2 rounded-lg bg-teal-500 hover:bg-teal-600 text-white font-medium text-xs transition-colors flex justify-center items-center gap-1"
            >
              <CheckCircle className="w-3.5 h-3.5" /> Confirm
            </button>
            <button
              onClick={() => onAction("No, cancel this.")}
              className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => onAction("Can we change the time?")}
              className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium text-xs transition-colors col-span-2"
            >
              Change Time
            </button>
          </div>
        </div>
      )

    case 'booking_success':
      return (
        <div className="bg-teal-950/40 border border-teal-500/30 rounded-xl p-4 mt-2 max-w-sm">
          <div className="flex items-center gap-2 mb-2 text-teal-400">
            <CheckCircle className="w-5 h-5" />
            <h4 className="font-semibold text-sm">Booking Successful!</h4>
          </div>
          <div className="text-xs text-teal-100/70 mb-3">
            Your appointment has been confirmed.
          </div>
          <div className="space-y-1.5 text-xs bg-slate-900/60 p-3 rounded-lg border border-teal-900/50">
            <div className="flex items-center gap-2 text-slate-300">
              <User className="w-3.5 h-3.5 text-slate-400" />
              <span>{actionData.doctor}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>{actionData.date}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>{actionData.time}</span>
            </div>
          </div>
        </div>
      )

    case 'complete_profile':
      return (
        <div className="bg-indigo-950/30 border border-indigo-500/30 rounded-xl p-4 mt-2 max-w-sm">
          <div className="flex items-center gap-2 mb-2 text-indigo-400">
            <Activity className="w-4 h-4" />
            <h4 className="font-semibold text-sm">Profile Incomplete</h4>
          </div>
          <p className="text-xs text-indigo-200/70 mb-3">
            Please complete your profile for a better experience. Missing: {actionData.missing_fields?.join(', ')}.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => window.location.href = '/patient/profile'}
              className="px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-xs transition-colors"
            >
              Complete Profile
            </button>
            <button
              onClick={() => onAction("I'll do it later, let's continue with booking.")}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors"
            >
              Later
            </button>
          </div>
        </div>
      )

    default:
      return null
  }
}
