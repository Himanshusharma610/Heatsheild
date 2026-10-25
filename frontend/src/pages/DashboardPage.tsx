import React from 'react';
import { useDashboardData } from '../hooks/useDashboardData';
import { EnvironmentalMetricCard } from '../components/dashboard/EnvironmentalMetricCard';
import { HeatIndexCard } from '../components/dashboard/HeatIndexCard';
import { AlertsSummaryCard } from '../components/dashboard/AlertsSummaryCard';
import { DeviceStatusCard } from '../components/dashboard/DeviceStatusCard';
import { LoadingState } from '../components/feedback/LoadingState';
import { ErrorState } from '../components/feedback/ErrorState';
import { StatusBadge } from '../components/feedback/StatusBadge';

export const DashboardPage: React.FC = () => {
  const {
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
  } = useDashboardData(15, 15);

  const primaryReading = latestReadings[0] || null;

  return (
    <div>
      {/* Page Title & Mission Header */}
      <section style={{ marginBottom: 'var(--space-xl)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: 'var(--space-xs)' }}>
          <StatusBadge status="ready" label="Module 10: Live Monitoring Active" />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>React 19 + TypeScript + FastAPI</span>
        </div>
        <h1>System Overview & Architecture Status — Live Monitoring Dashboard</h1>
        <p style={{ fontSize: '1.05rem', maxWidth: '850px', marginBottom: 0 }}>
          Real-time environmental screening telemetry, NWS Rothfusz / Steadman heat-risk evaluation, active alert incident episodes, and registered IoT sensor node inventory.
        </p>
      </section>

      {/* Live Polling & Controls Toolbar */}
      <div className="dashboard-toolbar" aria-label="Dashboard Refresh Controls">
        <div className="dashboard-toolbar-left">
          <div className={`refresh-indicator ${isRefreshing ? 'refreshing' : ''}`}>
            <div className={`pulse-dot ${isRefreshing ? 'pulse' : ''}`} aria-hidden="true" />
            <span>
              {isRefreshing
                ? 'Refreshing telemetry from backend...'
                : 'Live Monitoring Connected'}
            </span>
          </div>

          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Last updated:{' '}
            <strong>
              {lastRefreshedAt ? lastRefreshedAt.toLocaleTimeString() : 'Pending'}
            </strong>
          </div>

          <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            (Stale threshold: &gt;{staleThresholdMinutes}m)
          </span>
        </div>

        <div className="dashboard-toolbar-right">
          <label
            htmlFor="polling-interval-select"
            style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 500 }}
          >
            Auto-Refresh:
          </label>
          <select
            id="polling-interval-select"
            className="form-select"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.82rem' }}
            value={pollingIntervalSeconds}
            onChange={(e) => setPollingIntervalSeconds(Number(e.target.value))}
            aria-label="Select automatic refresh interval"
          >
            <option value={10}>10s</option>
            <option value={15}>15s (Default)</option>
            <option value={30}>30s</option>
            <option value={60}>60s</option>
            <option value={0}>Paused (Manual)</option>
          </select>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => refreshNow()}
            disabled={isRefreshing || isLoading}
            aria-label="Refresh dashboard data now"
            style={{
              padding: '0.35rem 0.75rem',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <span aria-hidden="true">↻</span>
            {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {/* Cached-Stale Warning Banner */}
      {isCachedStale && (
        <div className="stale-cached-banner" role="alert">
          <div className="stale-cached-banner-content">
            <span style={{ fontSize: '1.25rem' }} aria-hidden="true">⚠️</span>
            <div>
              <strong>Background Refresh Failed:</strong> {error || 'Backend communication dropped'}. Displaying previously fetched telemetry from{' '}
              {lastRefreshedAt ? lastRefreshedAt.toLocaleTimeString() : 'earlier'}. Data may be stale.
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => refreshNow()}
            style={{ padding: '0.3rem 0.65rem', fontSize: '0.8rem' }}
          >
            Retry Now
          </button>
        </div>
      )}

      {/* Initial Loading & Error States */}
      {isLoading && !lastRefreshedAt ? (
        <LoadingState message="Connecting to HeatShield backend and fetching live telemetry..." />
      ) : error && !lastRefreshedAt ? (
        <ErrorState
          title="Backend Connection Failed"
          message={`Unable to connect to the HeatShield FastAPI backend: ${error}. Please ensure the backend server is running.`}
          onRetry={() => refreshNow()}
        />
      ) : (
        <>
          {/* Top Telemetry & Evaluation Grid */}
          <section style={{ marginBottom: 'var(--space-xl)' }}>
            <h2 style={{ marginBottom: 'var(--space-md)' }}>Live Environmental Screening</h2>
            <div className="grid-3">
              <EnvironmentalMetricCard
                reading={primaryReading}
                staleThresholdMinutes={staleThresholdMinutes}
              />
              <HeatIndexCard heatIndex={heatIndex} />
              <AlertsSummaryCard alerts={activeAlerts} />
            </div>
          </section>

          {/* Registered Node Inventory Section */}
          <section style={{ marginBottom: 'var(--space-xl)' }}>
            <DeviceStatusCard devices={devices} />
          </section>

          {/* Operational Safety Invariants & Scientific Notes */}
          <section className="card">
            <h3 style={{ marginBottom: 'var(--space-sm)' }}>Operational Safety Invariants</h3>
            <ul
              style={{
                paddingLeft: '1.25rem',
                color: 'var(--text-secondary)',
                fontSize: '0.9rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <li>
                <strong>Screening Decision Support Only:</strong> This dashboard displays environmental screening metrics and supervisor decision-support alerts. It does not provide medical diagnoses or predict clinical heatstroke.
              </li>
              <li>
                <strong>Transparent Hardware State:</strong> Physical ESP32 microcontrollers and environmental sensors are pending procurement. Connection status reflects database registrations and heartbeat timestamps, not physical wire attachments.
              </li>
              <li>
                <strong>Honest Data Freshness:</strong> Missing or stale telemetry is never masked as safe or zero-risk. If a sensor node disconnects or data exceeds {staleThresholdMinutes} minutes, a Stale Data warning is explicitly highlighted.
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
};
