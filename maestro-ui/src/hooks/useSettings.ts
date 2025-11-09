import { useState, useEffect, useCallback } from 'react'
import type { ChatSettings } from '@/types/chat'

const SETTINGS_KEY = 'maestro-settings'

interface AppSettings extends ChatSettings {
  vaultPath?: string
  apiKeys?: {
    openai?: string
    anthropic?: string
    google?: string
  }
  darkMode?: boolean
}

const defaultSettings: AppSettings = {
  provider: 'local',
  modelTier: 'standard',
  sensitivity: 'medium',
  darkMode: false,
}

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(() => {
    const stored = localStorage.getItem(SETTINGS_KEY)
    if (stored) {
      try {
        return { ...defaultSettings, ...JSON.parse(stored) }
      } catch (e) {
        console.error('Failed to parse stored settings:', e)
      }
    }
    return defaultSettings
  })

  // Persist settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  }, [settings])

  const updateSettings = useCallback((updates: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }))
  }, [])

  const resetSettings = useCallback(() => {
    setSettings(defaultSettings)
    localStorage.removeItem(SETTINGS_KEY)
  }, [])

  return {
    settings,
    updateSettings,
    resetSettings,
  }
}
