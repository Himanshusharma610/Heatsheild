import { apiClient } from './api';
import type { HeatIndexCalculationRequest, HeatIndexResult } from '../features/readings/types';

export const heatRiskService = {
  calculateHeatIndex: async (request: HeatIndexCalculationRequest): Promise<HeatIndexResult> => {
    return apiClient.post<HeatIndexResult>('/readings/calculate-heat-index', request);
  },
};
