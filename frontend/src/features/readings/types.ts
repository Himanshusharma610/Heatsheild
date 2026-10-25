/**
 * Telemetry readings and heat-risk calculation contracts.
 * Matches backend schemas in app.schemas.reading and app.schemas.heat_risk.
 */

export type QualityStatus = 'valid' | 'suspect' | 'invalid' | 'missing';

export type HeatIndexScreeningLevel =
  | 'normal'
  | 'caution'
  | 'extreme_caution'
  | 'danger'
  | 'extreme_danger'
  | 'unavailable';

export interface LatestReadingItem {
  id: string;
  device_id: string;
  device_code: string;
  event_id: string;
  measured_at: string | null;
  received_at: string;
  temperature_c: number | null;
  relative_humidity_pct: number | null;
  quality_status: QualityStatus;
  source_mode: 'hardware' | 'simulated';
  firmware_version: string | null;
}

export interface LatestReadingsResponse {
  data: LatestReadingItem[];
}

export interface HeatIndexCalculationRequest {
  temperature_c: number;
  relative_humidity_pct: number;
  quality_status?: QualityStatus;
  measured_at?: string | null;
  allow_extended_range?: boolean;
}

export interface HeatIndexResult {
  status: 'valid' | 'out_of_domain' | 'missing_data' | 'invalid_input' | 'invalid_quality' | 'stale' | 'suspect_quality';
  indicator_name: string;
  value_c: number | null;
  value_f: number | null;
  unit: 'celsius' | 'fahrenheit';
  method: string;
  method_version: string;
  equation_applied: string;
  input_temperature_c: number | null;
  input_temperature_unit: string;
  input_relative_humidity_pct: number | null;
  input_humidity_unit: string;
  informational_screening_level: HeatIndexScreeningLevel;
  custom_classification: string | null;
  limitations: string[];
  notes: string;
  calculated_at: string;
}

export interface ReadingHistoryItem {
  id: string;
  device_id: string;
  device_code: string;
  event_id: string;
  measured_at: string | null;
  received_at: string;
  temperature_c: number | null;
  relative_humidity_pct: number | null;
  quality_status: QualityStatus;
  source_mode: 'hardware' | 'simulated';
  firmware_version: string | null;
  heat_index_c: number | null;
  heat_index_screening_level: HeatIndexScreeningLevel | null;
  heat_index_method: string | null;
}

export interface ReadingSummaryMetric {
  min: number | null;
  max: number | null;
  mean: number | null;
}

export interface ReadingHistorySummary {
  total_readings: number;
  valid_readings_count: number;
  invalid_readings_count: number;
  suspect_readings_count: number;
  missing_readings_count: number;
  temperature_c: ReadingSummaryMetric;
  relative_humidity_pct: ReadingSummaryMetric;
  heat_index_c: ReadingSummaryMetric;
  notes: string;
}

export interface ReadingHistoryPagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ReadingHistoryQueryMeta {
  device_id: string | null;
  worksite_id: string | null;
  start_time: string | null;
  end_time: string | null;
  order_asc: boolean;
  evaluated_at: string;
}

export interface ReadingHistoryResponse {
  data: ReadingHistoryItem[];
  summary: ReadingHistorySummary;
  pagination: ReadingHistoryPagination;
  query: ReadingHistoryQueryMeta;
}

export interface HistoryFilterParams {
  device_id?: string;
  worksite_id?: string;
  start_time?: string;
  end_time?: string;
  quality_status?: QualityStatus;
  order_asc?: boolean;
  limit?: number;
  offset?: number;
}

