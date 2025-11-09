import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { TrendingUp, Clock, CheckCircle, Activity } from 'lucide-react'

export function Metrics() {
  // In a real app, these would come from an API
  const metrics = {
    totalQueries: 142,
    avgResponseTime: 1.24,
    successRate: 98.5,
    activeServices: 5,
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Queries</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.totalQueries}</div>
          <p className="text-xs text-muted-foreground">+12% from last week</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.avgResponseTime}s</div>
          <p className="text-xs text-muted-foreground">-8% faster</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          <CheckCircle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.successRate}%</div>
          <p className="text-xs text-muted-foreground">High reliability</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Services</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{metrics.activeServices}/5</div>
          <p className="text-xs text-muted-foreground">All systems operational</p>
        </CardContent>
      </Card>
    </div>
  )
}
