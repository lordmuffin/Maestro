import { createContext, useContext, ReactNode } from 'react'
import { useSettings } from '@/hooks/useSettings'
import type { ChatSettings } from '@/types/chat'

interface AppSettings extends ChatSettings {
  vaultPath?: string
  apiKeys?: {
    openai?: string
    anthropic?: string
    google?: string
  }
  darkMode?: boolean
}

interface SettingsContextType {
  settings: AppSettings
  updateSettings: (updates: Partial<AppSettings>) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const settingsHook = useSettings()

  return (
    <SettingsContext.Provider value={settingsHook}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettingsContext() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error('useSettingsContext must be used within a SettingsProvider')
  }
  return context
}
