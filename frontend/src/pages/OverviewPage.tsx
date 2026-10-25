import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { healthService, type ReadyResponse, type HealthResponse } from '../services/healthService';
import { getApiBaseUrl } from '../services/api';
import { StatusBadge } from '../components/feedback/StatusBadge';
import { LoadingState } from '../components/feedback/LoadingState';
import { ErrorState } from '../components/feedback/ErrorState';

export const OverviewPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, readyRes] = await Promise.all([
        healthService.checkHealth().catch(() => null),
        healthService.checkReadiness().catch((err: Error) => {
          throw err;
        }),
      ]);
      setHealth(healthRes);
      setReadiness(readyRes);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Backend connection unavailable';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    Promise.all([
      healthService.checkHealth().catch(() => null),
      healthService.checkReadiness().catch((err: Error) => {
        throw err;
      }),
    ])
      .then(([healthRes, readyRes]) => {
        if (isMounted) {
          setHealth(healthRes);
          setReadiness(readyRes);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Backend connection unavailable');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div>
      <section style={{ marginBottom: 'var(--space-2xl)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: 'var(--space-xs)' }}>
          <StatusBadge status="ready" label="Module 9: Frontend Foundation" />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>React 19 + TypeScript + Vite</span>
        </div>
        <h1>System Overview & Architecture Status</h1>
        <p style={{ fontSize: '1.1rem', maxWidth: '800px' }}>
          HeatShield Bharat is an IoT-based environmental heat monitoring and early-warning decision support system designed to screen for dangerous thermal conditions in outdoor and industrial workplaces across India.
        </p>
      </section>

      {/* Backend Live Status Section */}
      <section className="card" style={{ marginBottom: 'var(--space-xl)' }}>
        <div className="card-header">
          <div>
            <h3>Backend Connectivity & Readiness Probe</h3>
            <p style={{ margin: 0, fontSize: '0.85rem' }}>
              Target API base URL: <code style={{ color: 'var(--accent-cyan)' }}>{getApiBaseUrl()}</code>
            </p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => { setLoading(true); fetchStatus(); }} disabled={loading} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
            {loading ? 'Probing...' : 'Refresh Status'}
          </button>
        </div>

        {loading ? (
          <LoadingState message="Connecting to HeatShield backend API..." />
        ) : error ? (
          <ErrorState
            title="Backend Service Unavailable"
            message={`Unable to connect to the FastAPI backend. ${error}. Please verify that the backend server is running.`}
            onRetry={fetchStatus}
          />
        ) : readiness ? (
          <div className="grid-3">
            <div style={{ padding: 'var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>API Service Liveness</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                <StatusBadge status={health?.status === 'healthy' ? 'healthy' : 'warning'} label={health?.status || 'Active'} />
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>v{health?.version || '0.1.0'}</span>
              </div>
            </div>

            <div style={{ padding: 'var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Database Connection</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                <StatusBadge status={readiness.services.database} />
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>PostgreSQL 15</span>
              </div>
            </div>

            <div style={{ padding: 'var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>System Overall State</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                <StatusBadge status={readiness.status} label={readiness.status === 'ready' ? 'Ready for Operation' : 'Initialization Pending'} />
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {/* Quick Navigation Cards */}
      <section style={{ marginBottom: 'var(--space-2xl)' }}>
        <h2 style={{ marginBottom: 'var(--space-md)' }}>Platform Modules & Capabilities</h2>
        <div className="grid-3">
          <Link to="/devices" className="card card-interactive" style={{ textDecoration: 'none' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-sm)' }}>
              <span style={{ fontSize: '1.5rem' }} aria-hidden="true">📡</span>
              <StatusBadge status="unconfirmed" label="Hardware Pending" />
            </div>
            <h3>Hardware Nodes</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: 0 }}>
              Inspect ESP32 microcontroller architecture, Hardware Abstraction Layer, and sensor contracts.
            </p>
          </Link>

          <Link to="/alerts" className="card card-interactive" style={{ textDecoration: 'none' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-sm)' }}>
              <span style={{ fontSize: '1.5rem' }} aria-hidden="true">🚨</span>
              <StatusBadge status="valid" label="Module 8 Active" />
            </div>
            <h3>Alert Engine</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: 0 }}>
              Review configured threshold rules, episode deduplication policy, and supervisor lifecycle events.
            </p>
          </Link>

          <Link to="/calculator" className="card card-interactive" style={{ textDecoration: 'none' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-sm)' }}>
              <span style={{ fontSize: '1.5rem' }} aria-hidden="true">🌡️</span>
              <StatusBadge status="valid" label="Module 7 Active" />
            </div>
            <h3>Heat-Risk Engine</h3>
            <p style={{ fontSize: '0.9rem', marginBottom: 0 }}>
              Test the authoritative NWS Rothfusz / Steadman calculation engine with full scientific explainability.
            </p>
          </Link>
        </div>
      </section>

      {/* Safety & System Invariants */}
      <section className="card">
        <h3 style={{ marginBottom: 'var(--space-sm)' }}>Operational Safety Invariants</h3>
        <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <li>
            <strong>Environmental Screening Only:</strong> The system produces operational screening metrics and decision-support alerts. It does not provide medical diagnoses or predict heatstroke.
          </li>
          <li>
            <strong>Transparent & Honest Telemetry:</strong> Unconnected hardware, missing data, or backend errors are never disguised as green "safe" or "zero risk" states.
          </li>
          <li>
            <strong>Provisional Development Rules:</strong> Current threshold rules are provisional testing parameters. Production safety policies require qualified institutional calibration.
          </li>
        </ul>
      </section>
    </div>
  );
};
