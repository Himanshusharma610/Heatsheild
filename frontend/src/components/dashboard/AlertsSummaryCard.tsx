import React from 'react';
import { Link } from 'react-router-dom';
import type { AlertData } from '../../features/alerts/types';
import { StatusBadge } from '../feedback/StatusBadge';

export interface AlertsSummaryCardProps {
  alerts: AlertData[];
}

export const AlertsSummaryCard: React.FC<AlertsSummaryCardProps> = ({ alerts }) => {
  const activeAlerts = alerts.filter(
    (a) => a.status === 'triggered' || a.status === 'acknowledged'
  );

  const criticalCount = activeAlerts.filter((a) => a.severity === 'critical').length;
  const warningCount = activeAlerts.filter((a) => a.severity === 'warning').length;

  return (
    <div className="card" style={{ height: '100%' }}>
      <div className="card-header">
        <div>
          <h3>Active Alert Incidents</h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Module 8 Deduplicated Episodes
          </span>
        </div>
        <Link to="/alerts" className="btn btn-secondary" style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}>
          View All Alerts
        </Link>
      </div>

      <div className="grid-3" style={{ marginBottom: 'var(--space-md)' }}>
        <div style={{ padding: 'var(--space-sm) var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Active</span>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: activeAlerts.length > 0 ? 'var(--accent-amber)' : 'var(--text-muted)' }}>
            {activeAlerts.length}
          </div>
        </div>

        <div style={{ padding: 'var(--space-sm) var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Critical</span>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: criticalCount > 0 ? 'var(--accent-rose)' : 'var(--text-muted)' }}>
            {criticalCount}
          </div>
        </div>

        <div style={{ padding: 'var(--space-sm) var(--space-md)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Warning</span>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: warningCount > 0 ? 'var(--accent-amber)' : 'var(--text-muted)' }}>
            {warningCount}
          </div>
        </div>
      </div>

      {activeAlerts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-md) 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          <span style={{ fontSize: '1.5rem', display: 'block', marginBottom: '0.25rem' }} aria-hidden="true">🛡️</span>
          No active or unacknowledged alert episodes recorded.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {activeAlerts.slice(0, 3).map((alert) => (
            <div
              key={alert.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.5rem 0.75rem',
                background: 'rgba(15, 23, 42, 0.5)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <StatusBadge status={alert.severity} />
                <code>{alert.trigger_condition}</code>
              </div>
              <span style={{ color: 'var(--text-muted)' }}>
                {new Date(alert.triggered_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
