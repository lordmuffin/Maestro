import { apiClient } from './client'
import type { ServiceHealthCheck, ServicesHealth } from '@/types/services'

const checkService = async (
  endpoint: string
): Promise<ServiceHealthCheck> => {
  const startTime = Date.now()

  try {
    await apiClient.get(`${endpoint}/health`, { timeout: 5000 })
    const responseTime = Date.now() - startTime

    return {
      status: 'healthy',
      timestamp: new Date(),
      responseTime,
    }
  } catch (error) {
    return {
      status: 'unhealthy',
      timestamp: new Date(),
      responseTime: Date.now() - startTime,
      error: error instanceof Error ? error.message : 'Unknown error',
    }
  }
}

export const servicesAPI = {
  checkAll: async (): Promise<ServicesHealth> => {
    const [supervisor, rag, mapping, skills, evaluation] = await Promise.all([
      checkService('/supervisor'),
      checkService('/rag'),
      checkService('/mapping'),
      checkService('/skills'),
      checkService('/evaluation'),
    ])

    return {
      supervisor,
      rag,
      mapping,
      skills,
      evaluation,
    }
  },

  checkSupervisor: () => checkService('/supervisor'),
  checkRAG: () => checkService('/rag'),
  checkMapping: () => checkService('/mapping'),
  checkSkills: () => checkService('/skills'),
  checkEvaluation: () => checkService('/evaluation'),
}

export function getPort(serviceName: string): number {
  const ports: Record<string, number> = {
    supervisor: 8003,
    rag: 8001,
    mapping: 8002,
    skills: 8004,
    evaluation: 8000,
  }
  return ports[serviceName] || 8000
}
