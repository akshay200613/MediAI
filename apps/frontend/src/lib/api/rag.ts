import apiClient from './client'
import { chatApi } from './chat'

export const ragApi = {
  ingestDocument: chatApi.ingestDocument,

  queryKnowledgeBase: async (query: string, topK = 5): Promise<{
    data: { answer: string; sources: any[]; retrieved_chunks: number; query: string }
  }> => {
    const res = await apiClient.post('/medai/rag/query', { query, top_k: topK })
    return res.data
  },
}
