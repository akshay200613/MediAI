/**
 * MediAI Clinical AI Chat Interface - Type Definitions
 */

export type RetrievalMethod = 'vector' | 'keyword' | 'hybrid'

export type Citation = {
  id: string
  documentName: string
  excerpt: string
  retrievalMethod: RetrievalMethod
  score: number
}

export type RetrievalStatus = 'idle' | 'searching' | 'fusing' | 'done'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: string
  isStreaming?: boolean
  retrievalStatus?: RetrievalStatus
  calloutType?: 'amber' | 'red' | null
  error?: string | null
}

export type ConversationSession = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
}
