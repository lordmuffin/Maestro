import { apiClient } from './client';

export interface ExecuteTaskRequest {
  query: string;
  sensitivity?: 'low' | 'medium' | 'high';
  task_type?: string;
  llm_provider?: string;
  model_tier?: string;
}

export interface ExecuteTaskResponse {
  status: string;
  result: any;
  agent_used: string;
  execution_time?: number;
  provider_used?: string;
  model_used?: string;
  privacy_warning?: string;
}

export const supervisorAPI = {
  execute: async (request: ExecuteTaskRequest): Promise<ExecuteTaskResponse> => {
    const { data } = await apiClient.post('/supervisor/execute', request);
    return data;
  },

  getAgentStatus: async () => {
    const { data } = await apiClient.get('/supervisor/agents');
    return data;
  }
};
