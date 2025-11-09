import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import type { Message } from '@/types/chat'

interface ChatWindowProps {
  messages: Message[]
  onSendMessage: (message: string) => void
  isLoading?: boolean
}

export function ChatWindow({ messages, onSendMessage, isLoading }: ChatWindowProps) {
  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} />
      <MessageInput onSend={onSendMessage} isLoading={isLoading} />
    </div>
  )
}
