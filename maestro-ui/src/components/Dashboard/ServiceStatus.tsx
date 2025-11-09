import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { servicesAPI, getPort } from '@/lib/api/services';

export function ServiceStatus() {
  const { data: services } = useQuery({
    queryKey: ['services'],
    queryFn: servicesAPI.checkAll,
    refetchInterval: 5000 // Poll every 5 seconds
  });

  const serviceNames = [
    { key: 'supervisor', name: 'Supervisor' },
    { key: 'rag', name: 'Local RAG' },
    { key: 'mapping', name: 'Path Mapping' },
    { key: 'skills', name: 'Skills' },
    { key: 'evaluation', name: 'Evaluation' },
  ] as const;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {serviceNames.map(({ key, name }) => {
        const service = services?.[key];
        const status = service?.status || 'unknown';

        return (
          <Card key={key}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-lg">
                {name}
                <Badge variant={status === 'healthy' ? 'success' : 'destructive'}>
                  {status}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Port:</span>
                  <span className="font-mono">{getPort(key)}</span>
                </div>
                {service?.responseTime && (
                  <div className="flex justify-between text-sm">
                    <span>Response Time:</span>
                    <span className="font-mono">{service.responseTime}ms</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span>Replicas:</span>
                  <span>2/2</span>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
