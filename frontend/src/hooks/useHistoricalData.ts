import { useState, useEffect, useRef, useCallback } from 'react';
import { readingService } from '../services/readingService';
import { deviceService } from '../services/deviceService';
import { alertService } from '../services/alertService';
import type { DeviceData } from '../features/devices/types';
import type {
  ReadingHistoryItem,
  ReadingHistorySummary,
  ReadingHistoryPagination,
  HistoryFilterParams,
} from '../features/readings/types';
import type { AlertData } from '../features/alerts/types';

export type TimePreset = '24h' | '7d' | '30d' | 'custom';

export interface UseHistoricalDataResult {
  devices: DeviceData[];
  selectedDeviceId: string;
  setSelectedDeviceId: (id: string) => void;
  timePreset: TimePreset;
  setTimePreset: (preset: TimePreset) => void;
  customStartDate: string;
  setCustomStartDate: (val: string) => void;
  customEndDate: string;
  setCustomEndDate: (val: string) => void;
  readings: ReadingHistoryItem[];
  summary: ReadingHistorySummary | null;
  pagination: ReadingHistoryPagination | null;
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  isLoading: boolean;
  error: string | null;
  validationError: string | null;
  alertHistory: AlertData[];
  isLoadingAlerts: boolean;
  refetch: () => Promise<void>;
}

export function useHistoricalData(initialPageSize = 100): UseHistoricalDataResult {
  const [devices, setDevices] = useState<DeviceData[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [timePreset, setTimePreset] = useState<TimePreset>('24h');
  
  // Custom range formatted as YYYY-MM-DDTHH:mm
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');

  const [readings, setReadings] = useState<ReadingHistoryItem[]>([]);
  const [summary, setSummary] = useState<ReadingHistorySummary | null>(null);
  const [pagination, setPagination] = useState<ReadingHistoryPagination | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(initialPageSize);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [alertHistory, setAlertHistory] = useState<AlertData[]>([]);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState<boolean>(false);

  const isMountedRef = useRef<boolean>(true);

  // Compute UTC start/end ISO strings based on preset or custom dates
  const computeTimeRange = useCallback((): { start?: string; end?: string; validationErr?: string } => {
    const now = new Date();

    if (timePreset === '24h') {
      const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      return { start: start.toISOString(), end: now.toISOString() };
    }
    if (timePreset === '7d') {
      const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return { start: start.toISOString(), end: now.toISOString() };
    }
    if (timePreset === '30d') {
      const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      return { start: start.toISOString(), end: now.toISOString() };
    }
    if (timePreset === 'custom') {
      if (!customStartDate || !customEndDate) {
        return { validationErr: 'Both start and end dates are required for custom range.' };
      }
      const s = new Date(customStartDate);
      const e = new Date(customEndDate);
      if (isNaN(s.getTime()) || isNaN(e.getTime())) {
        return { validationErr: 'Invalid date/time format.' };
      }
      if (s > e) {
        return { validationErr: 'Start date must be earlier than or equal to end date.' };
      }
      const diffDays = (e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        return { validationErr: 'Custom date range cannot exceed 30 days.' };
      }
      return { start: s.toISOString(), end: e.toISOString() };
    }
    return {};
  }, [timePreset, customStartDate, customEndDate]);

  // Load devices list once
  useEffect(() => {
    let active = true;
    deviceService
      .listDevices({ limit: 100 })
      .then((res) => {
        if (active) {
          setDevices(res.data || []);
        }
      })
      .catch(() => {
        // Soft fail; device filter can remain empty
      });
    return () => {
      active = false;
    };
  }, []);


  // Main data fetcher
  const fetchHistoricalData = useCallback(async () => {
    const { start, end, validationErr } = computeTimeRange();
    if (validationErr) {
      setValidationError(validationErr);
      setReadings([]);
      setSummary(null);
      setPagination(null);
      setIsLoading(false);
      return;
    }

    setValidationError(null);
    setIsLoading(true);
    setError(null);

    try {
      const params: HistoryFilterParams = {
        start_time: start,
        end_time: end,
        order_asc: true, // Deterministic chronological order for time-series charts
        limit: pageSize,
        offset: (page - 1) * pageSize,
      };
      if (selectedDeviceId) {
        params.device_id = selectedDeviceId;
      }

      const res = await readingService.getHistoricalReadings(params);

      if (isMountedRef.current) {
        setReadings(res.data);
        setSummary(res.summary);
        setPagination(res.pagination);
        setError(null);
      }
    } catch (err: unknown) {
      if (isMountedRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to retrieve historical readings.';
        setError(message);
        setReadings([]);
        setSummary(null);
        setPagination(null);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [computeTimeRange, pageSize, page, selectedDeviceId]);

  // Alert history fetcher
  const fetchAlertHistory = useCallback(async () => {
    const { start, end, validationErr } = computeTimeRange();
    if (validationErr) return;

    setIsLoadingAlerts(true);
    try {
      const res = await alertService.listAlerts({
        device_id: selectedDeviceId || undefined,
        start_time: start,
        end_time: end,
        page: 1,
        page_size: 50,
      });
      if (isMountedRef.current) {
        setAlertHistory(res.items || []);
      }
    } catch {
      if (isMountedRef.current) {
        setAlertHistory([]);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoadingAlerts(false);
      }
    }
  }, [computeTimeRange, selectedDeviceId]);

  // Refetch when filters or pagination change
  useEffect(() => {
    isMountedRef.current = true;
    queueMicrotask(() => {
      if (isMountedRef.current) {
        fetchHistoricalData();
        fetchAlertHistory();
      }
    });

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchHistoricalData, fetchAlertHistory]);


  const handleDeviceChange = (id: string) => {
    setSelectedDeviceId(id);
    setPage(1);
  };

  const handlePresetChange = (preset: TimePreset) => {
    setTimePreset(preset);
    setPage(1);
  };

  return {
    devices,
    selectedDeviceId,
    setSelectedDeviceId: handleDeviceChange,
    timePreset,
    setTimePreset: handlePresetChange,
    customStartDate,
    setCustomStartDate,
    customEndDate,
    setCustomEndDate,
    readings,
    summary,
    pagination,
    page,
    setPage,
    pageSize,
    isLoading,
    error,
    validationError,
    alertHistory,
    isLoadingAlerts,
    refetch: fetchHistoricalData,
  };
}
