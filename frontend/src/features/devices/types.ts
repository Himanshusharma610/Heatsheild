/**
 * Device domain types.
 * Matches backend schemas in app.schemas.device and app.models.device.
 */

export type DeviceSourceMode = 'hardware' | 'simulated' | 'diagnostic' | 'fallback';

export type DeviceStatus = 'registered' | 'online' | 'offline' | 'deactivated';

export interface DeviceData {
  id: string;
  device_code: string;
  worksite_id: string;
  display_name: string | null;
  status: DeviceStatus;
  firmware_version: string | null;
  last_seen_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface DeviceListResponse {
  data: DeviceData[];
  pagination: PaginationMeta;
}

export interface DeviceStatusSummary {
  total: number;
  online: number;
  offline: number;
  registered: number;
  deactivated: number;
}
