import { apiClient } from './api';
import type { DeviceListResponse } from '../features/devices/types';

export interface DeviceQueryParams {
  worksite_id?: string;
  status?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export const deviceService = {
  listDevices: async (params: DeviceQueryParams = {}): Promise<DeviceListResponse> => {
    const query = new URLSearchParams();
    if (params.worksite_id) query.set('worksite_id', params.worksite_id);
    if (params.status) query.set('status', params.status);
    if (params.is_active !== undefined) query.set('is_active', String(params.is_active));
    if (params.limit) query.set('limit', params.limit.toString());
    if (params.offset) query.set('offset', params.offset.toString());

    const qs = query.toString();
    const endpoint = `/devices${qs ? `?${qs}` : ''}`;
    return apiClient.get<DeviceListResponse>(endpoint);
  },
};
