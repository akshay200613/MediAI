'use client'
import { useState } from 'react'
import {
  Plus,
  MessageSquare,
  Trash2,
  Edit2,
  Check,
  X,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useChatStore, ConversationSession } from '@/lib/hooks/useChatStore'
import { cn } from '@/lib/utils'

export function ChatSidebar() {
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

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  // Group sessions by date
  const groupedSessions = sessions.reduce<{
    today: ConversationSession[]
    past7Days: ConversationSession[]
    older: ConversationSession[]
  }>(
    (acc, session) => {
      const now = new Date()
      const sessionDate = new Date(session.updatedAt)
      const diffDays = Math.floor((now.getTime() - sessionDate.getTime()) / (1000 * 3600 * 24))

      if (diffDays === 0) acc.today.push(session)
      else if (diffDays <= 7) acc.past7Days.push(session)
      else acc.older.push(session)

      return acc
    },
    { today: [], past7Days: [], older: [] },
  )

  const handleStartRename = (session: ConversationSession) => {
    setEditingId(session.id)
    setEditTitle(session.title)
  }

  const handleSaveRename = (id: string) => {
    if (editTitle.trim()) {
      renameSession(id, editTitle.trim())
    }
    setEditingId(null)
  }

  return (
    <>
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 md:hidden backdrop-blur-sm"
          onClick={toggleSidebar}
        />
      )}

      <aside
        className={cn(
          'glass-sidebar fixed md:relative z-30 h-full flex flex-col transition-all duration-300 flex-shrink-0',
          sidebarOpen ? 'w-72 translate-x-0' : '-translate-x-full md:translate-x-0 md:w-16',
        )}
      >
        {/* Top Controls */}
        <div className="p-3 border-b border-white/5 flex items-center justify-between">
          {sidebarOpen ? (
            <button
              onClick={() => createSession()}
              className="flex-1 btn-teal-gradient py-2 px-3 text-xs flex items-center justify-center gap-2 rounded-xl"
            >
              <Plus className="w-4 h-4" /> New Consultation
            </button>
          ) : (
            <button
              onClick={() => createSession()}
              className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center text-white shadow-glow"
              title="New Consultation"
            >
              <Plus className="w-5 h-5" />
            </button>
          )}

          <button
            onClick={toggleSidebar}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-white/5 ml-1 transition-colors"
            title={sidebarOpen ? 'Collapse rail' : 'Expand rail'}
          >
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        {/* Sessions List */}
        {sidebarOpen ? (
          <div className="flex-1 overflow-y-auto p-3 space-y-4 text-xs">
            {[
              { label: 'Today', items: groupedSessions.today },
              { label: 'Previous 7 Days', items: groupedSessions.past7Days },
              { label: 'Older', items: groupedSessions.older },
            ].map(
              (group) =>
                group.items.length > 0 && (
                  <div key={group.label} className="space-y-1">
                    <p className="px-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                      {group.label}
                    </p>
                    <div className="space-y-0.5">
                      {group.items.map((session) => {
                        const isActive = session.id === activeSessionId
                        const isEditing = session.id === editingId

                        return (
                          <div
                            key={session.id}
                            onClick={() => selectSession(session.id)}
                            className={cn(
                              'group relative flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer transition-all',
                              isActive
                                ? 'bg-teal-500/15 text-teal-300 font-medium border border-teal-500/20'
                                : 'text-slate-400 hover:text-white hover:bg-white/5',
                            )}
                          >
                            <div className="flex items-center gap-2.5 min-w-0 pr-12">
                              <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-teal-400" />
                              {isEditing ? (
                                <input
                                  type="text"
                                  value={editTitle}
                                  onChange={(e) => setEditTitle(e.target.value)}
                                  onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(session.id)}
                                  className="bg-surface-600 border border-teal-500 text-xs px-1.5 py-0.5 rounded text-white focus:outline-none w-full"
                                  autoFocus
                                />
                              ) : (
                                <span className="truncate">{session.title}</span>
                              )}
                            </div>

                            {/* Hover Action Icons */}
                            {!isEditing ? (
                              <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex items-center gap-1 bg-surface-800/90 px-1 py-0.5 rounded-lg border border-white/10 transition-opacity">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleStartRename(session)
                                  }}
                                  className="p-1 text-slate-400 hover:text-white"
                                  title="Rename"
                                >
                                  <Edit2 className="w-3 h-3" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    deleteSession(session.id)
                                  }}
                                  className="p-1 text-slate-400 hover:text-red-400"
                                  title="Delete"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleSaveRename(session.id)
                                  }}
                                  className="p-1 text-emerald-400 hover:text-emerald-300"
                                >
                                  <Check className="w-3 h-3" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setEditingId(null)
                                  }}
                                  className="p-1 text-slate-400 hover:text-white"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ),
            )}

            {sessions.length === 0 && (
              <div className="text-center py-8 text-slate-500">
                <Sparkles className="w-6 h-6 mx-auto mb-2 opacity-40 text-teal-400" />
                <p className="text-xs">No previous consultations</p>
              </div>
            )}
          </div>
        ) : (
          /* Collapsed Icon Bar */
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => selectSession(session.id)}
                className={cn(
                  'w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/5 transition-colors mx-auto',
                  session.id === activeSessionId && 'bg-teal-500/20 text-teal-400',
                )}
                title={session.title}
              >
                <MessageSquare className="w-4 h-4" />
              </button>
            ))}
          </div>
        )}
      </aside>
    </>
  )
}
