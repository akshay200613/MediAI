'use client'
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useChatStore } from '@/lib/hooks/useChatStore'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { ChatMessages } from '@/components/chat/ChatMessages'
import { ChatInput } from '@/components/chat/ChatInput'
import { ChatEmptyState } from '@/components/chat/ChatEmptyState'
import { pageTransition } from '@/lib/motion'

export default function AIChatPage() {
  const { sessions, activeSessionId, isGenerating, sendMessage } = useChatStore()

  const activeSession = sessions.find((s) => s.id === activeSessionId)
  const messages = activeSession?.messages || []

  // Global shortcut: Ctrl+N / Cmd+N for new chat
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
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
      className="w-full h-full flex overflow-hidden bg-surface-900"
    >
      {/* ── Left Rail (Collapsible History) ─────────────────────────────────── */}
      <ChatSidebar />

      {/* ── Main Chat Column (Centered ~720px) ───────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* Messages or Empty State */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {messages.length === 0 ? (
            <ChatEmptyState onSelectPrompt={(prompt) => sendMessage(prompt)} />
          ) : (
            <ChatMessages messages={messages} isGenerating={isGenerating} />
          )}
        </div>

        {/* Fixed Bottom Input Bar */}
        <ChatInput onSend={(text) => sendMessage(text)} isGenerating={isGenerating} />
      </div>
    </motion.div>
  )
}
