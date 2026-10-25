import React from 'react';
import type { LatestReadingItem } from '../../features/readings/types';
import { StatusBadge } from '../feedback/StatusBadge';

export interface EnvironmentalMetricCardProps {
  reading: LatestReadingItem | null;
  staleThresholdMinutes?: number;
}

export const EnvironmentalMetricCard: React.FC<EnvironmentalMetricCardProps> = ({
  reading,
  staleThresholdMinutes = 15,
}) => {
  const [currentTime] = React.useState<number>(() => Date.now());

  if (!reading) {
    return (
      <div className="card" style={{ height: '100%' }}>
        <div className="card-header">
          <h3>Latest Environmental Telemetry</h3>
          <StatusBadge status="missing" label="No Telemetry Received" />
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          No sensor readings are currently recorded in the backend database. Connect an authenticated sensor node to begin streaming telemetry.
        </p>
      </div>
    );
  }

  // Calculate reading age in minutes based on received_at or measured_at
  const timestampToEvaluate = reading.measured_at || reading.received_at;
  const readingTime = new Date(timestampToEvaluate).getTime();
  const ageMinutes = Math.floor((currentTime - readingTime) / (60 * 1000));
  const isStale = ageMinutes >= staleThresholdMinutes;

  return (
    <div className="card" style={{ height: '100%', borderColor: isStale ? 'rgba(245, 158, 11, 0.4)' : undefined }}>
      <div className="card-header">
        <div>
          <h3>Latest Environmental Telemetry</h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Node: <code>{reading.device_code}</code> (Event: <code>{reading.event_id}</code>)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          <StatusBadge status={reading.quality_status} label={`Quality: ${reading.quality_status}`} />
          {isStale && (
            <StatusBadge status="warning" label={`Stale Data (${ageMinutes}m old)`} />
          )}
          <StatusBadge status={reading.source_mode === 'hardware' ? 'valid' : 'info'} label={reading.source_mode} />
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 'var(--space-md)' }}>
        {/* Temperature Block */}
        <div style={{ padding: 'var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Ambient Temperature
          </span>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
            {reading.temperature_c !== null ? (
              <>
                {reading.temperature_c} <span style={{ fontSize: '1.1rem', fontWeight: 500, color: 'var(--text-muted)' }}>°C</span>
              </>
            ) : (
              <span style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Unavailable</span>
            )}
          </div>
        </div>

        {/* Humidity Block */}
        <div style={{ padding: 'var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Relative Humidity
          </span>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
            {reading.relative_humidity_pct !== null ? (
              <>
                {reading.relative_humidity_pct} <span style={{ fontSize: '1.1rem', fontWeight: 500, color: 'var(--text-muted)' }}>%</span>
              </>
            ) : (
              <span style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Unavailable</span>
            )}
          </div>
        </div>
      </div>

      {/* Timestamps & Quality Details */}
      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <div>
          <strong>Device Measured At:</strong>{' '}
          {reading.measured_at ? (
            <span>{new Date(reading.measured_at).toISOString()} (Device RTC)</span>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>Uncalibrated / Absent</span>
          )}
        </div>
        <div>
          <strong>Server Received At:</strong>{' '}
          <span>{new Date(reading.received_at).toISOString()} (UTC)</span>
        </div>
        {reading.firmware_version && (
          <div>
            <strong>Firmware:</strong> <code>v{reading.firmware_version}</code>
          </div>
        )}
      </div>
    </div>
  );
};
