'use client'

import { create } from 'zustand'
import { chatApi } from '@/lib/api/chat'
import type { ChatMessage, Citation, ConversationSession, RetrievalStatus } from '@/types/chat'

interface ChatStore {
  sessions: ConversationSession[]
  activeSessionId: string | null
  isGenerating: boolean
  isLoadingSessions: boolean
  abortController: AbortController | null
  sidebarOpen: boolean
  
  // Citation Panel State
  citationPanelOpen: boolean
  panelCitations: Citation[]
  selectedCitationId: string | null

  // Actions
  toggleSidebar: () => void
  openCitationPanel: (citations: Citation[], selectedId?: string) => void
  closeCitationPanel: () => void
  setSelectedCitationId: (id: string | null) => void
  fetchSessions: () => Promise<void>
  createSession: (title?: string) => string
  selectSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  renameSession: (id: string, newTitle: string) => void
  resetStore: () => void
  sendMessage: (text: string, patientId?: string) => Promise<void>
  stopGeneration: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  isGenerating: false,
  isLoadingSessions: false,
  abortController: null,
  sidebarOpen: true,
  
  citationPanelOpen: false,
  panelCitations: [],
  selectedCitationId: null,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  openCitationPanel: (citations, selectedId) =>
    set({
      citationPanelOpen: true,
      panelCitations: citations,
      selectedCitationId: selectedId || citations[0]?.id || null,
    }),

  closeCitationPanel: () => set({ citationPanelOpen: false }),

  setSelectedCitationId: (id) => set({ selectedCitationId: id }),

  resetStore: () => {
    set({
      sessions: [],
      activeSessionId: null,
      isGenerating: false,
      isLoadingSessions: false,
      abortController: null,
    })
  },

  fetchSessions: async () => {
    try {
      set({ isLoadingSessions: true })
      const res = await chatApi.getSessions()
      const fetched = res.data || []
      const currentSessions = get().sessions

      const updatedSessions: ConversationSession[] = fetched.map((s: any) => {
        const existing = currentSessions.find((cs) => cs.id === s.id)
        return {
          id: s.id,
          title: s.title || 'Consultation',
          createdAt: s.created_at || new Date().toISOString(),
          updatedAt: s.updated_at || new Date().toISOString(),
          messages: existing ? existing.messages : [],
        }
      })

      set({
        sessions: updatedSessions,
        activeSessionId: get().activeSessionId || (updatedSessions[0]?.id ?? null),
      })

      // If active session has no messages loaded yet, load them
      const activeId = get().activeSessionId
      if (activeId) {
        await get().selectSession(activeId)
      }
    } catch (err) {
      console.warn('Failed to fetch persistent chat sessions:', err)
    } finally {
      set({ isLoadingSessions: false })
    }
  },

