import { apiClient } from './api';
import type { AlertListResponse, AlertRuleListResponse, AlertSeverity, AlertStatus } from '../features/alerts/types';

export interface AlertFilterParams {
  status?: AlertStatus;
  severity?: AlertSeverity;
  worksite_id?: string;
  device_id?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export const alertService = {
  listAlerts: async (params: AlertFilterParams = {}): Promise<AlertListResponse> => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.severity) query.set('severity', params.severity);
    if (params.worksite_id) query.set('worksite_id', params.worksite_id);
    if (params.device_id) query.set('device_id', params.device_id);
    if (params.start_time) query.set('start_time', params.start_time);
    if (params.end_time) query.set('end_time', params.end_time);
    if (params.page) query.set('page', params.page.toString());
    if (params.page_size) query.set('page_size', params.page_size.toString());

    const qs = query.toString();
    const endpoint = `/alerts${qs ? `?${qs}` : ''}`;
    return apiClient.get<AlertListResponse>(endpoint);
  },


  listAlertRules: async (page = 1, pageSize = 50): Promise<AlertRuleListResponse> => {
    return apiClient.get<AlertRuleListResponse>(`/alert-rules?page=${page}&page_size=${pageSize}`);
  },

  acknowledgeAlert: async (alertId: string, actionTaken: string): Promise<unknown> => {
    return apiClient.post(`/alerts/${alertId}/acknowledge`, { action_taken: actionTaken });
  },

  resolveAlert: async (alertId: string, resolutionNotes?: string): Promise<unknown> => {
    return apiClient.post(`/alerts/${alertId}/resolve`, { resolution_notes: resolutionNotes });
  },
};
