import { Badge } from '@/components/ui/badge'

interface AgentBadgeProps {
  agent: string
  className?: string
}

export function AgentBadge({ agent, className }: AgentBadgeProps) {
  const getAgentColor = (agentName: string) => {
    const colors: Record<string, 'default' | 'secondary' | 'success' | 'warning'> = {
      'Local RAG': 'success',
      'Claude Agent': 'default',
      'Gemini Agent': 'secondary',
      'OpenAI Agent': 'warning',
      'Supervisor': 'secondary',
    }
    return colors[agentName] || 'default'
  }

  return (
    <Badge variant={getAgentColor(agent)} className={className}>
      {agent}
    </Badge>
  )
}
