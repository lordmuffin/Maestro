import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';

interface LLMSettings {
  provider: 'local' | 'claude' | 'gemini' | 'openai';
  modelTier: 'fast' | 'standard' | 'premium';
  sensitivity: 'low' | 'medium' | 'high';
}

export function LLMSelector({ value, onChange }: {
  value: LLMSettings;
  onChange: (settings: LLMSettings) => void;
}) {
  const showPrivacyWarning =
    value.provider !== 'local' && value.sensitivity === 'high';

  return (
    <div className="space-y-4">
      <div>
        <Label className="text-sm font-medium">LLM Provider</Label>
        <Select
          value={value.provider}
          onValueChange={(provider) => onChange({ ...value, provider: provider as any })}
        >
          <SelectTrigger className="mt-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="local">Ollama (Local)</SelectItem>
            <SelectItem value="claude">Anthropic Claude</SelectItem>
            <SelectItem value="gemini">Google Gemini</SelectItem>
            <SelectItem value="openai">OpenAI</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label className="text-sm font-medium">Model Tier</Label>
        <Select
          value={value.modelTier}
          onValueChange={(modelTier) => onChange({ ...value, modelTier: modelTier as any })}
        >
          <SelectTrigger className="mt-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="fast">Fast</SelectItem>
            <SelectItem value="standard">Standard</SelectItem>
            <SelectItem value="premium">Premium</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label className="text-sm font-medium">Data Sensitivity</Label>
        <Select
          value={value.sensitivity}
          onValueChange={(sensitivity) => onChange({ ...value, sensitivity: sensitivity as any })}
        >
          <SelectTrigger className="mt-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="low">Low</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="high">High</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {showPrivacyWarning && (
        <Alert variant="warning">
          <AlertDescription>
            ⚠️ Using cloud provider with high-sensitivity data.
            Consider using 'local' provider for maximum privacy.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
