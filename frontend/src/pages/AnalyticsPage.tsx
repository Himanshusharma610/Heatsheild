import React, { useState } from 'react';
import { useHistoricalData } from '../hooks/useHistoricalData';
import { TimeSeriesChart } from '../components/analytics/TimeSeriesChart';
import { AnalyticsSummaryCards } from '../components/analytics/AnalyticsSummaryCards';
import { HistoricalReadingsTable } from '../components/analytics/HistoricalReadingsTable';
import { HistoricalAlertsView } from '../components/analytics/HistoricalAlertsView';
import { StatusBadge } from '../components/feedback/StatusBadge';

export const AnalyticsPage: React.FC = () => {
  const {
    devices,
    selectedDeviceId,
    setSelectedDeviceId,
    timePreset,
    setTimePreset,
    customStartDate,
    setCustomStartDate,
    customEndDate,
    setCustomEndDate,
    readings,
    summary,
    pagination,
    page,
    setPage,
    pageSize,
    isLoading,
    error,
    validationError,
    alertHistory,
    isLoadingAlerts,
    refetch,
  } = useHistoricalData();

  const [activeTab, setActiveTab] = useState<'charts' | 'table' | 'alerts'>('charts');

  return (
    <div className="analytics-page" role="main">
      <section style={{ marginBottom: 'var(--space-xl)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: 'var(--space-xs)' }}>
          <StatusBadge status="ready" label="Module 11: Historical Telemetry & Analytics" />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Time-Series Trends & Descriptive Screening</span>
        </div>
        <h1>Historical Data, Charts & Analytics</h1>
        <p style={{ fontSize: '1.05rem', maxWidth: '850px', marginBottom: 0 }}>
          Chronological environmental sensor telemetry, descriptive summaries, and historical alert occurrences using persisted backend readings.
        </p>
      </section>


      {/* Control Bar: Device Filter & Time-Range Selector */}
      <section className="card analytics-controls-card" aria-label="Historical Query Controls">
        <div className="controls-row">
          {/* Device Selector */}
          <div className="control-group">
            <label htmlFor="device-select" className="control-label">
              Device Filter:
            </label>
            <select
              id="device-select"
              className="control-select"
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              aria-label="Filter by sensor device"
            >
              <option value="">All Registered Devices</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.device_code} ({d.display_name})
                </option>
              ))}
            </select>
          </div>

          {/* Time Preset Buttons */}
          <div className="control-group">
            <span className="control-label">Time Window:</span>
            <div className="preset-button-group" role="group" aria-label="Historical Time Window Presets">
              <button
                type="button"
                className={`preset-btn ${timePreset === '24h' ? 'active' : ''}`}
                onClick={() => setTimePreset('24h')}
                aria-pressed={timePreset === '24h'}
              >
                24 Hours
              </button>
              <button
                type="button"
                className={`preset-btn ${timePreset === '7d' ? 'active' : ''}`}
                onClick={() => setTimePreset('7d')}
                aria-pressed={timePreset === '7d'}
              >
                7 Days
              </button>
              <button
                type="button"
                className={`preset-btn ${timePreset === '30d' ? 'active' : ''}`}
                onClick={() => setTimePreset('30d')}
                aria-pressed={timePreset === '30d'}
              >
                30 Days (Max)
              </button>
              <button
                type="button"
                className={`preset-btn ${timePreset === 'custom' ? 'active' : ''}`}
                onClick={() => setTimePreset('custom')}
                aria-pressed={timePreset === 'custom'}
              >
                Custom Range
              </button>
            </div>
          </div>

          {/* Refresh Action */}
          <div className="control-group control-group-action">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => refetch()}
              disabled={isLoading}
              aria-label="Refresh historical data"
            >
              {isLoading ? 'Querying...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Custom Date Range Picker */}
        {timePreset === 'custom' && (
          <div className="custom-range-row" aria-label="Custom Date Range Inputs">
            <div className="control-group">
              <label htmlFor="custom-start" className="control-label">
                Start Date/Time:
              </label>
              <input
                id="custom-start"
                type="datetime-local"
                className="control-input"
                value={customStartDate}
                onChange={(e) => setCustomStartDate(e.target.value)}
              />
            </div>
            <div className="control-group">
              <label htmlFor="custom-end" className="control-label">
                End Date/Time:
              </label>
              <input
                id="custom-end"
                type="datetime-local"
                className="control-input"
                value={customEndDate}
                onChange={(e) => setCustomEndDate(e.target.value)}
              />
            </div>
            <span className="control-hint">Maximum query window: 30 days.</span>
          </div>
        )}

        {/* Validation Error Message */}
        {validationError && (
          <div className="validation-error-banner" role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{validationError}</span>
          </div>
        )}

        {/* API Error Message */}
        {error && (
          <div className="error-banner" role="alert">
            <p><strong>Query Failed:</strong> {error}</p>
          </div>
        )}
      </section>

      {/* Basic Descriptive Summaries */}
      <AnalyticsSummaryCards summary={summary} isLoading={isLoading} />

      {/* Navigation View Tabs */}
      <div className="analytics-tabs-bar" role="tablist" aria-label="Analytics Views">
        <button
          type="button"
          role="tab"
          id="tab-charts"
          aria-selected={activeTab === 'charts'}
          aria-controls="panel-charts"
          className={`tab-btn ${activeTab === 'charts' ? 'active' : ''}`}
          onClick={() => setActiveTab('charts')}
        >
          Environmental Trend Charts
        </button>
        <button
          type="button"
          role="tab"
          id="tab-table"
          aria-selected={activeTab === 'table'}
          aria-controls="panel-table"
          className={`tab-btn ${activeTab === 'table' ? 'active' : ''}`}
          onClick={() => setActiveTab('table')}
        >
          Historical Telemetry Log ({pagination?.total || 0})
        </button>
        <button
          type="button"
          role="tab"
          id="tab-alerts"
          aria-selected={activeTab === 'alerts'}
          aria-controls="panel-alerts"
          className={`tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          Alert History ({alertHistory.length})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'charts' && (
        <div id="panel-charts" role="tabpanel" aria-labelledby="tab-charts" className="charts-grid">
          {/* Temperature Trend Chart */}
          <TimeSeriesChart
            data={readings}
            metric="temperature"
            title="Ambient Temperature Trend"
            unit="°C"
            colorHex="#f59e0b"
            badgeLabel="Sensor Ambient"
          />

          {/* Relative Humidity Trend Chart */}
          <TimeSeriesChart
            data={readings}
            metric="humidity"
            title="Relative Humidity Trend"
            unit="%"
            colorHex="#10b981"
            badgeLabel="Hygrometer"
          />

          {/* Heat Index Trend Chart */}
          <TimeSeriesChart
            data={readings}
            metric="heat_index"
            title="Calculated Heat Index Trend"
            unit="°C"
            colorHex="#f43f5e"
            badgeLabel="NOAA Rothfusz (Not WBGT)"
          />
        </div>
      )}

      {activeTab === 'table' && (
        <div id="panel-table" role="tabpanel" aria-labelledby="tab-table">
          <HistoricalReadingsTable
            readings={readings}
            pagination={pagination}
            page={page}
            onPageChange={setPage}
            pageSize={pageSize}
            isLoading={isLoading}
          />
        </div>
      )}

      {activeTab === 'alerts' && (
        <div id="panel-alerts" role="tabpanel" aria-labelledby="tab-alerts">
          <HistoricalAlertsView alerts={alertHistory} isLoading={isLoadingAlerts} />
        </div>
      )}
    </div>
  );
};
export default AnalyticsPage;
