import { apiClient } from './client'
import type { QueryRequest, QueryResponse, IndexStatus } from '@/types/api'

export const ragAPI = {
  query: async (request: QueryRequest): Promise<QueryResponse> => {
    const { data } = await apiClient.post('/rag/query', request)
    return data
  },

  buildIndex: async (): Promise<{ status: string; message: string }> => {
    const { data } = await apiClient.post('/rag/build_index')
    return data
  },

  getIndexStatus: async (): Promise<IndexStatus> => {
    const { data } = await apiClient.get('/rag/index_status')
    return data
  },

  uploadDocument: async (file: File): Promise<{ status: string; document_id: string }> => {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await apiClient.post('/rag/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },
}
