import { useServiceHealth } from '@/hooks/useServiceHealth'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

export function HealthCheck() {
  const { data: health, isLoading } = useServiceHealth()

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  const services = [
    { name: 'Supervisor', key: 'supervisor' as const },
    { name: 'Local RAG', key: 'rag' as const },
    { name: 'Path Mapping', key: 'mapping' as const },
    { name: 'Skills', key: 'skills' as const },
    { name: 'Evaluation', key: 'evaluation' as const },
  ]

  const healthyCount = services.filter(
    (s) => health?.[s.key]?.status === 'healthy'
  ).length

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          System Health
          <Badge variant={healthyCount === services.length ? 'success' : 'warning'}>
            {healthyCount}/{services.length} Healthy
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {services.map((service) => {
            const status = health?.[service.key]?.status
            const isHealthy = status === 'healthy'

            return (
              <div
                key={service.key}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50"
              >
                <div className="flex items-center gap-2">
                  {isHealthy ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-sm font-medium">{service.name}</span>
                </div>
                <Badge variant={isHealthy ? 'success' : 'destructive'} className="text-xs">
                  {status || 'unknown'}
                </Badge>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
