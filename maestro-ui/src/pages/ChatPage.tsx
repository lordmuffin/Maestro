import { useState } from 'react';
import { ChatWindow } from '@/components/Chat/ChatWindow';
import { useMutation } from '@tanstack/react-query';
import { supervisorAPI } from '@/lib/api/supervisor';
import { LLMSelector } from '@/components/Settings/LLMSelector';
import { ServiceHealthIndicator } from '@/components/Dashboard/ServiceHealthIndicator';
import type { Message } from '@/types/chat';

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [settings, setSettings] = useState({
    provider: 'local' as 'local' | 'claude' | 'gemini' | 'openai',
    modelTier: 'standard' as 'fast' | 'standard' | 'premium',
    sensitivity: 'medium' as 'low' | 'medium' | 'high'
  });

  const sendMessage = useMutation({
    mutationFn: async (query: string) => {
      // Add user message immediately
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMsg]);

      // Call supervisor API
      const response = await supervisorAPI.execute({
        query,
        sensitivity: settings.sensitivity,
        llm_provider: settings.provider,
        model_tier: settings.modelTier
      });

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
          executionTime: response.execution_time
        }
      };
      setMessages(prev => [...prev, assistantMsg]);

      return response;
    }
  });

  return (
    <div className="flex h-full">
      {/* Sidebar with settings */}
      <aside className="w-80 border-r bg-slate-50 dark:bg-slate-900/50 p-4 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Chat Settings</h2>

        <div className="space-y-6">
          <LLMSelector
            value={settings}
            onChange={setSettings}
          />

          <div className="pt-4 border-t">
            <ServiceHealthIndicator />
          </div>
        </div>
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col">
        <ChatWindow
          messages={messages}
          onSendMessage={(query) => sendMessage.mutate(query)}
          isLoading={sendMessage.isPending}
        />
      </main>
    </div>
  );
}
