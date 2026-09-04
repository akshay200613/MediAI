import apiClient from './client'

export const chatApi = {
  sendMessage: async (content: string, sessionId?: string, patientId?: string, signal?: AbortSignal): Promise<{
    data: { content: string; session_id: string; sources: unknown[]; agent_name: string; tool_calls: unknown[] }
    success: boolean
    message: string
  }> => {
    const res = await apiClient.post('/medai/chat', {
      content,
      session_id: sessionId,
      patient_id: patientId,
      use_rag: true,
    }, { signal })
    return res.data
  },

  streamMessage: async (
    content: string, 
    sessionId?: string, 
    patientId?: string, 
    onChunk?: (chunk: string) => void
  ): Promise<void> => {
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('access_token') : null
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://127.0.0.1:8000' : 'http://localhost:8000')
    const res = await fetch(`${API_BASE_URL}/api/v1/medai/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        content,
        session_id: sessionId,
        patient_id: patientId,
        use_rag: true
      })
    })

    if (!res.ok) {
      throw new Error(`Failed to stream message: ${res.statusText}`)
    }

    const reader = res.body?.getReader()
    if (!reader) return

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      
      const lines = buffer.split('\n')
      buffer = lines.pop() || ""
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const dataStr = line.slice(6)
            if (dataStr.trim() === '') continue
            const data = JSON.parse(dataStr)
            if (data.content && onChunk) {
              onChunk(data.content)
            } else if (data.error) {
              throw new Error(data.error)
            }
          } catch (e) {
            console.error("Error parsing stream chunk:", e)
          }
        }
      }
    }
  },

  clearSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/medai/chat/sessions/${sessionId}`)
  },

  ingestDocument: async (file: File, title: string, category = 'general'): Promise<{
    data: { source_id: string; chunks_indexed: number; title: string }
  }> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    formData.append('category', category)
    const res = await apiClient.post('/medai/rag/ingest', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  getSessions: async (): Promise<{
    data: Array<{ id: string; title: string; updated_at: string }>
    success: boolean
    message: string
  }> => {
    const res = await apiClient.get('/medai/chat/sessions')
    return res.data
  },

  getSessionMessages: async (sessionId: string): Promise<{
    data: Array<{ id: string; role: string; content: string; created_at: string }>
    success: boolean
    message: string
  }> => {
    const res = await apiClient.get(`/medai/chat/sessions/${sessionId}/messages`)
    return res.data
  },
}
