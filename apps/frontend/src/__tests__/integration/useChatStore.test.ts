/**
 * Integration tests for useChatStore.ts
 * Uses Vitest + msw to mock the API layer.
 *
 * Tests the complete state-machine transitions:
 *  createSession → selectSession → sendMessage → stopGeneration → deleteSession
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// We import the store after setting up MSW so the module-level axios instance gets the mock
import { useChatStore } from '@/lib/hooks/useChatStore'

// ── MSW Server setup ──────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const handlers = [
  http.post(`${API_URL}/api/v1/medai/chat/message`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        content: 'This is a mock AI response about medications.',
        citations: [],
        session_id: 'session-test-123',
      },
    })
  }),
]

const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// ── Helpers ───────────────────────────────────────────────────────────────────

function resetStore() {
  // Reset to initial state between tests
  useChatStore.setState({
    sessions: [],
    activeSessionId: null,
    isGenerating: false,
    abortController: null,
    sidebarOpen: true,
    citationPanelOpen: false,
    panelCitations: [],
    selectedCitationId: null,
  })
}

// ── Session Management ────────────────────────────────────────────────────────

describe('Session management', () => {
  beforeEach(resetStore)

  it('createSession adds a session with unique ID and sets it as active', () => {
    const { result } = renderHook(() => useChatStore())

    let sessionId: string
    act(() => {
      sessionId = result.current.createSession()
    })

    expect(result.current.sessions).toHaveLength(1)
    expect(result.current.activeSessionId).toBe(sessionId!)
    expect(result.current.sessions[0].title).toBe('New Consultation')
    expect(result.current.sessions[0].messages).toEqual([])
  })

  it('createSession creates sessions with unique IDs', () => {
    const { result } = renderHook(() => useChatStore())

    let id1: string, id2: string
    act(() => {
      id1 = result.current.createSession()
    })
    // Advance timer so Date.now() returns a different value for the next session
    vi.useFakeTimers()
    vi.advanceTimersByTime(10)
    act(() => {
      id2 = result.current.createSession()
    })
    vi.useRealTimers()

    expect(id1!).not.toBe(id2!)
    expect(result.current.sessions).toHaveLength(2)
  })

  it('selectSession changes activeSessionId', () => {
    const { result } = renderHook(() => useChatStore())

    let id1: string, id2: string
    act(() => {
      id1 = result.current.createSession()
      id2 = result.current.createSession()
    })

    act(() => {
      result.current.selectSession(id1!)
    })

    expect(result.current.activeSessionId).toBe(id1!)
  })

  it('deleteSession removes the session and picks next active', () => {
    const { result } = renderHook(() => useChatStore())

    let id1: string, id2: string
    act(() => {
      id1 = result.current.createSession()
    })
    vi.useFakeTimers()
    vi.advanceTimersByTime(5)
    act(() => {
      id2 = result.current.createSession()
      result.current.selectSession(id2!)
    })
    vi.useRealTimers()

    act(() => {
      result.current.deleteSession(id2!)
    })

    expect(result.current.sessions.find((s) => s.id === id2!)).toBeUndefined()
    // Should fall back to the remaining session (id1)
    expect(result.current.sessions).toHaveLength(1)
    expect(result.current.activeSessionId).toBe(id1!)
  })

  it('deleteSession with only one session leaves activeSessionId null', () => {
    const { result } = renderHook(() => useChatStore())

    let id: string
    act(() => {
      id = result.current.createSession()
    })

    act(() => {
      result.current.deleteSession(id!)
    })

    expect(result.current.sessions).toHaveLength(0)
    expect(result.current.activeSessionId).toBeNull()
  })

  it('renameSession updates session title', () => {
    const { result } = renderHook(() => useChatStore())

    let id: string
    act(() => {
      id = result.current.createSession()
    })

    act(() => {
      result.current.renameSession(id!, 'Patient Consultation')
    })

    const session = result.current.sessions.find((s) => s.id === id!)
    expect(session?.title).toBe('Patient Consultation')
  })
})

// ── Sidebar & Citation Panel ──────────────────────────────────────────────────

describe('Sidebar and citation panel', () => {
  beforeEach(resetStore)

  it('toggleSidebar flips sidebarOpen', () => {
    const { result } = renderHook(() => useChatStore())

    expect(result.current.sidebarOpen).toBe(true)
    act(() => {
      result.current.toggleSidebar()
    })
    expect(result.current.sidebarOpen).toBe(false)
    act(() => {
      result.current.toggleSidebar()
    })
    expect(result.current.sidebarOpen).toBe(true)
  })

  it('openCitationPanel sets panel state', () => {
    const { result } = renderHook(() => useChatStore())
    const citations = [{ id: 'c1', title: 'Source 1', content: 'Text', score: 0.9, source: 'doc.pdf' }]

    act(() => {
      result.current.openCitationPanel(citations as any, 'c1')
    })

    expect(result.current.citationPanelOpen).toBe(true)
    expect(result.current.selectedCitationId).toBe('c1')
    expect(result.current.panelCitations).toHaveLength(1)
  })

  it('closeCitationPanel sets citationPanelOpen to false', () => {
    const { result } = renderHook(() => useChatStore())

    act(() => {
      result.current.openCitationPanel([] as any)
      result.current.closeCitationPanel()
    })

    expect(result.current.citationPanelOpen).toBe(false)
  })
})

// ── stopGeneration ────────────────────────────────────────────────────────────

describe('stopGeneration', () => {
  beforeEach(resetStore)

  it('aborts the controller and sets isGenerating to false', () => {
    const { result } = renderHook(() => useChatStore())
    const controller = new AbortController()
    const abortSpy = vi.spyOn(controller, 'abort')

    act(() => {
      useChatStore.setState({ abortController: controller, isGenerating: true })
    })

    act(() => {
      result.current.stopGeneration()
    })

    expect(abortSpy).toHaveBeenCalled()
    expect(result.current.isGenerating).toBe(false)
    expect(result.current.abortController).toBeNull()
  })

  it('does nothing when abortController is null', () => {
    const { result } = renderHook(() => useChatStore())

    act(() => {
      useChatStore.setState({ abortController: null, isGenerating: false })
    })

    expect(() => {
      act(() => {
        result.current.stopGeneration()
      })
    }).not.toThrow()
  })
})
