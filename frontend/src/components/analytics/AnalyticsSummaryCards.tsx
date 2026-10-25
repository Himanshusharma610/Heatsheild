import React from 'react';
import type { ReadingHistorySummary } from '../../features/readings/types';

export interface AnalyticsSummaryCardsProps {
  summary: ReadingHistorySummary | null;
  isLoading: boolean;
}

export const AnalyticsSummaryCards: React.FC<AnalyticsSummaryCardsProps> = ({ summary, isLoading }) => {
  if (isLoading) {
    return (
      <div className="summary-cards-grid" aria-label="Loading analytics summaries">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card summary-card skeleton-loading">
            <div className="skeleton-title" style={{ height: 18, width: '40%', marginBottom: 12 }}></div>
            <div className="skeleton-val" style={{ height: 32, width: '60%', marginBottom: 8 }}></div>
            <div className="skeleton-sub" style={{ height: 14, width: '80%' }}></div>
          </div>
        ))}
      </div>
    );
  }

  if (!summary || summary.total_readings === 0) {
    return (
      <div className="summary-empty-banner" role="status">
        <p>No sensor readings available in the selected time range. Summary statistics are unavailable.</p>
      </div>
    );
  }

  const formatMetric = (val: number | null | undefined, unit: string) => {
    if (val === null || val === undefined) {
      return 'N/A';
    }
    return `${val.toFixed(1)} ${unit}`;
  };

  const validPct = summary.total_readings > 0
    ? ((summary.valid_readings_count / summary.total_readings) * 100).toFixed(0)
    : '0';

  return (
    <section className="analytics-summary-section" aria-label="Descriptive Statistics Summary">
      <div className="summary-cards-grid">
        {/* Temperature Summary Card */}
        <div className="card summary-card">
          <div className="summary-card-header">
            <span className="summary-card-title">Temperature</span>
            <span className="summary-card-badge temp-badge">°C</span>
          </div>
          <div className="summary-card-main">
            <span className="summary-mean-label">Mean</span>
            <span className="summary-mean-val">{formatMetric(summary.temperature_c.mean, '°C')}</span>
          </div>
          <div className="summary-card-submetrics">
            <div className="submetric">
              <span className="submetric-label">Min:</span>
              <span className="submetric-val font-mono">{formatMetric(summary.temperature_c.min, '°C')}</span>
            </div>
            <div className="submetric">
              <span className="submetric-label">Max:</span>
              <span className="submetric-val font-mono">{formatMetric(summary.temperature_c.max, '°C')}</span>
            </div>
          </div>
        </div>

        {/* Relative Humidity Summary Card */}
        <div className="card summary-card">
          <div className="summary-card-header">
            <span className="summary-card-title">Relative Humidity</span>
            <span className="summary-card-badge humidity-badge">%</span>
          </div>
          <div className="summary-card-main">
            <span className="summary-mean-label">Mean</span>
            <span className="summary-mean-val">{formatMetric(summary.relative_humidity_pct.mean, '%')}</span>
          </div>
          <div className="summary-card-submetrics">
            <div className="submetric">
              <span className="submetric-label">Min:</span>
              <span className="submetric-val font-mono">{formatMetric(summary.relative_humidity_pct.min, '%')}</span>
            </div>
            <div className="submetric">
              <span className="submetric-label">Max:</span>
              <span className="submetric-val font-mono">{formatMetric(summary.relative_humidity_pct.max, '%')}</span>
            </div>
          </div>
        </div>

        {/* Heat Index Summary Card */}
        <div className="card summary-card">
          <div className="summary-card-header">
            <span className="summary-card-title">Heat Index (NOAA)</span>
            <span className="summary-card-badge heat-badge">°C</span>
          </div>
          <div className="summary-card-main">
            <span className="summary-mean-label">Mean</span>
            <span className="summary-mean-val">{formatMetric(summary.heat_index_c.mean, '°C')}</span>
          </div>
          <div className="summary-card-submetrics">
            <div className="submetric">
              <span className="submetric-label">Min:</span>
              <span className="submetric-val font-mono">{formatMetric(summary.heat_index_c.min, '°C')}</span>
            </div>
            <div className="submetric">
              <span className="submetric-label">Max:</span>
              <span className="submetric-val font-mono">{formatMetric(summary.heat_index_c.max, '°C')}</span>
            </div>
          </div>
        </div>

        {/* Data Quality & Coverage Card */}
        <div className="card summary-card">
          <div className="summary-card-header">
            <span className="summary-card-title">Data Quality & Coverage</span>
            <span className="summary-card-badge quality-badge">{validPct}% Valid</span>
          </div>
          <div className="summary-card-main">
            <span className="summary-mean-label">Total Readings</span>
            <span className="summary-mean-val font-mono">{summary.total_readings}</span>
          </div>
          <div className="summary-card-submetrics">
            <div className="submetric">
              <span className="submetric-label text-success">Valid:</span>
              <span className="submetric-val font-mono">{summary.valid_readings_count}</span>
            </div>
            <div className="submetric">
              <span className="submetric-label text-warning">Suspect:</span>
              <span className="submetric-val font-mono">{summary.suspect_readings_count}</span>
            </div>
            <div className="submetric">
              <span className="submetric-label text-danger">Invalid/Miss:</span>
              <span className="submetric-val font-mono">{summary.invalid_readings_count + summary.missing_readings_count}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="summary-transparency-note" role="note">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          <strong>Data Integrity Note:</strong> {summary.notes} Descriptive statistics are for environmental screening and decision support only. They do not certify safe worksite conditions or diagnose medical risk.
        </span>
      </div>
    </section>
  );
};
