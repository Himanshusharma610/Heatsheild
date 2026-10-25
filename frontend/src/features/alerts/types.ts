/**
 * Alert and Alert Rule contracts.
 * Matches backend schemas in app.schemas.alert.
 */

export type AlertSeverity = 'info' | 'warning' | 'critical';

export type AlertStatus = 'triggered' | 'acknowledged' | 'resolved' | 'expired';

export type RuleOperator = 'gt' | 'gte' | 'lt' | 'lte' | 'eq';

export type RuleMetric = 'temperature_c' | 'relative_humidity_pct' | 'heat_index_c';

export interface AlertRuleData {
  id: string;
  name: string;
  metric: RuleMetric;
  operator: RuleOperator;
  threshold: number;
  severity: AlertSeverity;
  worksite_id?: string | null;
  device_id?: string | null;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleListResponse {
  items: AlertRuleData[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AlertData {
  id: string;
  rule_id: string;
  device_id: string;
  worksite_id?: string | null;
  reading_id?: string | null;
  severity: AlertSeverity;
  status: AlertStatus;
  trigger_value: number;
  trigger_condition: string;
  rule_version: number;
  triggered_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  created_at: string;
  rule_name?: string | null;
  device_code?: string | null;
}

export interface AlertListResponse {
  items: AlertData[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AlertAcknowledgeRequest {
  action_taken: string;
  notes?: string | null;
}

export interface AlertResolveRequest {
  resolution_notes?: string | null;
}
