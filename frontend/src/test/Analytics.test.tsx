import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';

import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { TimeSeriesChart } from '../components/analytics/TimeSeriesChart';
import { AnalyticsSummaryCards } from '../components/analytics/AnalyticsSummaryCards';
import type { ReadingHistoryItem, ReadingHistoryResponse, ReadingHistorySummary } from '../features/readings/types';
import type { DeviceData } from '../features/devices/types';
import type { AlertData } from '../features/alerts/types';

describe('Module 11: Historical Data, Charts & Analytics', () => {
  const mockDevices: DeviceData[] = [
    {
      id: 'dev-001',
      device_code: 'NODE-JP01-D001',
      worksite_id: 'ws-001',
      display_name: 'Tower Crane Sensor',
      status: 'online',
      firmware_version: '1.2.0',
      last_seen_at: '2026-10-25T10:00:00Z',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'dev-002',
      device_code: 'NODE-JP01-D002',
      worksite_id: 'ws-001',
      display_name: 'Ground Station Sensor',
      status: 'online',
      firmware_version: '1.2.0',
      last_seen_at: '2026-10-25T10:00:00Z',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ];

  const mockHistoricalReadings: ReadingHistoryItem[] = [
    {
      id: 'rdg-h1',
      device_id: 'dev-001',
      device_code: 'NODE-JP01-D001',
      event_id: 'evt-001',
      measured_at: '2026-10-25T08:00:00Z',
      received_at: '2026-10-25T08:00:02Z',
      temperature_c: 32.0,
      relative_humidity_pct: 55.0,
      quality_status: 'valid',
      source_mode: 'hardware',
      firmware_version: '1.2.0',
      heat_index_c: 36.5,
      heat_index_screening_level: 'caution',
      heat_index_method: 'nws_rothfusz_v1',
    },
    {
      id: 'rdg-h2',
      device_id: 'dev-001',
      device_code: 'NODE-JP01-D001',
      event_id: 'evt-002',
      measured_at: '2026-10-25T08:15:00Z',
      received_at: '2026-10-25T08:15:02Z',
      temperature_c: 34.0,
      relative_humidity_pct: 60.0,
      quality_status: 'valid',
      source_mode: 'hardware',
      firmware_version: '1.2.0',
      heat_index_c: 41.2,
      heat_index_screening_level: 'extreme_caution',
      heat_index_method: 'nws_rothfusz_v1',
    },
    {
      id: 'rdg-h3',
      device_id: 'dev-001',
      device_code: 'NODE-JP01-D001',
      event_id: 'evt-003',
      measured_at: '2026-10-25T08:30:00Z',
      received_at: '2026-10-25T08:30:02Z',
      temperature_c: null,
      relative_humidity_pct: null,
      quality_status: 'missing',
      source_mode: 'hardware',
      firmware_version: '1.2.0',
      heat_index_c: null,
      heat_index_screening_level: null,
      heat_index_method: null,
    },
    {
      id: 'rdg-h4',
      device_id: 'dev-001',
      device_code: 'NODE-JP01-D001',
      event_id: 'evt-004',
      measured_at: '2026-10-25T08:45:00Z',
      received_at: '2026-10-25T08:45:02Z',
      temperature_c: 36.0,
      relative_humidity_pct: 65.0,
      quality_status: 'valid',
      source_mode: 'hardware',
      firmware_version: '1.2.0',
      heat_index_c: 46.8,
      heat_index_screening_level: 'danger',
      heat_index_method: 'nws_rothfusz_v1',
    },
  ];

  const mockSummary: ReadingHistorySummary = {
    total_readings: 4,
    valid_readings_count: 3,
    invalid_readings_count: 0,
    suspect_readings_count: 0,
    missing_readings_count: 1,
    temperature_c: { min: 32.0, max: 36.0, mean: 34.0 },
    relative_humidity_pct: { min: 55.0, max: 65.0, mean: 60.0 },
    heat_index_c: { min: 36.5, max: 46.8, mean: 41.5 },
    notes: 'Summary statistics computed exclusively from 3 valid readings. 1 invalid or missing readings excluded from averages.',
  };

  const mockHistoryResponse: ReadingHistoryResponse = {
    data: mockHistoricalReadings,
    summary: mockSummary,
    pagination: {
      total: 4,
      limit: 100,
      offset: 0,
      has_more: false,
    },
    query: {
      device_id: null,
      worksite_id: null,
      start_time: '2026-10-24T08:00:00Z',
      end_time: '2026-10-25T08:00:00Z',
      order_asc: true,
      evaluated_at: '2026-10-25T09:00:00Z',
    },
  };

  const mockAlerts: AlertData[] = [
    {
      id: 'alt-001',
      rule_id: 'rule-01',
      device_id: 'dev-001',
      severity: 'warning',
      status: 'triggered',
      trigger_value: 36.5,
      trigger_condition: 'heat_index > 35.0 C',
      rule_version: 1,
      triggered_at: '2026-10-25T08:05:00Z',
      acknowledged_at: null,
      resolved_at: null,
      created_at: '2026-10-25T08:05:00Z',
      device_code: 'NODE-JP01-D001',
    },
  ];

  const setupMockFetch = (options?: {
    history?: ReadingHistoryResponse;
    devices?: DeviceData[];
    alerts?: AlertData[];
    failHistory?: boolean;
  }) => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const {

        history = mockHistoryResponse,
        devices = mockDevices,
        alerts = mockAlerts,
        failHistory = false,
      } = options || {};

      if (failHistory && url.includes('/readings/history')) {
        return Promise.reject(new Error('Backend Database Unavailable'));
      }


      const createResponse = (body: unknown) =>
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });


      if (url.includes('/readings/history')) {
        return Promise.resolve(createResponse(history));
      }

      if (url.includes('/devices')) {
        return Promise.resolve(createResponse({ data: devices, pagination: { total: devices.length, limit: 100, offset: 0, has_more: false } }));
      }

      if (url.includes('/alerts')) {
        return Promise.resolve(createResponse({ items: alerts, total: alerts.length, page: 1, page_size: 50, pages: 1 }));
      }

      return Promise.resolve(createResponse({}));
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });


  it('1. Renders historical data page with page title, controls, and descriptive summaries', async () => {
    setupMockFetch();

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    // Verify page header
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Historical Data, Charts & Analytics/i);

    // Verify summary statistics render
    await waitFor(() => {
      expect(screen.getByText('34.0 °C')).toBeInTheDocument();
      expect(screen.getByText('60.0 %')).toBeInTheDocument();
      expect(screen.getByText('41.5 °C')).toBeInTheDocument();
    });

    // Verify integrity disclaimer
    expect(screen.getByText(/Data Integrity Note:/i)).toBeInTheDocument();
    expect(screen.getByText(/Descriptive statistics are for environmental screening/i)).toBeInTheDocument();
  });

  it('2. Switches time-range presets (24h, 7d, 30d, custom)', async () => {
    const user = userEvent.setup();
    setupMockFetch();

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    const btn7d = screen.getByRole('button', { name: '7 Days' });
    const btn30d = screen.getByRole('button', { name: '30 Days (Max)' });
    const btnCustom = screen.getByRole('button', { name: 'Custom Range' });

    expect(screen.getByRole('button', { name: '24 Hours' })).toHaveClass('active');

    // Click 7 Days
    await user.click(btn7d);
    expect(btn7d).toHaveClass('active');

    // Click 30 Days
    await user.click(btn30d);
    expect(btn30d).toHaveClass('active');

    // Click Custom Range
    await user.click(btnCustom);
    expect(btnCustom).toHaveClass('active');
    expect(screen.getByLabelText(/Start Date\/Time:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/End Date\/Time:/i)).toBeInTheDocument();
  });

  it('3. Renders temperature and relative humidity trend charts with correct units', async () => {
    setupMockFetch();

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Ambient Temperature Trend')).toBeInTheDocument();
      expect(screen.getByText('Relative Humidity Trend')).toBeInTheDocument();
      expect(screen.getByText('Calculated Heat Index Trend')).toBeInTheDocument();
    });

    // Verify units are labeled
    expect(screen.getAllByText('°C').length).toBeGreaterThan(0);
    expect(screen.getAllByText('%').length).toBeGreaterThan(0);

    // Heat Index must be transparently identified as NOAA Rothfusz, not WBGT
    expect(screen.getByText('NOAA Rothfusz (Not WBGT)')).toBeInTheDocument();
  });

  it('4. Displays honest empty-history state when no readings match criteria', async () => {
    const emptyResponse: ReadingHistoryResponse = {
      data: [],
      summary: {
        total_readings: 0,
        valid_readings_count: 0,
        invalid_readings_count: 0,
        suspect_readings_count: 0,
        missing_readings_count: 0,
        temperature_c: { min: null, max: null, mean: null },
        relative_humidity_pct: { min: null, max: null, mean: null },
        heat_index_c: { min: null, max: null, mean: null },
        notes: 'No readings found.',
      },
      pagination: { total: 0, limit: 100, offset: 0, has_more: false },
      query: { ...mockHistoryResponse.query },
    };

    setupMockFetch({ history: emptyResponse });

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/No Historical Readings Recorded/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/No sensor readings available in the selected time range/i)).toBeInTheDocument();
    });
  });

  it('5. Handles API query failure with error banner and avoids crashing', async () => {
    setupMockFetch({ failHistory: true });

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Backend Database Unavailable/i)).toBeInTheDocument();
    });
  });

  it('6. Handles missing values without substituting false zeroes in charts and tables', async () => {
    const user = userEvent.setup();

    // Isolated TimeSeriesChart component test
    render(
      <TimeSeriesChart
        data={mockHistoricalReadings}
        metric="temperature"
        title="Ambient Temperature Trend"
        unit="°C"
        colorHex="#f59e0b"
      />
    );

    // Click Table View toggle to verify data representation
    const tableBtn = screen.getByRole('button', { name: 'Table View' });
    await user.click(tableBtn);

    await waitFor(() => {
      // The 3rd reading has null temperature; it must display 'Missing / None', never '0.0 °C'
      expect(screen.getByText('Missing / None')).toBeInTheDocument();
      expect(screen.queryByText('0.0 °C')).not.toBeInTheDocument();
    });
  });


  it('7. Displays measurement timestamps separately from server receipt timestamps', async () => {
    const user = userEvent.setup();
    setupMockFetch();

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('34.0 °C')).toBeInTheDocument();
    });

    const tabTable = screen.getByRole('tab', { name: /Historical Telemetry Log/i });
    await user.click(tabTable);

    await waitFor(() => {
      expect(screen.getByText('Historical Sensor Telemetry Log')).toBeInTheDocument();
      expect(screen.getByText('Measurement Time (RTC)')).toBeInTheDocument();
      expect(screen.getByText('Server Received (UTC)')).toBeInTheDocument();
      expect(screen.getAllByText('NODE-JP01-D001').length).toBeGreaterThan(0);
    });
  });





  it('8. Renders summary statistics with min, max, and mean and explicit data quality indicators', () => {
    render(<AnalyticsSummaryCards summary={mockSummary} isLoading={false} />);

    // Temperature metrics
    expect(screen.getByText('34.0 °C')).toBeInTheDocument();
    expect(screen.getByText('32.0 °C')).toBeInTheDocument();
    expect(screen.getByText('36.0 °C')).toBeInTheDocument();

    // Coverage & Quality
    expect(screen.getByText('75% Valid')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // valid count
  });

  it('9. Handles insufficient valid data (< 2 points) by warning rather than extrapolating misleading lines', () => {
    const singlePointData: ReadingHistoryItem[] = [mockHistoricalReadings[0]];

    render(
      <TimeSeriesChart
        data={singlePointData}
        metric="temperature"
        title="Ambient Temperature Trend"
        unit="°C"
        colorHex="#f59e0b"
      />
    );

    expect(screen.getByText(/Insufficient Valid Readings for Trend/i)).toBeInTheDocument();
    expect(screen.getByText(/At least 2 valid points are required to plot a continuous trend/i)).toBeInTheDocument();
  });

  it('10. Renders historical alert events tab showing persisted alerts, trigger values, and status', async () => {
    const user = userEvent.setup();
    setupMockFetch();

    render(
      <MemoryRouter>
        <AnalyticsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('34.0 °C')).toBeInTheDocument();
    });

    // Switch to Alert History tab
    const tabAlerts = screen.getByRole('tab', { name: /Alert History/i });
    await user.click(tabAlerts);

    await waitFor(() => {
      expect(screen.getByText('Historical Alert Events')).toBeInTheDocument();
      expect(screen.getByText('heat_index > 35.0 C')).toBeInTheDocument();
      expect(screen.getByText('warning')).toBeInTheDocument();
    });
  });

});
