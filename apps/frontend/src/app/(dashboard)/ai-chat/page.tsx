'use client'

import { useEffect, useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import { useChatStore } from '@/lib/hooks/useChatStore'
import { useAuth } from '@/lib/auth/context'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { ChatMessages } from '@/components/chat/ChatMessages'
import { ChatInput } from '@/components/chat/ChatInput'
import { ChatEmptyState } from '@/components/chat/ChatEmptyState'
import { pageTransition } from '@/lib/motion'

export default function AIChatPage() {
  const router = useRouter()
  const { user } = useAuth()
  const searchParams = useSearchParams()
  const collectProfile = searchParams.get('collect_profile') === 'true'
  const {
    sessions,
    activeSessionId,
    isGenerating,
    sendMessage,
  } = useChatStore()

  // Derive a safe display name — never expose raw email
  const displayName = useMemo(() => {
    const name = user?.full_name || ''
    if (!name) return 'User'
    if (name.includes('@')) {
      const part = name.split('@')[0]
      return part.charAt(0).toUpperCase() + part.slice(1)
    }
    return name
  }, [user])

  const firstName = useMemo(() => {
    const name = user?.full_name || ''
    if (!name || name.includes('@')) return ''
    return name.trim().split(' ')[0]
  }, [user])

  const activeSession = sessions.find((s) => s.id === activeSessionId)
  const messages = activeSession?.messages || []

  // Load persistent sessions on mount when user is authenticated
  useEffect(() => {
    if (user) {
      useChatStore.getState().fetchSessions()
    }
  }, [user])

  // Handle Booking Resumption after Profile Completion
  useEffect(() => {
    if (!user) return

    const resumeSessionId = searchParams.get('resume_session') || (typeof window !== 'undefined' ? sessionStorage.getItem('pending_booking_session_id') : null)

    if (resumeSessionId) {
      // Clear pending storage keys
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('pending_booking_session_id')
        sessionStorage.removeItem('pending_booking_state')
      }
      
      // Select the active session and send seamless resumption message
      useChatStore.getState().selectSession(resumeSessionId).then(() => {
        setTimeout(() => {
          sendMessage("Welcome back! My profile has been updated. Let's continue booking my appointment.")
        }, 500)
      })
      return
    }

    // Default welcoming message personalized with user's actual account name
    if (sessions.length === 0 || !activeSessionId) {
      const name = firstName || displayName
      const sessionId = useChatStore.getState().createSession()
      
      const welcomeMsg = collectProfile
        ? `Hey ${name}! Let's get your medical profile completed so you can book your consultation. What is your Date of Birth (YYYY-MM-DD) and Gender?`
        : `Hey ${name}! How can I help you with medical questions or appointment booking today?`

      useChatStore.setState((state) => ({
        sessions: state.sessions.map((s) => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: [
                {
                  id: `msg-welcome-${Date.now()}`,
                  role: 'assistant',
                  content: welcomeMsg,
                  timestamp: new Date().toISOString(),
                },
              ],
            }
          }
          return s
        }),
      }))
    }
  }, [user, sessions.length, activeSessionId, collectProfile, firstName, displayName, searchParams])

  // Global shortcut: Ctrl+N / Cmd+N for new consultation session
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n') {
        e.preventDefault()
        useChatStore.getState().createSession()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <motion.div
      variants={pageTransition}
      initial="initial"
      animate="animate"
      exit="exit"
      className="w-full h-full flex overflow-hidden bg-slate-950 font-sans"
    >
      {/* ── Left Rail: Collapsible Conversation History ──────────────────────── */}
      <ChatSidebar />

      {/* ── Main Chat Column ────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative bg-slate-950">
        {/* Top Header with Back Button */}
        <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-sm flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold border border-slate-700/80 flex items-center gap-1.5 transition-colors shadow-sm cursor-pointer"
              title="Go back"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back</span>
            </button>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
              <h2 className="text-xs sm:text-sm font-bold text-slate-100 truncate max-w-[200px] sm:max-w-md">
                {activeSession?.title || 'AI Medical Assistant'}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={() => useChatStore.getState().createSession()}
            className="text-xs text-teal-400 hover:text-teal-300 font-medium px-2.5 py-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
          >
            + New Consultation
          </button>
        </div>

        {/* Messages Thread or Welcoming Empty State */}
        <div className="flex-1 overflow-y-auto flex flex-col relative">
          {messages.length === 0 ? (
            <ChatEmptyState
              onSelectPrompt={(prompt) => sendMessage(prompt)}
              userName={firstName || displayName}
            />
          ) : (
            <ChatMessages
              messages={messages}
              isGenerating={isGenerating}
              userName={displayName}
              onRetryMessage={(prompt) => sendMessage(prompt)}
              onActionSelected={(prompt) => sendMessage(prompt)}
            />
          )}
        </div>

        {/* Fixed Bottom Input Bar */}
        <ChatInput onSend={(text) => sendMessage(text)} isGenerating={isGenerating} />
      </div>
    </motion.div>
  )
}
