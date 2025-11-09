export type ServiceStatus = 'healthy' | 'unhealthy' | 'unknown' | 'loading'

export interface Service {
  name: string
  displayName: string
  status: ServiceStatus
  port: number
  url: string
  description: string
  lastChecked?: Date
  responseTime?: number
  version?: string
  replicas?: {
    desired: number
    current: number
  }
}

export interface ServiceHealthCheck {
  status: ServiceStatus
  timestamp: Date
  responseTime: number
  error?: string
}

export interface ServicesHealth {
  supervisor: ServiceHealthCheck
  rag: ServiceHealthCheck
  mapping: ServiceHealthCheck
  skills: ServiceHealthCheck
  evaluation: ServiceHealthCheck
}

export interface SystemMetrics {
  totalQueries: number
  averageResponseTime: number
  successRate: number
  activeServices: number
  lastUpdated: Date
}

export interface ServiceMetrics {
  requestCount: number
  errorCount: number
  averageLatency: number
  p95Latency: number
  p99Latency: number
  uptime: number
}
