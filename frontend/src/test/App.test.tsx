import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../app/App';
import { LoadingState } from '../components/feedback/LoadingState';
import { ErrorState } from '../components/feedback/ErrorState';
import { EmptyState } from '../components/feedback/EmptyState';
import { StatusBadge } from '../components/feedback/StatusBadge';

describe('Frontend Foundation Application & Routing', () => {
  beforeEach(() => {
    sessionStorage.setItem('heatshield_auth_token', 'mock-valid-jwt');
    // Mock health/readiness probe network calls so tests run deterministically
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            id: 'a0000000-0000-0000-0000-000000000001',
            email: 'supervisor@heatshield.gov.in',
            display_name: 'Test Supervisor',
            role: 'supervisor',
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
      if (url.includes('/ready')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            status: 'ready',
            services: { database: 'connected' },
            timestamp: new Date().toISOString(),
          }),
        });
      }
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            status: 'healthy',
            version: '0.1.0',
            timestamp: new Date().toISOString(),
          }),
        });
      }
      if (url.includes('/alerts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            items: [],
            total: 0,
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
          json: async () => ({
            items: [],
            total: 0,
            page: 1,
            page_size: 50,
            pages: 1,
          }),
        });
      }
      if (url.includes('/devices')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            data: [],
            meta: { total: 0, limit: 50, offset: 0, has_more: false },
          }),
        });
      }
      if (url.includes('/readings/latest')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            data: [],
            total: 0,
            queried_at: new Date().toISOString(),
          }),
        });
      }
      return Promise.reject(new Error(`Unhandled mock for ${url}`));
    });
  });

  it('renders the application shell, title, and navigation elements', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText('HeatShield Bharat')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { level: 1, name: /system overview & architecture status/i })).toBeInTheDocument();

    const nav = screen.getByRole('navigation', { name: /main navigation/i });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^dashboard$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^overview$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^devices$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^alerts$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^risk calculator$/i })).toBeInTheDocument();

    // Settle async readiness probe
    expect(await screen.findByText('Connected (DB Ready)')).toBeInTheDocument();
  });

  it('navigates to the Devices page and displays honest unconfirmed hardware state without fake sensor data', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    const devicesLink = screen.getByRole('link', { name: /^devices$/i });
    await user.click(devicesLink);

    expect(screen.getByRole('heading', { level: 1, name: /hardware devices & sensor nodes/i })).toBeInTheDocument();
    expect(screen.getByText(/physical hardware unconfirmed/i)).toBeInTheDocument();
    expect(screen.getByText(/no connected physical devices/i)).toBeInTheDocument();
    // Verify no fabricated telemetry or fake reading counts are present
    expect(screen.queryByText(/42\.5\s*°C/)).not.toBeInTheDocument();
  });

  it('navigates to the Alerts page with real API integration and empty state', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    const alertsLink = screen.getByRole('link', { name: /^alerts$/i });
    await user.click(alertsLink);

    expect(screen.getByRole('heading', { level: 1, name: /active alerts & configured rules/i })).toBeInTheDocument();
    expect(await screen.findByText(/no active alerts/i)).toBeInTheDocument();
  });

  it('navigates to the Risk Calculator page and allows testing', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    const calcLink = screen.getByRole('link', { name: /^risk calculator$/i });
    await user.click(calcLink);

    expect(screen.getByRole('heading', { level: 1, name: /heat-risk calculation testbench/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/dry-bulb ambient temperature/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/relative humidity/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /calculate heat index/i })).toBeInTheDocument();
  });

  it('renders the Not Found page when navigating to an unknown route', async () => {
    render(
      <MemoryRouter initialEntries={['/unmatched/random-path-404']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /404 — page not found/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /return to system overview/i })).toBeInTheDocument();
    expect(await screen.findByText('Connected (DB Ready)')).toBeInTheDocument();
  });

  it('renders LoadingState, ErrorState, EmptyState, and StatusBadge with correct accessible semantics', () => {
    const { rerender } = render(<LoadingState message="Testing loading spinner..." />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Testing loading spinner...')).toBeInTheDocument();

    const onRetry = vi.fn();
    rerender(<ErrorState title="Test Failure" message="Network dropped" onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Test Failure')).toBeInTheDocument();
    expect(screen.getByText('Network dropped')).toBeInTheDocument();

    rerender(<EmptyState title="Empty Records" description="No items available" />);
    expect(screen.getByText('Empty Records')).toBeInTheDocument();
    expect(screen.getByText('No items available')).toBeInTheDocument();

    rerender(<StatusBadge status="warning" label="Borderline Heat" />);
    expect(screen.getByLabelText('Status: Borderline Heat')).toBeInTheDocument();
  });
});
