export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  role: MessageRole
  content: string
  agent?: string
  timestamp: Date
  metadata?: MessageMetadata
}

export interface MessageMetadata {
  provider?: string
  model?: string
  sensitivity?: 'low' | 'medium' | 'high'
  privacyWarning?: string
  executionTime?: number
  sources?: MessageSource[]
  error?: string
}

export interface MessageSource {
  title: string
  content: string
  score: number
  metadata: Record<string, any>
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
  settings: ChatSettings
}

export interface ChatSettings {
  provider: 'local' | 'claude' | 'gemini' | 'openai'
  modelTier: 'fast' | 'standard' | 'premium'
  sensitivity: 'low' | 'medium' | 'high'
}

export interface ChatHistory {
  sessions: ChatSession[]
  currentSessionId?: string
}
