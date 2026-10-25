import React from 'react';
import type { HeatIndexResult } from '../../features/readings/types';
import { StatusBadge } from '../feedback/StatusBadge';

export interface HeatIndexCardProps {
  heatIndex: HeatIndexResult | null;
}

export const HeatIndexCard: React.FC<HeatIndexCardProps> = ({ heatIndex }) => {
  if (!heatIndex || heatIndex.value_c === null) {
    return (
      <div className="card" style={{ height: '100%' }}>
        <div className="card-header">
          <h3>Calculated Heat-Risk Indicator</h3>
          <StatusBadge status="unavailable" label="Indicator Unavailable" />
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          {heatIndex?.notes ||
            'The apparent heat index cannot be calculated until valid dry-bulb temperature and relative humidity telemetry is received from an active sensor node.'}
        </p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
          <strong>Safety Note:</strong> An unavailable indicator does not mean conditions are safe.
        </p>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: '100%' }}>
      <div className="card-header">
        <div>
          <h3>Calculated Heat-Risk Indicator</h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Method: <code>{heatIndex.method}</code> (v{heatIndex.method_version})
          </span>
        </div>
        <StatusBadge status={heatIndex.informational_screening_level} />
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: 'var(--space-md)' }}>
        <span style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent-amber)' }}>
          {heatIndex.value_c} <span style={{ fontSize: '1.25rem', fontWeight: 600 }}>°C</span>
        </span>
        {heatIndex.value_f !== null && (
          <span style={{ fontSize: '1.1rem', color: 'var(--text-muted)', fontWeight: 500 }}>
            ({heatIndex.value_f} °F)
          </span>
        )}
      </div>

      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: 'var(--space-md)' }}>
        <div><strong>Status:</strong> <StatusBadge status={heatIndex.status} /></div>
        <div><strong>Equation:</strong> <code>{heatIndex.equation_applied}</code></div>
        <div><strong>Evaluated At:</strong> {new Date(heatIndex.calculated_at).toISOString()}</div>
      </div>

      <div style={{ padding: 'var(--space-sm) var(--space-md)', background: 'rgba(15, 23, 42, 0.6)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--accent-cyan)' }}>
        <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>
          Scientific Limitations
        </span>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
          Environmental screening indicator only. NOT Wet Bulb Globe Temperature (WBGT). Does not diagnose clinical heatstroke or predict individual physiological strain.
        </p>
      </div>
    </div>
  );
};
