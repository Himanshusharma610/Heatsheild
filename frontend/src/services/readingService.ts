import { apiClient } from './api';
import type {
  HistoryFilterParams,
  LatestReadingsResponse,
  ReadingHistoryResponse,
} from '../features/readings/types';

export interface LatestReadingQueryParams {
  device_id?: string;
  worksite_id?: string;
  quality_status?: string;
}

export const readingService = {
  getLatestReadings: async (params: LatestReadingQueryParams = {}): Promise<LatestReadingsResponse> => {
    const query = new URLSearchParams();
    if (params.device_id) query.set('device_id', params.device_id);
    if (params.worksite_id) query.set('worksite_id', params.worksite_id);
    if (params.quality_status) query.set('quality_status', params.quality_status);

    const qs = query.toString();
    const endpoint = `/readings/latest${qs ? `?${qs}` : ''}`;
    return apiClient.get<LatestReadingsResponse>(endpoint);
  },

  getHistoricalReadings: async (params: HistoryFilterParams = {}): Promise<ReadingHistoryResponse> => {
    const query = new URLSearchParams();
    if (params.device_id) query.set('device_id', params.device_id);
    if (params.worksite_id) query.set('worksite_id', params.worksite_id);
    if (params.start_time) query.set('start_time', params.start_time);
    if (params.end_time) query.set('end_time', params.end_time);
    if (params.quality_status) query.set('quality_status', params.quality_status);
    if (params.order_asc !== undefined) query.set('order_asc', String(params.order_asc));
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));

    const qs = query.toString();
    const endpoint = `/readings/history${qs ? `?${qs}` : ''}`;
    return apiClient.get<ReadingHistoryResponse>(endpoint);
  },
};

