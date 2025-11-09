import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { supervisorAPI } from '@/lib/api/supervisor'
import type { Message, ChatSettings } from '@/types/chat'

export function useChat(initialSettings?: ChatSettings) {
  const [messages, setMessages] = useState<Message[]>([])
  const [settings, setSettings] = useState<ChatSettings>(
    initialSettings || {
      provider: 'local',
      modelTier: 'standard',
      sensitivity: 'medium',
    }
  )

  const sendMessage = useMutation({
    mutationFn: async (query: string) => {
      // Add user message immediately
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])

      // Call supervisor API
      const response = await supervisorAPI.execute({
        query,
        sensitivity: settings.sensitivity,
        llm_provider: settings.provider,
        model_tier: settings.modelTier,
      })

      // Add assistant response
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.result.response || 'No response',
        agent: response.agent_used,
        timestamp: new Date(),
        metadata: {
          provider: response.provider_used,
          model: response.model_used,
          sensitivity: settings.sensitivity,
          privacyWarning: response.privacy_warning,
          executionTime: response.execution_time,
        },
      }
      setMessages((prev) => [...prev, assistantMsg])

      return response
    },
  })

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  const updateSettings = useCallback((newSettings: Partial<ChatSettings>) => {
    setSettings((prev) => ({ ...prev, ...newSettings }))
  }, [])

  return {
    messages,
    settings,
    sendMessage: sendMessage.mutate,
    isLoading: sendMessage.isPending,
    error: sendMessage.error,
    clearMessages,
    updateSettings,
  }
}
