import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { LoginPage } from '../pages/LoginPage';
import { AlertsPage } from '../pages/AlertsPage';
import { Header } from '../components/layout/Header';
import { getAuthToken, setAuthToken } from '../services/api';

describe('Module 12: Frontend Authentication and Role-Based Access Control', () => {
  beforeEach(() => {
    sessionStorage.clear();
    setAuthToken(null);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
    setAuthToken(null);
  });

  // ============================================================================
  // Scenario 16: Login and logout states render correctly
  // ============================================================================
  it('renders login form, validates credentials, and submits successfully', async () => {
    const user = userEvent.setup();

    globalThis.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/auth/login') && options?.method === 'POST') {
        const body = JSON.parse(options.body as string);
        if (body.email === 'supervisor@heatshield.gov.in' && body.password === 'ValidPass123!') {
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({
              access_token: 'valid-jwt-token-123',
              token_type: 'bearer',
              expires_in: 28800,
              user: {
                id: '11111111-1111-1111-1111-111111111111',
                email: 'supervisor@heatshield.gov.in',
                display_name: 'Supervisor Rao',
                role: 'supervisor',
                is_active: true,
                created_at: new Date().toISOString(),
              },
            }),
          });
        }
        return Promise.resolve({
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            error: {
              code: 'UNAUTHORIZED',
              message: 'Invalid email or password.',
            },
          }),
        });
      }
      return Promise.reject(new Error(`Unhandled mock for ${url}`));
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div>Target Dashboard Page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Verify form elements
    expect(screen.getByRole('heading', { name: /sign in to heatshield/i })).toBeInTheDocument();
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    // 1. Submit with invalid password -> Error alert displayed
    await user.type(emailInput, 'supervisor@heatshield.gov.in');
    await user.type(passwordInput, 'WrongPassword!');
    await user.click(submitBtn);

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i);

    // 2. Submit with valid credentials -> Success & Token stored in sessionStorage
    await user.clear(passwordInput);
    await user.type(passwordInput, 'ValidPass123!');
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Target Dashboard Page')).toBeInTheDocument();
    });
    expect(getAuthToken()).toBe('valid-jwt-token-123');
  });

  // ============================================================================
  // Scenario 17: Protected routes behave correctly
  // ============================================================================
  it('redirects unauthenticated users to /login and allows authenticated users', async () => {
    // Unauthenticated user attempting to access protected dashboard
    const { unmount } = render(
      <MemoryRouter initialEntries={['/protected-dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page Stand-in</div>} />
            <Route
              path="/protected-dashboard"
              element={
                <ProtectedRoute>
                  <div>Secret Supervisory Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Should immediately navigate to /login
    expect(screen.getByText('Login Page Stand-in')).toBeInTheDocument();
    expect(screen.queryByText('Secret Supervisory Dashboard')).not.toBeInTheDocument();
    unmount();

    // Authenticated user with token and valid session
    sessionStorage.setItem('heatshield_auth_token', 'active-session-token');
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            id: '22222222-2222-2222-2222-222222222222',
            email: 'admin@heatshield.gov.in',
            display_name: 'Director Admin',
            role: 'admin',
            is_active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
      return Promise.reject(new Error(`Unhandled mock ${url}`));
    });

    render(
      <MemoryRouter initialEntries={['/protected-dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page Stand-in</div>} />
            <Route
              path="/protected-dashboard"
              element={
                <ProtectedRoute>
                  <div>Secret Supervisory Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Secret Supervisory Dashboard')).toBeInTheDocument();
  });

  // ============================================================================
  // Scenario 18: Expired or invalid sessions are handled
  // ============================================================================
  it('handles expired session by clearing token and updating Header state', async () => {
    sessionStorage.setItem('heatshield_auth_token', 'expired-token');

    // /auth/me returns 401 expired
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/auth/me') || url.includes('/ready')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            error: {
              code: 'UNAUTHORIZED',
              message: 'Authentication token has expired.',
            },
          }),
        });
      }
      return Promise.reject(new Error(`Unhandled mock ${url}`));
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <Header />
        </AuthProvider>
      </MemoryRouter>
    );

    // Expect header to transition to unauthenticated (Sign In link displayed)
    expect(await screen.findByRole('link', { name: /sign in/i })).toBeInTheDocument();
    expect(getAuthToken()).toBeNull();
  });

  // ============================================================================
  // Scenario 19: Role-aware controls reflect actual permissions
  // ============================================================================
  it('shows action buttons for supervisors and view-only notice for viewers on AlertsPage', async () => {
    const mockAlert = {
      id: 'alert-001',
      device_id: 'dev-001',
      device_code: 'HS-DEL-01',
      event_type: 'heat_index',
      severity: 'warning',
      status: 'triggered',
      trigger_condition: 'heat_index >= 41.0',
      trigger_value: '42.3 °C',
      rule_version: 1,
      triggered_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    };

    // Helper component injecting user role context for testing
    const AlertsWithRole: React.FC<{ role: 'viewer' | 'supervisor' }> = ({ role }) => {
      sessionStorage.setItem('heatshield_auth_token', `token-${role}`);
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/auth/me')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({
              id: '33333333-3333-3333-3333-333333333333',
              email: `${role}@heatshield.gov.in`,
              role,
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
            json: async () => ({ items: [], total: 0, page: 1, page_size: 50, pages: 1 }),
          });
        }
        return Promise.reject(new Error(`Unhandled mock ${url}`));
      });

      return (
        <AuthProvider>
          <AlertsPage />
        </AuthProvider>
      );
    };

    // 1. As Supervisor -> Acknowledge button is enabled
    const { unmount } = render(
      <MemoryRouter>
        <AlertsWithRole role="supervisor" />
      </MemoryRouter>
    );

    expect(await screen.findByRole('button', { name: /^acknowledge$/i })).toBeInTheDocument();
    unmount();

    // 2. As Viewer -> Action button is NOT rendered; Supervisor Required notice is displayed
    render(
      <MemoryRouter>
        <AlertsWithRole role="viewer" />
      </MemoryRouter>
    );

    expect(await screen.findByText(/supervisor required/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^acknowledge$/i })).not.toBeInTheDocument();
  });

  // ============================================================================
  // Scenario 20: No fake authenticated identity in production
  // ============================================================================
  it('does not fabricate any default logged-in identity when no token is present', async () => {
    // Component inspecting current auth state
    const AuthInspector: React.FC = () => {
      const { user, isAuthenticated, isLoading } = useAuth();
      if (isLoading) return <div>Checking...</div>;
      return (
        <div>
          <span data-testid="is-authenticated">{isAuthenticated ? 'yes' : 'no'}</span>
          <span data-testid="user-email">{user ? user.email : 'none'}</span>
        </div>
      );
    };

    render(
      <AuthProvider>
        <AuthInspector />
      </AuthProvider>
    );

    expect(await screen.findByTestId('is-authenticated')).toHaveTextContent('no');
    expect(screen.getByTestId('user-email')).toHaveTextContent('none');
  });
});
