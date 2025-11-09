import { useState, KeyboardEvent } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Send, Loader2 } from 'lucide-react'

interface MessageInputProps {
  onSend: (message: string) => void
  isLoading?: boolean
  placeholder?: string
}

export function MessageInput({ onSend, isLoading, placeholder }: MessageInputProps) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex items-end gap-2 p-4 border-t bg-background">
      <Textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Ask anything about your vault...'}
        className="min-h-[60px] max-h-[200px] resize-none"
        disabled={isLoading}
      />
      <Button
        onClick={handleSend}
        disabled={!input.trim() || isLoading}
        size="icon"
        className="h-[60px] w-[60px]"
      >
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Send className="h-5 w-5" />
        )}
      </Button>
    </div>
  )
}