  createSession: (title) => {
    const newId = `session-${Date.now()}`
    const newSession: ConversationSession = {
      id: newId,
      title: title || 'New Consultation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    }
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      activeSessionId: newId,
    }))
    return newId
  },

  selectSession: async (id) => {
    set({ activeSessionId: id })
    const session = get().sessions.find((s) => s.id === id)
    if (session && session.messages.length === 0) {
      try {
        const res = await chatApi.getSessionMessages(id)
        const msgs = (res.data || []).map((m: any) => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.created_at || new Date().toISOString(),
        }))

        set((state) => ({
          sessions: state.sessions.map((s) => (s.id === id ? { ...s, messages: msgs } : s)),
        }))
      } catch (err) {
        console.warn('Failed to load session messages:', err)
      }
    }
  },

  deleteSession: async (id) => {
    set((state) => {
      const filtered = state.sessions.filter((s) => s.id !== id)
      const nextActive = state.activeSessionId === id ? filtered[0]?.id || null : state.activeSessionId
      return { sessions: filtered, activeSessionId: nextActive }
    })
    try {
      await chatApi.clearSession(id)
    } catch {}
  },

  renameSession: (id, newTitle) => {
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? { ...s, title: newTitle } : s)),
    }))
  },

  sendMessage: async (text, patientId) => {
    const controller = new AbortController()
    set({ abortController: controller })
    
    let sessionId = get().activeSessionId
    if (!sessionId) {
      sessionId = get().createSession()
    }

    const userMsgId = `msg-user-${Date.now()}`
    const userMessage: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }

    const assistantMsgId = `msg-ai-${Date.now()}`
    const initialAssistantMessage: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      retrievalStatus: 'searching',
    }

    // Append user & temporary assistant message
    set((state) => {
      const updatedSessions = state.sessions.map((s) => {
        if (s.id === sessionId) {
          const isFirst = s.messages.length === 0
          return {
            ...s,
            title: isFirst ? text.slice(0, 32) + (text.length > 32 ? '...' : '') : s.title,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, userMessage, initialAssistantMessage],
          }
        }
        return s
      })
      return { sessions: updatedSessions, isGenerating: true }
    })

    // Simulate retrieval rank fusion transition
    setTimeout(() => {
      set((state) => ({
        sessions: state.sessions.map((s) => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: s.messages.map((m) =>
                m.id === assistantMsgId ? { ...m, retrievalStatus: 'fusing' } : m
              ),
            }
          }
          return s
        }),
      }))
    }, 400)

    try {
      let response;
      let attempt = 0;
      const maxRetries = 2;

      while (attempt <= maxRetries) {
        try {
          response = await chatApi.sendMessage(text, sessionId, patientId, controller.signal);
          break; // Success
        } catch (err: any) {
          const isCanceled = err?.name === 'CanceledError' || err?.message?.includes('canceled');
          if (isCanceled) throw err; // Don't retry user cancellations

          const serverDetail = err?.response?.data?.detail || err?.response?.data?.message || '';
          const isUnavailable = serverDetail.includes('The AI service is temporarily unavailable') || err?.response?.status >= 500 || err?.response?.status === 429;

          if (isUnavailable && attempt < maxRetries) {
            attempt++;
            // Update UI to show retry attempt
            set((state) => ({
              sessions: state.sessions.map((s) => {
                if (s.id === sessionId) {
                  return {
                    ...s,
                    messages: s.messages.map((m) =>
                      m.id === assistantMsgId ? { ...m, retrievalStatus: 'searching' as any, content: `Connection lost. Retrying automatically (Attempt ${attempt}/${maxRetries})...` } : m
                    ),
                  }
                }
                return s
              }),
            }));
            await new Promise((resolve) => setTimeout(resolve, attempt * 1500));
            continue;
          }
          throw err;
        }
      }

      const currentContent = response!.data.content
      const rawSources = (response?.data as any)?.sources || (response?.data as any)?.citations || []
      const citations: Citation[] = rawSources.map((s: any, idx: number) => ({
        id: String(s.id || s.chunk_id || s.document_id || `source-${idx + 1}`),
        documentName: s.title || s.documentName || s.hospital_name || s.category || `Source ${idx + 1}`,
        excerpt: s.text || s.excerpt || s.content || '',
        retrievalMethod: (s.retrievalMethod || (s.dense_score ? 'hybrid' : 'vector')) as any,
        score: typeof s.score === 'number' ? s.score : 0.85,
      }))

      set((state) => ({
        sessions: state.sessions.map((s) => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: s.messages.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: currentContent,
                      citations: citations.length > 0 ? citations : m.citations,
                      retrievalStatus: 'done',
                    }
                  : m
              ),
            }
          }
          return s
        }),
      }))

      // Check for clinical warning keywords
      let calloutType: 'amber' | 'red' | null = null
      if (/emergency|urgent|immediate medical attention|seek emergency/i.test(currentContent)) {
        calloutType = 'red'
      } else if (/note:|important:|flagged:|warning:|disclaimer/i.test(currentContent)) {
        calloutType = 'amber'
      }

      set((state) => ({
        sessions: state.sessions.map((s) => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: s.messages.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      isStreaming: false,
                      calloutType,
                    }
                  : m
              ),
            }
          }
          return s
        }),
      }))
    } catch (err: any) {
      const isCanceled = err?.name === 'CanceledError' || err?.message?.includes('canceled')
      // Extract the exact user-facing message from a 503 (or any HTTP error) response
      const serverDetail: string | undefined =
        err?.response?.data?.detail || err?.response?.data?.message
      const SERVICE_UNAVAILABLE = 'The AI service is temporarily unavailable. Please try again.'
      const errorContent = isCanceled
        ? 'Generation stopped by user.'
        : serverDetail || SERVICE_UNAVAILABLE

      set((state) => ({
        sessions: state.sessions.map((s) => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: s.messages.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: errorContent,
                      isStreaming: false,
                      retrievalStatus: 'done',
                      error: isCanceled ? undefined : errorContent,
                      calloutType: isCanceled ? undefined : 'amber',
                    }
                  : m
              ),
            }
          }
          return s
        }),
      }))
    } finally {
      set({ isGenerating: false, abortController: null })
    }
  },

  stopGeneration: () => {
    const { abortController } = get()
    if (abortController) {
      abortController.abort()
      set({ abortController: null, isGenerating: false })
    }
  }
}))
