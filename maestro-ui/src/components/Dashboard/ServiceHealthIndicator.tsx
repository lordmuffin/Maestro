import { useServiceHealth } from '@/hooks/useServiceHealth'
import { Badge } from '@/components/ui/badge'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'

export function ServiceHealthIndicator() {
  const { data: health, isLoading } = useServiceHealth()

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Checking services...</span>
      </div>
    )
  }

  const services = ['supervisor', 'rag', 'mapping', 'skills', 'evaluation'] as const
  const healthyCount = services.filter((s) => health?.[s]?.status === 'healthy').length
  const allHealthy = healthyCount === services.length

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {allHealthy ? (
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )}
        <span className="text-sm font-medium">Service Status</span>
      </div>
      <Badge variant={allHealthy ? 'success' : 'warning'} className="w-full justify-center">
        {healthyCount}/{services.length} Services Online
      </Badge>
    </div>
  )
}
