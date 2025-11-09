import { useEffect, useRef } from 'react'
import { Message } from '@/types/chat'
import { AgentBadge } from './AgentBadge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { formatTimestamp, formatExecutionTime } from '@/lib/utils'
import { Copy, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface MessageListProps {
  messages: Message[]
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="max-w-md space-y-4">
          <h2 className="text-2xl font-semibold">Welcome to Maestro AI</h2>
          <p className="text-muted-foreground">
            Your intelligent executive assistant for knowledge management. Ask questions about your vault,
            and I'll help you find answers using your personal knowledge base.
          </p>
          <div className="grid grid-cols-1 gap-2 mt-6 text-sm">
            <div className="p-3 rounded-lg bg-muted/50 text-left">
              💡 Try: "What are my notes about AI?"
            </div>
            <div className="p-3 rounded-lg bg-muted/50 text-left">
              💡 Try: "Summarize my project ideas"
            </div>
            <div className="p-3 rounded-lg bg-muted/50 text-left">
              💡 Try: "What tasks do I have pending?"
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-lg p-4 ${
              message.role === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted'
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm">
                  {message.role === 'user' ? 'You' : 'Assistant'}
                </span>
                {message.agent && <AgentBadge agent={message.agent} />}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs opacity-70">
                  {formatTimestamp(message.timestamp)}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => copyToClipboard(message.content)}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            </div>

            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </div>

            {message.metadata && (
              <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
                {message.metadata.privacyWarning && (
                  <Alert variant="warning" className="py-2">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription className="text-xs ml-6">
                      {message.metadata.privacyWarning}
                    </AlertDescription>
                  </Alert>
                )}

                <div className="flex flex-wrap gap-2 text-xs">
                  {message.metadata.provider && (
                    <Badge variant="outline" className="text-xs">
                      {message.metadata.provider}
                    </Badge>
                  )}
                  {message.metadata.model && (
                    <Badge variant="outline" className="text-xs">
                      {message.metadata.model}
                    </Badge>
                  )}
                  {message.metadata.executionTime && (
                    <Badge variant="outline" className="text-xs">
                      {formatExecutionTime(message.metadata.executionTime)}
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
