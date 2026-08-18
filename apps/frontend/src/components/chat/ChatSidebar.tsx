'use client'

import React, { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  MessageSquare,
  Search,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
  Database,
  Pencil,
  Check,
  Stethoscope,
} from 'lucide-react'
import { useChatStore } from '@/lib/hooks/useChatStore'
import type { ConversationSession } from '@/types/chat'

export const ChatSidebar: React.FC = () => {
  const {
    sessions,
    activeSessionId,
    sidebarOpen,
    toggleSidebar,
    createSession,
    selectSession,
    deleteSession,
    renameSession,
  } = useChatStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  // Filtered and Date-Grouped Sessions
  const groupedSessions = useMemo(() => {
    const query = searchQuery.toLowerCase().trim()
    const filtered = sessions.filter((s) => s.title.toLowerCase().includes(query))

    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const yesterday = today - 86400000
    const weekAgo = today - 7 * 86400000

    const groups: { [key: string]: ConversationSession[] } = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    }

    filtered.forEach((session) => {
      const sessionTime = new Date(session.updatedAt || session.createdAt).getTime()
      if (sessionTime >= today) {
        groups.Today.push(session)
      } else if (sessionTime >= yesterday) {
        groups.Yesterday.push(session)
      } else if (sessionTime >= weekAgo) {
        groups['Previous 7 Days'].push(session)
      } else {
        groups.Older.push(session)
      }
    })

    return groups
  }, [sessions, searchQuery])

  const handleStartRename = (session: ConversationSession, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(session.id)
    setEditingTitle(session.title)
  }

  const handleSaveRename = (id: string, e: React.MouseEvent | React.FormEvent) => {
    e.stopPropagation()
    e.preventDefault()
    if (editingTitle.trim()) {
      renameSession(id, editingTitle.trim())
    }
    setEditingId(null)
  }

  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        onClick={toggleSidebar}
        className="lg:hidden fixed top-3 left-3 z-30 p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white"
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
      </button>

      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="h-full bg-slate-900/95 border-r border-slate-800/80 flex flex-col shrink-0 z-20 overflow-hidden text-slate-300 font-sans"
          >
            {/* Header */}
            <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                  <Stethoscope className="w-4 h-4" />
                </div>
                <span className="font-semibold text-sm text-slate-100 tracking-tight">Clinical Assistant</span>
              </div>
              <button
                onClick={toggleSidebar}
                className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Collapse sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Actions: New Chat & Search */}
            <div className="p-3 space-y-2 border-b border-slate-800/60">
              <button
                onClick={() => createSession()}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs shadow-md shadow-teal-900/20 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  New Consultation
                </span>
                <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-teal-700/60 rounded text-teal-100">
                  Ctrl+N
                </kbd>
              </button>

              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Search consultations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
                />
              </div>
            </div>

            {/* Conversation History List */}
            <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
              {Object.entries(groupedSessions).map(([groupTitle, groupSessions]) => {
                if (groupSessions.length === 0) return null

                return (
                  <div key={groupTitle} className="space-y-1">
                    <h4 className="px-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                      {groupTitle}
                    </h4>
                    <div className="space-y-0.5">
                      {groupSessions.map((session) => {
                        const isActive = session.id === activeSessionId
                        const isEditing = editingId === session.id

                        return (
                          <div
                            key={session.id}
                            onClick={() => selectSession(session.id)}
                            className={`group relative flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                              isActive
                                ? 'bg-slate-800 text-teal-300 font-medium border border-slate-700/60'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1 pr-1">
                              <MessageSquare
                                className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-teal-400' : 'text-slate-500'}`}
                              />
                              {isEditing ? (
                                <form
                                  onSubmit={(e) => handleSaveRename(session.id, e)}
                                  className="flex items-center gap-1 flex-1"
                                >
                                  <input
                                    type="text"
                                    value={editingTitle}
                                    onChange={(e) => setEditingTitle(e.target.value)}
                                    autoFocus
                                    className="w-full bg-slate-950 text-slate-100 border border-teal-500/50 rounded px-1.5 py-0.5 text-xs focus:outline-none"
                                  />
                                  <button
                                    type="submit"
                                    onClick={(e) => handleSaveRename(session.id, e)}
                                    className="p-1 text-teal-400 hover:text-teal-300"
                                  >
                                    <Check className="w-3.5 h-3.5" />
                                  </button>
                                </form>
                              ) : (
                                <span className="truncate text-xs">{session.title}</span>
                              )}
                            </div>

                            {/* Session Quick Actions */}
                            {!isEditing && (
                              <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
                                <button
                                  onClick={(e) => handleStartRename(session, e)}
                                  className="p-1 rounded text-slate-500 hover:text-slate-200 hover:bg-slate-700/60"
                                  title="Rename session"
                                >
                                  <Pencil className="w-3 h-3" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    deleteSession(session.id)
                                  }}
                                  className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-700/60"
                                  title="Delete session"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}

              {sessions.length === 0 && (
                <div className="py-10 text-center px-4">
                  <p className="text-xs text-slate-500">No previous consultations.</p>
                  <p className="text-[11px] text-slate-600 mt-1">Start a new query to initiate RAG assistance.</p>
                </div>
              )}
            </div>

          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
