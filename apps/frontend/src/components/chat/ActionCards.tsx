'use client'

import React, { useState } from 'react'
import { Calendar, Clock, User, CheckCircle, Activity, Info, XCircle, Loader2 } from 'lucide-react'

interface ActionCardsProps {
  actionData: any
  onAction: (message: string) => void
}

export const ActionCards: React.FC<ActionCardsProps> = ({ actionData, onAction }) => {
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)
  const [confirmationStatus, setConfirmationStatus] = useState<'idle' | 'confirming' | 'confirmed' | 'cancelled' | 'changing'>('idle')

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
            {actionData.slots?.map((slot: string) => {
              const isChosen = selectedSlot === slot
              const isOther = selectedSlot !== null && !isChosen
              return (
                <button
                  key={slot}
                  disabled={selectedSlot !== null}
                  onClick={() => {
                    setSelectedSlot(slot)
                    onAction(JSON.stringify({
                      __action: 'select_slot',
                      doctor: actionData.doctor,
                      doctor_id: actionData.doctor_id,
                      specialty: actionData.specialty || 'General Practice',
                      date: actionData.date,
                      selected_slot: slot,
                    }))
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    isChosen
                      ? 'bg-teal-600 text-white border-teal-500 shadow-md pointer-events-none'
                      : isOther
                      ? 'opacity-30 bg-slate-900 border-slate-800 text-slate-500 cursor-not-allowed'
                      : 'bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border-teal-500/30'
                  }`}
                >
                  {slot}
                </button>
              )
            })}
          </div>
          {(!actionData.slots || actionData.slots.length === 0) && (
            <div className="text-xs text-rose-400 mt-2">No slots available on this date.</div>
          )}
        </div>
      )

    case 'booking_confirmation':
      const isHandled = confirmationStatus !== 'idle'

      return (
        <div className={`border rounded-xl p-4 mt-2 max-w-sm transition-all ${
          isHandled
            ? 'bg-slate-900/90 border-slate-800 opacity-75'
            : 'bg-slate-800/80 border-slate-700'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-amber-400">
              <Info className="w-4 h-4" />
              <h4 className="font-semibold text-sm">Confirm Booking</h4>
            </div>
            {confirmationStatus === 'confirmed' && (
              <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-bold">
                ✓ Submitted
              </span>
            )}
            {confirmationStatus === 'cancelled' && (
              <span className="text-[10px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded-full font-bold">
                Cancelled
              </span>
            )}
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

          {isHandled ? (
            <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-center text-xs text-slate-400 font-medium">
              {confirmationStatus === 'confirming' || confirmationStatus === 'confirmed' ? (
                <div className="flex items-center justify-center gap-2 text-teal-300">
                  <CheckCircle className="w-4 h-4 text-teal-400" />
                  <span>Booking confirmed. Processing in progress...</span>
                </div>
              ) : (
                <span>Option completed.</span>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setConfirmationStatus('confirmed')
                  onAction(JSON.stringify({
                    __action: 'confirm_booking',
                    doctor: actionData.doctor,
                    doctor_id: actionData.doctor_id,
                    specialty: actionData.specialty,
                    date: actionData.date,
                    time: actionData.time,
                    type: actionData.type,
                    reason: actionData.reason,
                  }))
                }}
                className="px-3 py-2 rounded-lg bg-teal-500 hover:bg-teal-600 text-white font-medium text-xs transition-colors flex justify-center items-center gap-1 cursor-pointer shadow-md"
              >
                <CheckCircle className="w-3.5 h-3.5" /> Confirm
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirmationStatus('cancelled')
                  onAction(JSON.stringify({
                    __action: 'cancel_booking_flow'
                  }))
                }}
                className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirmationStatus('changing')
                  onAction("Can we check another available date or time?")
                }}
                className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium text-xs transition-colors col-span-2 cursor-pointer"
              >
                Change Time
              </button>
            </div>
          )}
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
      const handleCompleteProfileRedirect = () => {
        try {
          const { useChatStore } = require('@/lib/hooks/useChatStore')
          const activeId = useChatStore.getState().activeSessionId
          if (activeId) {
            sessionStorage.setItem('pending_booking_session_id', activeId)
            sessionStorage.setItem('pending_booking_state', JSON.stringify({
              missing_fields: actionData.missing_fields,
              message: actionData.message,
              timestamp: new Date().toISOString()
            }))
          }
        } catch {}
        window.location.href = `/patient/profile?return_to=chat&session_id=${sessionStorage.getItem('pending_booking_session_id') || ''}`
      }

      return (
        <div className="bg-indigo-950/40 border border-indigo-500/40 rounded-xl p-4 mt-2 max-w-sm space-y-3">
          <div className="flex items-center gap-2 text-indigo-300 font-semibold text-xs">
            <Activity className="w-4 h-4 text-indigo-400 shrink-0" />
            <span>Mandatory Medical Profile Required</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {actionData.message || 'Please complete your mandatory medical details (Phone Number, Gender, Date of Birth) before finalizing your booking.'}
            {actionData.missing_fields && actionData.missing_fields.length > 0 && (
              <span className="block mt-1 font-mono text-[11px] text-amber-300">
                Missing: {actionData.missing_fields.join(', ')}
              </span>
            )}
          </p>
          <div className="flex flex-col gap-2 pt-1">
            <button
              onClick={handleCompleteProfileRedirect}
              className="w-full px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-950/30 transition-all flex items-center justify-center gap-1.5"
            >
              <User className="w-3.5 h-3.5" />
              Complete Profile (Full Page)
            </button>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onAction("I will provide my missing details directly here in chat.")}
                className="px-2.5 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 font-medium text-[11px] transition-colors"
              >
                Provide details in chat
              </button>
              <button
                onClick={() => onAction("I'll do it later, let's continue with booking.")}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-[11px] transition-colors"
              >
                Later
              </button>
            </div>
          </div>
        </div>
      )

    default:
      return null
  }
}
