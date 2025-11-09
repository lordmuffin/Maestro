// Base API response types
export interface ApiResponse<T = any> {
  status: string
  data?: T
  error?: string
  message?: string
}

// Supervisor API types
export interface ExecuteTaskRequest {
  query: string
  sensitivity?: 'low' | 'medium' | 'high'
  task_type?: string
  llm_provider?: string
  model_tier?: string
}

export interface ExecuteTaskResponse {
  status: string
  result: {
    response?: string
    data?: any
  }
  agent_used: string
  execution_time?: number
  provider_used?: string
  model_used?: string
  privacy_warning?: string
  timestamp?: string
}

export interface AgentStatus {
  name: string
  status: 'active' | 'inactive' | 'error'
  last_used?: string
  total_queries?: number
}

// RAG API types
export interface QueryRequest {
  query: string
  top_k?: number
  filter?: Record<string, any>
}

export interface QueryResponse {
  results: Array<{
    content: string
    metadata: Record<string, any>
    score: number
  }>
  query_time: number
}

export interface IndexStatus {
  total_documents: number
  last_updated: string
  index_size: string
}

// Path Mapping API types
export interface PathMappingResponse {
  mapped_paths: string[]
  unmapped_paths: string[]
  vault_root: string
}

// Skills API types
export interface SkillDefinition {
  name: string
  description: string
  parameters: Record<string, any>
  enabled: boolean
}

export interface SkillExecutionRequest {
  skill_name: string
  parameters: Record<string, any>
}

export interface SkillExecutionResponse {
  status: string
  result: any
  execution_time: number
}

// Evaluation API types
export interface EvaluationRequest {
  query: string
  response: string
  ground_truth?: string
}

export interface EvaluationResponse {
  accuracy_score: number
  relevance_score: number
  completeness_score: number
  overall_score: number
  feedback: string
}
