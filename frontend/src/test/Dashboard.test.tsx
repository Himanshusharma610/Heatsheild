import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../pages/DashboardPage';
import { EnvironmentalMetricCard } from '../components/dashboard/EnvironmentalMetricCard';
import { HeatIndexCard } from '../components/dashboard/HeatIndexCard';
import { AlertsSummaryCard } from '../components/dashboard/AlertsSummaryCard';
import { DeviceStatusCard } from '../components/dashboard/DeviceStatusCard';
import type { LatestReadingItem, HeatIndexResult } from '../features/readings/types';
import type { DeviceData } from '../features/devices/types';
import type { AlertData } from '../features/alerts/types';

describe('Module 10: Live Monitoring Dashboard & Device Status', () => {
  const mockDevices: DeviceData[] = [
    {
      id: 'dev-001',
      device_code: 'NODE-DELHI-01',
      worksite_id: 'ws-001',
      display_name: 'Delhi Anand Vihar Sensor',
      status: 'online',
      firmware_version: '1.2.0',
      last_seen_at: new Date(Date.now() - 60000).toISOString(),
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'dev-002',
      device_code: 'NODE-MUMBAI-02',
      worksite_id: 'ws-001',
      display_name: 'Mumbai Port Sensor',
      status: 'offline',
      firmware_version: '1.1.0',
      last_seen_at: new Date(Date.now() - 3600000).toISOString(),
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ];

  const mockReading: LatestReadingItem = {
    id: 'rdg-001',
    device_id: 'dev-001',
    device_code: 'NODE-DELHI-01',
    event_id: 'EVT-1001',
    temperature_c: 34.5,
    relative_humidity_pct: 68.0,
    quality_status: 'valid',
    source_mode: 'hardware',
    measured_at: new Date(Date.now() - 120000).toISOString(),
    received_at: new Date(Date.now() - 118000).toISOString(),
    firmware_version: '1.2.0',
  };

  const mockAlerts: AlertData[] = [
    {
      id: 'alt-001',
      rule_id: 'rule-01',
      device_id: 'dev-001',
      severity: 'critical',
      status: 'triggered',
      trigger_value: 41.5,
      trigger_condition: 'heat_index > 40.0 C',
      rule_version: 1,
      triggered_at: new Date(Date.now() - 300000).toISOString(),
      acknowledged_at: null,
      resolved_at: null,
      created_at: new Date(Date.now() - 300000).toISOString(),
    },
  ];

  const mockHeatIndex: HeatIndexResult = {
    status: 'valid',
    indicator_name: 'heat_index',
    value_c: 44.2,
    value_f: 111.6,
    unit: 'celsius',
    method: 'nws_heat_index',
    method_version: '1.0.0',
    equation_applied: 'rothfusz_full',
    input_temperature_c: 34.5,
    input_temperature_unit: 'celsius',
    input_relative_humidity_pct: 68.0,
    input_humidity_unit: 'percent',
    informational_screening_level: 'danger',
    custom_classification: null,
    limitations: ['Environmental screening only. NOT WBGT.'],
    notes: 'Calculated using 16-term regression.',
    calculated_at: new Date().toISOString(),
  };

  const setupFetchMock = (options?: {
    devices?: DeviceData[];
    readings?: LatestReadingItem[];
    alerts?: AlertData[];
    heatIndex?: HeatIndexResult;
    failEndpoints?: string[];
  }) => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const {
        devices = mockDevices,
        readings = [mockReading],
        alerts = mockAlerts,
        heatIndex = mockHeatIndex,
        failEndpoints = [],
      } = options || {};

      if (failEndpoints.some((ep) => url.includes(ep))) {
        return Promise.reject(new Error(`Simulated failure for ${url}`));
      }

      if (url.includes('/devices')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            data: devices,
            meta: { total: devices.length, limit: 50, offset: 0, has_more: false },
          }),
        });
      }

      if (url.includes('/readings/latest')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            data: readings,
            total: readings.length,
            queried_at: new Date().toISOString(),
          }),
        });
      }

      if (url.includes('/readings/calculate-heat-index')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => heatIndex,
        });
      }

      if (url.includes('/alerts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            items: alerts,
            total: alerts.length,
            page: 1,
            page_size: 20,
            pages: 1,
          }),
        });
      }

      return Promise.reject(new Error(`Unhandled mock URL in test: ${url}`));
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // 1. Dashboard rendering with valid API data
  it('1. renders dashboard with valid API data and establishes live monitoring state', async () => {
    setupFetchMock();

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Live Monitoring Connected')).toBeInTheDocument();
    expect(screen.getAllByText('NODE-DELHI-01').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Mumbai Port Sensor')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /live environmental screening/i })).toBeInTheDocument();
  });

  // 2. Correct display of temperature and humidity with units
  it('2. displays temperature in °C and relative humidity in % with explicit units', async () => {
    setupFetchMock();

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    // Look for ambient temperature 34.5 °C and humidity 68 %
    expect(await screen.findByText('34.5')).toBeInTheDocument();
    expect(screen.getAllByText('°C').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('68')).toBeInTheDocument();
    expect(screen.getByText('%')).toBeInTheDocument();
  });

  // 3. Missing or unavailable measurements
  it('3. displays clear "Unavailable" label when measurements are null, without assuming zero', () => {
    const readingWithNulls: LatestReadingItem = {
      ...mockReading,
      temperature_c: null,
      relative_humidity_pct: null,
    };

    render(<EnvironmentalMetricCard reading={readingWithNulls} />);

    const unavailElements = screen.getAllByText('Unavailable');
    expect(unavailElements.length).toBeGreaterThanOrEqual(2);
    // Ensure no false 0 is displayed
    expect(screen.queryByText('0 °C')).not.toBeInTheDocument();
    expect(screen.queryByText('0 %')).not.toBeInTheDocument();
  });

  it('3b. displays empty telemetry state when no reading object exists', () => {
    render(<EnvironmentalMetricCard reading={null} />);

    expect(screen.getByText('No Telemetry Received')).toBeInTheDocument();
    expect(screen.getByText(/no sensor readings are currently recorded/i)).toBeInTheDocument();
  });

  // 4. Empty device list
  it('4. displays honest unconfirmed hardware state when device list is empty', async () => {
    setupFetchMock({ devices: [] });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/no sensor nodes are registered in the backend database/i)).toBeInTheDocument();
    expect(screen.getByText(/physical esp32 boards and environmental sensor modules have not yet been purchased/i)).toBeInTheDocument();
  });

  // 5. Backend request failure
  it('5a. displays ErrorState when initial backend request fails', async () => {
    setupFetchMock({ failEndpoints: ['/devices'] });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/backend connection failed/i)).toBeInTheDocument();
  });

  it('5b. retains previously fetched cached data and shows stale warning banner when background refresh fails', async () => {
    const user = userEvent.setup();
    setupFetchMock();

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    // Initial load succeeds - wait for telemetry data to render
    const initialNodes = await screen.findAllByText('NODE-DELHI-01');
    expect(initialNodes.length).toBeGreaterThanOrEqual(1);

    // Now make subsequent fetch calls fail
    setupFetchMock({ failEndpoints: ['/readings/latest'] });

    // Click Refresh Now
    const refreshBtn = screen.getByRole('button', { name: /refresh dashboard data now/i });
    await user.click(refreshBtn);

    // Should display stale-cached alert banner while keeping NODE-DELHI-01 on screen
    expect(await screen.findByText(/background refresh failed/i)).toBeInTheDocument();
    expect(screen.getAllByText('NODE-DELHI-01').length).toBeGreaterThanOrEqual(1);
  });

  // 6. Invalid API response handling
  it('6. handles malformed/invalid API response safely without throwing unhandled exceptions', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/devices')) {
        // Return 500 server error with HTML or malformed body
        return Promise.resolve({
          ok: false,
          status: 500,
          headers: new Headers({ 'content-type': 'text/plain' }),
          json: async () => ({ error: { code: 'SERVER_ERROR', message: 'Internal Server Error' } }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ data: [] }),
      });
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/backend connection failed/i)).toBeInTheDocument();
  });

  // 7. Stale reading presentation
  it('7. presents explicit Stale Data warning badge when reading timestamp exceeds threshold', () => {
    // 30 minutes old reading
    const thirtyMinutesAgo = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    const staleReading: LatestReadingItem = {
      ...mockReading,
      measured_at: thirtyMinutesAgo,
      received_at: thirtyMinutesAgo,
    };

    render(<EnvironmentalMetricCard reading={staleReading} staleThresholdMinutes={15} />);

    expect(screen.getByText(/stale data/i)).toBeInTheDocument();
    expect(screen.getByText(/30m old/i)).toBeInTheDocument();
  });

  // 8. Unknown device status
  it('8. handles unknown or novel device statuses gracefully without crashing', () => {
    const devicesWithUnknownStatus: DeviceData[] = [
      {
        id: 'dev-unknown',
        device_code: 'NODE-EXPERIMENTAL',
        worksite_id: 'ws-001',
        display_name: 'Experimental Lab Node',
        status: 'provisioning_unknown' as any,
        firmware_version: null,
        last_seen_at: null,
        is_active: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(<DeviceStatusCard devices={devicesWithUnknownStatus} />);

    expect(screen.getByText('NODE-EXPERIMENTAL')).toBeInTheDocument();
    expect(screen.getByText('Never seen')).toBeInTheDocument();
    expect(screen.getByText('Deactivated')).toBeInTheDocument();
  });

  // 9. Refresh behavior without overlapping requests
  it('9. prevents overlapping refresh requests when triggered concurrently', async () => {
    let callCount = 0;
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/devices')) {
        callCount++;
        // Delayed resolution
        return new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                status: 200,
                headers: new Headers({ 'content-type': 'application/json' }),
                json: async () => ({ data: [], meta: { total: 0 } }),
              }),
            50
          )
        );
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ data: [], items: [] }),
      });
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    const refreshBtn = await screen.findByRole('button', { name: /refresh dashboard data now/i });

    // Rapid double click
    user.click(refreshBtn);
    user.click(refreshBtn);

    await waitFor(() => {
      expect(callCount).toBeLessThanOrEqual(2);
    });
  });

  // 10. Polling cleanup on unmount
  it('10. cleans up timer intervals upon component unmount', async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    setupFetchMock();

    const { unmount } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await screen.findByText('Live Monitoring Connected');

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  // 11. No fabricated readings or risk classifications
  it('11. does not display fabricated readings or claim clinical heatstroke diagnosis', () => {
    render(<HeatIndexCard heatIndex={null} />);

    expect(screen.getByText('Indicator Unavailable')).toBeInTheDocument();
    expect(screen.getByText(/an unavailable indicator does not mean conditions are safe/i)).toBeInTheDocument();

    // Verify it doesn't fabricate an arbitrary number
    expect(screen.queryByText(/42\.5\s*°C/)).not.toBeInTheDocument();
    expect(screen.queryByText(/WBGT/)).not.toBeInTheDocument();
  });

  // 12. Correct display of actual indicator and alert statuses when available
  it('12a. displays calculated NWS heat index with scientific limitations and screening tier', () => {
    render(<HeatIndexCard heatIndex={mockHeatIndex} />);

    expect(screen.getByText('44.2')).toBeInTheDocument();
    expect(screen.getByText('(111.6 °F)')).toBeInTheDocument();
    expect(screen.getByText('nws_heat_index')).toBeInTheDocument();
    expect(screen.getByText('rothfusz_full')).toBeInTheDocument();
    expect(screen.getByText(/environmental screening indicator only\. not wet bulb globe temperature/i)).toBeInTheDocument();
  });

  it('12b. displays active alert counts and incident breakdown according to Module 8 schema', () => {
    render(
      <MemoryRouter>
        <AlertsSummaryCard alerts={mockAlerts} />
      </MemoryRouter>
    );

    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1); // active alert count
    expect(screen.getByText('heat_index > 40.0 C')).toBeInTheDocument();
  });
});
