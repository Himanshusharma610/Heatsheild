import React, { useEffect, useState } from 'react';
import { alertService } from '../services/alertService';
import type { AlertData, AlertRuleData } from '../features/alerts/types';
import { StatusBadge } from '../components/feedback/StatusBadge';
import { LoadingState } from '../components/feedback/LoadingState';
import { ErrorState } from '../components/feedback/ErrorState';
import { EmptyState } from '../components/feedback/EmptyState';

import { useAuth } from '../context/AuthContext';

export const AlertsPage: React.FC = () => {
  const { canManageAlerts } = useAuth();
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [rules, setRules] = useState<AlertRuleData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlertData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [alertsRes, rulesRes] = await Promise.all([
        alertService.listAlerts().catch((err: Error) => {
          throw err;
        }),
        alertService.listAlertRules().catch(() => ({ items: [], total: 0, page: 1, page_size: 50, pages: 1 })),
      ]);
      setAlerts(alertsRes.items || []);
      setRules(rulesRes.items || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to retrieve alerts from backend';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    Promise.all([
      alertService.listAlerts().catch((err: Error) => {
        throw err;
      }),
      alertService.listAlertRules().catch(() => ({ items: [], total: 0, page: 1, page_size: 50, pages: 1 })),
    ])
      .then(([alertsRes, rulesRes]) => {
        if (isMounted) {
          setAlerts(alertsRes.items || []);
          setRules(rulesRes.items || []);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to retrieve alerts from backend');
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
          <StatusBadge status="valid" label="Module 8: Alert Engine Connected" />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Deduplication & Supervisor Lifecycle</span>
        </div>
        <h1>Active Alerts & Configured Rules</h1>
        <p style={{ fontSize: '1.05rem', maxWidth: '850px' }}>
          Real-time incident management for environmental threshold breaches. Alerts represent decision-support notifications and require documented supervisor acknowledgement.
        </p>
      </section>

      {/* Alert Feed Section */}
      <section className="card" style={{ marginBottom: 'var(--space-xl)' }}>
        <div className="card-header">
          <div>
            <h3>Active Alert Incidents</h3>
            <p style={{ margin: 0, fontSize: '0.85rem' }}>
              Connected to backend endpoint: <code style={{ color: 'var(--accent-cyan)' }}>GET /api/v1/alerts</code>
            </p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => { setLoading(true); fetchAlertData(); }} disabled={loading} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
            {loading ? 'Refreshing...' : 'Refresh Alerts'}
          </button>
        </div>

        {loading ? (
          <LoadingState message="Fetching alerts from backend..." />
        ) : error ? (
          <ErrorState
            title="Backend Alert Service Unavailable"
            message={`Could not load alerts from backend. ${error}. Verify that the backend is running and alert tables are migrated.`}
            onRetry={fetchAlertData}
          />
        ) : alerts.length === 0 ? (
          <EmptyState
            title="No Active Alerts"
            description="There are currently no active or unacknowledged alert episodes recorded in the backend database. New alerts are automatically triggered when incoming telemetry breaches configured threshold rules."
          />
        ) : (
          <div className="table-container">
            <table className="data-table" aria-label="Active Alerts List">
              <thead>
                <tr>
                  <th scope="col">Severity</th>
                  <th scope="col">Status</th>
                  <th scope="col">Trigger Condition</th>
                  <th scope="col">Trigger Value</th>
                  <th scope="col">Triggered At</th>
                  <th scope="col">Rule Version</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr key={alert.id}>
                    <td>
                      <StatusBadge status={alert.severity} />
                    </td>
                    <td>
                      <StatusBadge status={alert.status} />
                    </td>
                    <td><code>{alert.trigger_condition}</code></td>
                    <td><strong>{alert.trigger_value}</strong></td>
                    <td>{new Date(alert.triggered_at).toLocaleString()}</td>
                    <td>v{alert.rule_version}</td>
                    <td>
                      {alert.status === 'triggered' ? (
                        canManageAlerts ? (
                          <button
                            type="button"
                            className="btn btn-primary"
                            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', backgroundColor: '#f97316' }}
                            onClick={async () => {
                              const action = window.prompt('Document safety action taken (required):', 'Hydration station opened; outdoor labor paused.');
                              if (action && action.trim()) {
                                try {
                                  await alertService.acknowledgeAlert(alert.id, action.trim());
                                  fetchAlertData();
                                } catch (err) {
                                  window.alert(err instanceof Error ? err.message : 'Failed to acknowledge alert');
                                }
                              }
                            }}
                          >
                            Acknowledge
                          </button>
                        ) : (
                          <span
                            style={{
                              color: 'var(--text-muted, #94a3b8)',
                              fontSize: '0.75rem',
                              fontStyle: 'italic',
                              display: 'inline-block',
                              padding: '0.2rem 0.4rem',
                              border: '1px dashed #475569',
                              borderRadius: '4px',
                            }}
                            title="Supervisor or administrator role required to acknowledge alert episodes."
                          >
                            Supervisor Required
                          </span>
                        )
                      ) : alert.status === 'acknowledged' ? (
                        canManageAlerts ? (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
                            onClick={async () => {
                              const notes = window.prompt('Enter resolution notes (optional):', 'Heat index dropped below threshold.');
                              try {
                                await alertService.resolveAlert(alert.id, notes || undefined);
                                fetchAlertData();
                              } catch (err) {
                                window.alert(err instanceof Error ? err.message : 'Failed to resolve alert');
                              }
                            }}
                          >
                            Resolve
                          </button>
                        ) : (
                          <span style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.75rem' }}>
                            Acknowledged
                          </span>
                        )
                      ) : (
                        <span style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.75rem' }}>Resolved</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Configured Rules Section */}
      <section className="card">
        <div className="card-header">
          <div>
            <h3>Configured Threshold Rules</h3>
            <p style={{ margin: 0, fontSize: '0.85rem' }}>
              Connected to backend endpoint: <code style={{ color: 'var(--accent-cyan)' }}>GET /api/v1/alert-rules</code>
            </p>
          </div>
        </div>

        {rules.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            No threshold rules configured in database. Rules can be provisioned via the Module 8 supervisor API (<code>POST /api/v1/alert-rules</code>).
          </p>
        ) : (
          <div className="table-container">
            <table className="data-table" aria-label="Configured Rules List">
              <thead>
                <tr>
                  <th scope="col">Rule Name</th>
                  <th scope="col">Metric</th>
                  <th scope="col">Operator</th>
                  <th scope="col">Threshold</th>
                  <th scope="col">Severity</th>
                  <th scope="col">Active?</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td><strong>{rule.name}</strong></td>
                    <td><code>{rule.metric}</code></td>
                    <td><code>{rule.operator}</code></td>
                    <td>{rule.threshold}</td>
                    <td><StatusBadge status={rule.severity} /></td>
                    <td>
                      <StatusBadge status={rule.is_active ? 'valid' : 'disabled'} label={rule.is_active ? 'Active' : 'Disabled'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
