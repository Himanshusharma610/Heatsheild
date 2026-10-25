import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../app/App';
import { EnvironmentalMetricCard } from '../components/dashboard/EnvironmentalMetricCard';
import type { LatestReadingItem } from '../features/readings/types';
import type { AlertData } from '../features/alerts/types';

describe('Module 13: Frontend End-to-End Integration and Flow Verification', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('redirects unauthenticated users attempting to access protected dashboard to /login', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Sign In to HeatShield/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    });
  });

  it('renders live telemetry reading with explicit units (°C and %) and quality status', async () => {
    sessionStorage.setItem('heatshield_auth_token', 'mock-supervisor-token');

    const mockReading: LatestReadingItem = {
      id: 'rdg-integration-001',
      device_id: 'dev-001',
      device_code: 'HS-DEL-01',
      event_id: 'EVT-INT-001',
      temperature_c: 38.2,
      relative_humidity_pct: 65.0,
      quality_status: 'valid',
      source_mode: 'hardware',
      measured_at: new Date(Date.now() - 30000).toISOString(),
      received_at: new Date(Date.now() - 25000).toISOString(),
      firmware_version: '0.3.1',
    };

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            id: 'u-sup-001',
            email: 'supervisor.delhi@heatshield.gov.in',
            display_name: 'Dr. V. Ramanathan',
            role: 'supervisor',
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
      if (url.includes('/readings/latest')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            data: [mockReading],
          }),
        });
      }
      if (url.includes('/devices')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            items: [
              {
                id: 'dev-001',
                device_code: 'HS-DEL-01',
                worksite_id: 'ws-001',
                display_name: 'Anand Vihar Thermal Node',
                status: 'online',
                firmware_version: '0.3.1',
                last_seen_at: new Date().toISOString(),
                is_active: true,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ],
          }),
        });
      }
      if (url.includes('/alerts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            data: [],
            pagination: { total: 0, limit: 50, offset: 0, has_more: false },
          }),
        });
      }
      if (url.includes('/heat-index/calculate')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            heat_index_c: 54.2,
            heat_index_screening_level: 'danger',
            heat_index_status: 'valid',
            heat_index_method: 'rothfusz_nws',
            version: '2026.1',
            data_stale: false,
            data_quality: 'valid',
            advisory: 'Screening advisory: Extreme heat danger.',
          }),
        });
      }
      return Promise.reject(new Error(`Unhandled mock URL: ${url}`));
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    // Verify supervisor identity loaded
    await waitFor(() => {
      expect(screen.getByText('Dr. V. Ramanathan')).toBeInTheDocument();
    });

    // Verify telemetry data and units
    await waitFor(() => {
      expect(screen.getByText('38.2')).toBeInTheDocument();
      expect(screen.getByText('65')).toBeInTheDocument();
      expect(screen.getByText('°C')).toBeInTheDocument();
      expect(screen.getByText('%')).toBeInTheDocument();
    });

    // Verify node code and quality status badge
    expect(screen.getByText(/HS-DEL-01/i)).toBeInTheDocument();
    expect(screen.getByText(/Quality: valid/i)).toBeInTheDocument();
  });

  it('renders "Unavailable" for null measurements and never converts them to 0 or 0.0', () => {
    const partialReading: LatestReadingItem = {
      id: 'rdg-null-001',
      device_id: 'dev-001',
      device_code: 'HS-NULL-TEST',
      event_id: 'EVT-NULL-001',
      temperature_c: null, // Partial sensor failure
      relative_humidity_pct: null,
      quality_status: 'missing',
      source_mode: 'hardware',
      firmware_version: null,
      measured_at: new Date().toISOString(),
      received_at: new Date().toISOString(),
    };

    render(<EnvironmentalMetricCard reading={partialReading} />);

    // Should display 'Unavailable' twice (for temp and humidity)
    const unavailableLabels = screen.getAllByText('Unavailable');
    expect(unavailableLabels.length).toBe(2);

    // CRITICAL: Ensure no 0 or 0.0 is shown as fake measurement
    expect(screen.queryByText('0 °C')).not.toBeInTheDocument();
    expect(screen.queryByText('0.0 °C')).not.toBeInTheDocument();
    expect(screen.queryByText('0 %')).not.toBeInTheDocument();
  });

  it('renders stale data warning badge when telemetry age exceeds threshold', () => {
    const staleReading: LatestReadingItem = {
      id: 'rdg-stale-001',
      device_id: 'dev-001',
      device_code: 'HS-STALE-TEST',
      event_id: 'EVT-STALE-001',
      temperature_c: 33.0,
      relative_humidity_pct: 60.0,
      quality_status: 'valid',
      source_mode: 'hardware',
      firmware_version: '0.3.1',
      // Measured 45 minutes ago (well past the 15-minute threshold)
      measured_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
      received_at: new Date(Date.now() - 44 * 60 * 1000).toISOString(),
    };

    render(<EnvironmentalMetricCard reading={staleReading} staleThresholdMinutes={15} />);

    // Stale data badge must appear
    expect(screen.getByText(/Stale Data/i)).toBeInTheDocument();
  });

  it('enforces RBAC on Alerts page: supervisor sees Acknowledge button while viewer sees restricted notice', async () => {
    const mockAlert: AlertData = {
      id: 'alt-integ-001',
      rule_id: 'rule-01',
      device_id: 'dev-001',
      severity: 'warning',
      status: 'triggered',
      trigger_condition: 'heat_index >= 40.0',
      trigger_value: 44.8,
      triggered_at: new Date().toISOString(),
      rule_version: 1,
      created_at: new Date().toISOString(),
    };

    // First: Test as viewer
    sessionStorage.setItem('heatshield_auth_token', 'mock-viewer-token');

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            id: 'u-viewer-001',
            email: 'viewer.field@heatshield.gov.in',
            display_name: 'A. Field Viewer',
            role: 'viewer', // Read-only
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
      if (url.includes('/alerts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            items: [mockAlert],
            total: 1,
            page: 1,
            page_size: 20,
            pages: 1,
          }),
        });
      }
      if (url.includes('/alert-rules')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ items: [], total: 0 }),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });

    const { unmount } = render(
      <MemoryRouter initialEntries={['/alerts']}>
        <App />
      </MemoryRouter>
    );

    // As viewer, acknowledge button should NOT exist, but "Supervisor Required" notice should appear
    await waitFor(() => {
      expect(screen.getByText('Supervisor Required')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /^Acknowledge$/i })).not.toBeInTheDocument();
    });

    unmount();

    // Second: Test as supervisor
    sessionStorage.setItem('heatshield_auth_token', 'mock-supervisor-token');

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            id: 'u-sup-002',
            email: 'supervisor@heatshield.gov.in',
            display_name: 'B. Field Supervisor',
            role: 'supervisor', // Supervisor
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
      if (url.includes('/alerts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            items: [mockAlert],
            total: 1,
            page: 1,
            page_size: 20,
            pages: 1,
          }),
        });
      }
      if (url.includes('/alert-rules')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ items: [], total: 0 }),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${url}`));
    });

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <App />
      </MemoryRouter>
    );

    // As supervisor, "Acknowledge" button MUST be present
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Acknowledge$/i })).toBeInTheDocument();
    });
  });

  it('renders ErrorState when backend API encounters an unrecoverable failure', async () => {
    sessionStorage.setItem('heatshield_auth_token', 'mock-token');

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            id: 'u-001',
            email: 'test@heatshield.gov.in',
            display_name: 'Test Officer',
            role: 'viewer',
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
      // Simulate backend service failure on alerts endpoint
      if (url.includes('/alerts')) {
        return Promise.resolve({
          ok: false,
          status: 503,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            error: {
              code: 'SERVICE_UNAVAILABLE',
              message: 'Database connection failed',
            },
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ items: [], total: 0 }),
      });
    });

    render(
      <MemoryRouter initialEntries={['/alerts']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Could not load alerts from backend/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry Request/i })).toBeInTheDocument();
    });
  });
});
