import { ServiceStatus } from '@/components/Dashboard/ServiceStatus'
import { HealthCheck } from '@/components/Dashboard/HealthCheck'
import { Metrics } from '@/components/Dashboard/Metrics'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function DashboardPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold">System Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Monitor your Maestro AI system status and performance
          </p>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="services">Services</TabsTrigger>
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {/* Metrics Cards */}
            <Metrics />

            {/* Health Check */}
            <HealthCheck />

            {/* Services Grid */}
            <div>
              <h2 className="text-xl font-semibold mb-4">Service Status</h2>
              <ServiceStatus />
            </div>
          </TabsContent>

          <TabsContent value="services" className="space-y-6">
            <ServiceStatus />
          </TabsContent>

          <TabsContent value="metrics" className="space-y-6">
            <Metrics />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <HealthCheck />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
