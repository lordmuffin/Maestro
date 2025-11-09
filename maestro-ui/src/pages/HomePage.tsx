import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { MessageSquare, Brain, Shield, Zap, ArrowRight } from 'lucide-react'

export function HomePage() {
  const features = [
    {
      icon: Brain,
      title: 'Intelligent RAG',
      description: 'Query your knowledge base with advanced retrieval-augmented generation',
    },
    {
      icon: Shield,
      title: 'Privacy-First',
      description: 'Local-first architecture with optional cloud providers for flexibility',
    },
    {
      icon: Zap,
      title: 'Multi-Agent System',
      description: 'Supervisor orchestrates specialized agents for optimal task execution',
    },
  ]

  return (
    <div className="h-full overflow-y-auto">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 border-b">
        <div className="max-w-5xl mx-auto px-8 py-16">
          <div className="text-center space-y-6">
            <h1 className="text-5xl font-bold tracking-tight">
              Welcome to{' '}
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Maestro AI
              </span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Your intelligent executive assistant for knowledge management.
              Query your Obsidian vault with the power of AI.
            </p>
            <div className="flex gap-4 justify-center">
              <Link to="/chat">
                <Button size="lg" className="gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Start Chatting
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/dashboard">
                <Button size="lg" variant="outline">
                  View Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-5xl mx-auto px-8 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          Powerful Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Quick Start Section */}
      <div className="bg-muted/50 border-y">
        <div className="max-w-5xl mx-auto px-8 py-16">
          <h2 className="text-3xl font-bold text-center mb-8">
            Quick Start Guide
          </h2>
          <div className="space-y-4 max-w-2xl mx-auto">
            <Card>
              <CardContent className="pt-6">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    1
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">Configure Your Vault</h3>
                    <p className="text-sm text-muted-foreground">
                      Go to Settings and set your Obsidian vault path
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    2
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">Choose Your LLM Provider</h3>
                    <p className="text-sm text-muted-foreground">
                      Select between local (Ollama) or cloud providers (Claude, GPT, Gemini)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                    3
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">Start Asking Questions</h3>
                    <p className="text-sm text-muted-foreground">
                      Navigate to Chat and query your knowledge base
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
