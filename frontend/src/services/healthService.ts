import { apiClient } from './api';

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ReadyResponse {
  status: 'ready' | 'not_ready';
  services: {
    database: 'connected' | 'unavailable' | 'not_configured';
  };
  timestamp: string;
}

export const healthService = {
  checkHealth: async (): Promise<HealthResponse> => {
    return apiClient.get<HealthResponse>('/health');
  },

  checkReadiness: async (): Promise<ReadyResponse> => {
    return apiClient.get<ReadyResponse>('/ready');
  },
};
