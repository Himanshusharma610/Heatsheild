import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ApiClientError } from '../services/api';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email: cleanEmail, password });
      navigate(from, { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.message || 'Authentication failed. Please verify your credentials.');
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred during login. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: 'calc(100vh - 180px)',
        padding: '2rem 1rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '12px',
          padding: '2.5rem 2rem',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              borderRadius: '10px',
              backgroundColor: '#f97316',
              color: '#ffffff',
              fontSize: '1.5rem',
              fontWeight: 700,
              marginBottom: '1rem',
            }}
          >
            HS
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', margin: '0 0 0.5rem 0' }}>
            Sign In to HeatShield
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', margin: 0 }}>
            Environmental heat surveillance & occupational safety monitoring
          </p>
        </div>

        {errorMessage && (
          <div
            role="alert"
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              color: '#fca5a5',
              fontSize: '0.875rem',
              marginBottom: '1.5rem',
            }}
          >
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div style={{ marginBottom: '1.25rem' }}>
            <label
              htmlFor="email-input"
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: '#cbd5e1',
                marginBottom: '0.5rem',
              }}
            >
              Email Address
            </label>
            <input
              id="email-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="supervisor@heatshield.gov.in"
              autoComplete="email"
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '0.625rem 0.875rem',
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '6px',
                color: '#f8fafc',
                fontSize: '0.95rem',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: '1.75rem' }}>
            <label
              htmlFor="password-input"
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                color: '#cbd5e1',
                marginBottom: '0.5rem',
              }}
            >
              Password
            </label>
            <input
              id="password-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              autoComplete="current-password"
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '0.625rem 0.875rem',
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '6px',
                color: '#f8fafc',
                fontSize: '0.95rem',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              backgroundColor: isSubmitting ? '#9a3412' : '#f97316',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.95rem',
              fontWeight: 600,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.15s ease',
            }}
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div
          style={{
            marginTop: '2rem',
            paddingTop: '1.5rem',
            borderTop: '1px solid #334155',
            textAlign: 'center',
            fontSize: '0.75rem',
            color: '#64748b',
          }}
        >
          Access is restricted to authorized safety personnel. In accordance with National Heat Action Plan protocols,
          credentials are provisioned by system administrators.
        </div>
      </div>
    </div>
  );
};
