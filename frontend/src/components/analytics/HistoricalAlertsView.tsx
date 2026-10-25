import React from 'react';
import type { AlertData } from '../../features/alerts/types';

export interface HistoricalAlertsViewProps {
  alerts: AlertData[];
  isLoading: boolean;
}

export const HistoricalAlertsView: React.FC<HistoricalAlertsViewProps> = ({ alerts, isLoading }) => {
  const formatTimestamp = (iso: string | null | undefined) => {
    if (!iso) return <span className="text-muted">—</span>;
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev) {
      case 'critical':
        return 'badge-danger';
      case 'warning':
        return 'badge-warning';
      default:
        return 'badge-info';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'triggered':
        return 'pill-invalid';
      case 'acknowledged':
        return 'pill-suspect';
      case 'resolved':
        return 'pill-valid';
      default:
        return 'pill-missing';
    }
  };

  return (
    <div className="card table-card" role="region" aria-label="Historical Alert Log">
      <div className="table-header">
        <h3 className="table-title">Historical Alert Events</h3>
        <span className="table-counter">
          {alerts.length} event{alerts.length === 1 ? '' : 's'} recorded in range
        </span>
      </div>

      {isLoading ? (
        <div className="table-loading-container" role="status">
          <div className="loading-spinner" aria-hidden="true" />
          <p>Loading historical alert events...</p>
        </div>
      ) : alerts.length === 0 ? (
        <div className="table-empty-state" role="status">
          <p className="empty-title">No Alerts In Selected Range</p>
          <p className="empty-desc">
            No safety threshold breach alerts were triggered during this time window.
          </p>
        </div>
      ) : (
        <div className="table-responsive-wrapper">
          <table className="data-table" aria-label="Persisted Alert History">
            <thead>
              <tr>
                <th scope="col">Triggered At</th>
                <th scope="col">Device Code</th>
                <th scope="col">Rule Triggered</th>
                <th scope="col">Severity</th>
                <th scope="col">Status</th>
                <th scope="col">Trigger Value</th>
                <th scope="col">Acknowledged At</th>
                <th scope="col">Resolved At</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td>{formatTimestamp(a.triggered_at)}</td>
                  <td className="font-mono">{a.device_code || a.device_id.slice(0, 8)}</td>
                  <td>{a.rule_name || a.trigger_condition || 'Environmental Threshold'}</td>
                  <td>
                    <span className={`status-badge-inline ${getSeverityBadgeClass(a.severity)}`}>
                      {a.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`status-pill ${getStatusBadgeClass(a.status)}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="font-mono">
                    {a.trigger_value !== undefined ? `${Number(a.trigger_value).toFixed(1)}` : '—'}
                  </td>
                  <td>{formatTimestamp(a.acknowledged_at)}</td>
                  <td>{formatTimestamp(a.resolved_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
