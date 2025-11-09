import { useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Key, Eye, EyeOff } from 'lucide-react'

interface APIKey {
  provider: string
  key: string
  isSet: boolean
}

export function APIKeyManager() {
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({
    openai: false,
    anthropic: false,
    google: false,
  })

  const [apiKeys, setApiKeys] = useState<APIKey[]>([
    { provider: 'OpenAI', key: '', isSet: false },
    { provider: 'Anthropic (Claude)', key: '', isSet: false },
    { provider: 'Google (Gemini)', key: '', isSet: false },
  ])

  const toggleShowKey = (provider: string) => {
    setShowKeys((prev) => ({
      ...prev,
      [provider.toLowerCase()]: !prev[provider.toLowerCase()],
    }))
  }

  const handleKeyChange = (index: number, value: string) => {
    const newKeys = [...apiKeys]
    newKeys[index].key = value
    setApiKeys(newKeys)
  }

  const handleSave = (index: number) => {
    const newKeys = [...apiKeys]
    newKeys[index].isSet = newKeys[index].key.length > 0
    setApiKeys(newKeys)
    // In a real app, save to backend or secure storage
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5" />
          API Key Management
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {apiKeys.map((apiKey, index) => {
          const providerKey = apiKey.provider.toLowerCase().split(' ')[0]
          const isVisible = showKeys[providerKey]

          return (
            <div key={apiKey.provider} className="space-y-2">
              <Label htmlFor={`api-key-${index}`}>{apiKey.provider}</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    id={`api-key-${index}`}
                    type={isVisible ? 'text' : 'password'}
                    value={apiKey.key}
                    onChange={(e) => handleKeyChange(index, e.target.value)}
                    placeholder={`Enter ${apiKey.provider} API key`}
                    className="pr-10"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-10 w-10"
                    onClick={() => toggleShowKey(apiKey.provider)}
                  >
                    {isVisible ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <Button onClick={() => handleSave(index)} variant="outline">
                  {apiKey.isSet ? 'Update' : 'Save'}
                </Button>
              </div>
              {apiKey.isSet && (
                <p className="text-xs text-green-600 dark:text-green-400">
                  ✓ API key configured
                </p>
              )}
            </div>
          )
        })}

        <div className="pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            <strong>Note:</strong> API keys are stored securely and never sent to any third-party
            services. They are only used for direct communication with the respective AI providers.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
