import { useQuery } from '@tanstack/react-query'
import { servicesAPI } from '@/lib/api/services'
import type { ServicesHealth } from '@/types/services'

export function useServiceHealth(refetchInterval: number = 5000) {
  return useQuery<ServicesHealth>({
    queryKey: ['services', 'health'],
    queryFn: servicesAPI.checkAll,
    refetchInterval,
    retry: 2,
  })
}

export function useServiceStatus(serviceName: keyof ServicesHealth) {
  const { data, isLoading, error } = useServiceHealth()

  return {
    status: data?.[serviceName],
    isLoading,
    error,
  }
}
