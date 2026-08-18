'use client'

import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { useChatStore } from '@/lib/hooks/useChatStore'
import { useAuth } from '@/lib/auth/context'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { ChatMessages } from '@/components/chat/ChatMessages'
import { ChatInput } from '@/components/chat/ChatInput'
import { ChatEmptyState } from '@/components/chat/ChatEmptyState'
import { pageTransition } from '@/lib/motion'

export default function AIChatPage() {
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

  useEffect(() => {
    if (!user) return

    if (sessions.length === 0 || !activeSessionId) {
      const name = firstName || displayName || 'there'
      const sessionId = useChatStore.getState().createSession()
      
      const welcomeMsg = collectProfile
        ? `Hello ${name}! Let's get your medical profile completed so you can book your doctor consultation. I'll need to collect a few details: Date of Birth, Gender, Blood Group, Address, and Emergency Contact. Let's start with your Date of Birth (YYYY-MM-DD) and Gender. What are they?`
        : `Hello ${name}! I'm your MediAI Clinical Assistant. How can I help you today?`

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
  }, [user, sessions.length, activeSessionId, collectProfile, firstName, displayName])

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
            />
          )}
        </div>

        {/* Fixed Bottom Input Bar */}
        <ChatInput onSend={(text) => sendMessage(text)} isGenerating={isGenerating} />
      </div>
    </motion.div>
  )
}
