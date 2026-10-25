import { useState, useEffect, useRef, useCallback } from 'react';
import { deviceService } from '../services/deviceService';
import { readingService } from '../services/readingService';
import { alertService } from '../services/alertService';
import { heatRiskService } from '../services/heatRiskService';
import type { DeviceData } from '../features/devices/types';
import type { LatestReadingItem, HeatIndexResult } from '../features/readings/types';
import type { AlertData } from '../features/alerts/types';

export interface DashboardData {
  devices: DeviceData[];
  latestReadings: LatestReadingItem[];
  activeAlerts: AlertData[];
  heatIndex: HeatIndexResult | null;
  lastRefreshedAt: Date | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  isCachedStale: boolean;
  pollingIntervalSeconds: number;
  setPollingIntervalSeconds: (seconds: number) => void;
  refreshNow: () => Promise<void>;
  staleThresholdMinutes: number;
}

export function useDashboardData(
  initialPollingSeconds = 15,
  staleThresholdMinutes = 15
): DashboardData {
  const [devices, setDevices] = useState<DeviceData[]>([]);
  const [latestReadings, setLatestReadings] = useState<LatestReadingItem[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<AlertData[]>([]);
  const [heatIndex, setHeatIndex] = useState<HeatIndexResult | null>(null);

  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isCachedStale, setIsCachedStale] = useState<boolean>(false);
  const [pollingIntervalSeconds, setPollingIntervalSeconds] = useState<number>(initialPollingSeconds);

  const isFetchingRef = useRef<boolean>(false);
  const isMountedRef = useRef<boolean>(true);
  const isInitialRef = useRef<boolean>(true);

  const fetchData = useCallback(
    async (isBackground = false) => {
      // Prevent overlapping requests
      if (isFetchingRef.current) return;
      isFetchingRef.current = true;

      if (isBackground) {
        setIsRefreshing(true);
      } else if (!isInitialRef.current) {
        setIsLoading(true);
      }
      isInitialRef.current = false;

      try {
        const [devicesRes, readingsRes, alertsRes] = await Promise.all([
          deviceService.listDevices({ limit: 50 }),
          readingService.getLatestReadings(),
          alertService.listAlerts({ page_size: 20 }),
        ]);

        if (!isMountedRef.current) return;

        const fetchedDevices = devicesRes.data || [];
        const fetchedReadings = readingsRes.data || [];
        const fetchedAlerts = alertsRes.items || [];

        setDevices(fetchedDevices);
        setLatestReadings(fetchedReadings);
        setActiveAlerts(fetchedAlerts);
        setError(null);
        setIsCachedStale(false);
        setLastRefreshedAt(new Date());

        // If a latest reading is available with numeric temperature and humidity, evaluate heat index
        const primaryReading = fetchedReadings[0];
        if (
          primaryReading &&
          typeof primaryReading.temperature_c === 'number' &&
          typeof primaryReading.relative_humidity_pct === 'number'
        ) {
          try {
            const hiRes = await heatRiskService.calculateHeatIndex({
              temperature_c: primaryReading.temperature_c,
              relative_humidity_pct: primaryReading.relative_humidity_pct,
              quality_status: primaryReading.quality_status,
              measured_at: primaryReading.measured_at,
            });
            if (isMountedRef.current) {
              setHeatIndex(hiRes);
            }
          } catch {
            if (isMountedRef.current) {
              setHeatIndex(null);
            }
          }
        } else {
          setHeatIndex(null);
        }
      } catch (err: unknown) {
        if (!isMountedRef.current) return;
        const msg = err instanceof Error ? err.message : 'Failed to fetch dashboard data';
        setError(msg);

        // Retain previous cached data if background refresh failed
        if (isBackground) {
          setIsCachedStale(true);
        }
      } finally {
        isFetchingRef.current = false;
        if (isMountedRef.current) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    },
    []
  );

  const refreshNow = useCallback(async () => {
    await fetchData(true);
  }, [fetchData]);

  // Initial load
  useEffect(() => {
    isMountedRef.current = true;
    fetchData(false);

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchData]);

  // Polling loop
  useEffect(() => {
    if (pollingIntervalSeconds <= 0) return;

    const intervalId = setInterval(() => {
      fetchData(true);
    }, pollingIntervalSeconds * 1000);

    return () => {
      clearInterval(intervalId);
    };
  }, [pollingIntervalSeconds, fetchData]);

  return {
    devices,
    latestReadings,
    activeAlerts,
    heatIndex,
    lastRefreshedAt,
    isLoading,
    isRefreshing,
    error,
    isCachedStale,
    pollingIntervalSeconds,
    setPollingIntervalSeconds,
    refreshNow,
    staleThresholdMinutes,
  };
}
