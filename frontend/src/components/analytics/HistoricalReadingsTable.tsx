import React from 'react';
import type { ReadingHistoryItem, ReadingHistoryPagination } from '../../features/readings/types';

export interface HistoricalReadingsTableProps {
  readings: ReadingHistoryItem[];
  pagination: ReadingHistoryPagination | null;
  page: number;
  onPageChange: (newPage: number) => void;
  pageSize: number;
  isLoading: boolean;
}

export const HistoricalReadingsTable: React.FC<HistoricalReadingsTableProps> = ({
  readings,
  pagination,
  page,
  onPageChange,
  pageSize,
  isLoading,
}) => {
  const totalPages = pagination ? Math.ceil(pagination.total / pageSize) : 1;

  const formatTimestamp = (iso: string | null) => {
    if (!iso) return <span className="text-muted">Absent (Fallback to Received)</span>;
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
  };

  const getHeatIndexBadgeClass = (level: string | null) => {
    switch (level) {
      case 'danger':
      case 'extreme_danger':
        return 'badge-danger';
      case 'extreme_caution':
      case 'caution':
        return 'badge-warning';
      case 'normal':
        return 'badge-success';
      default:
        return 'badge-muted';
    }
  };

  return (
    <div className="card table-card" role="region" aria-label="Historical Sensor Readings">
      <div className="table-header">
        <h3 className="table-title">Historical Sensor Telemetry Log</h3>
        {pagination && (
          <span className="table-counter">
            Showing {readings.length} of {pagination.total} records
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="table-loading-container" role="status">
          <div className="loading-spinner" aria-hidden="true" />
          <p>Querying persisted historical readings...</p>
        </div>
      ) : readings.length === 0 ? (
        <div className="table-empty-state" role="status">
          <p className="empty-title">No Historical Readings Found</p>
          <p className="empty-desc">
            No real sensor readings match the selected time range and device criteria.
          </p>
        </div>
      ) : (
        <>
          <div className="table-responsive-wrapper">
            <table className="data-table" aria-label="Historical Telemetry Readings Log">
              <thead>
                <tr>
                  <th scope="col">Device Code</th>
                  <th scope="col">Measurement Time (RTC)</th>
                  <th scope="col">Server Received (UTC)</th>
                  <th scope="col">Temperature</th>
                  <th scope="col">Humidity</th>
                  <th scope="col">Heat Index (NOAA)</th>
                  <th scope="col">Quality</th>
                </tr>
              </thead>
              <tbody>
                {readings.map((r) => (
                  <tr key={r.id}>
                    <td className="font-mono font-bold">{r.device_code}</td>
                    <td>{formatTimestamp(r.measured_at)}</td>
                    <td>{formatTimestamp(r.received_at)}</td>
                    <td className="font-mono">
                      {r.temperature_c !== null ? `${Number(r.temperature_c).toFixed(1)} °C` : <span className="text-muted">None</span>}
                    </td>
                    <td className="font-mono">
                      {r.relative_humidity_pct !== null ? `${Number(r.relative_humidity_pct).toFixed(1)} %` : <span className="text-muted">None</span>}
                    </td>
                    <td>
                      {r.heat_index_c !== null ? (
                        <div className="heat-cell">
                          <span className="font-mono font-bold">{Number(r.heat_index_c).toFixed(1)} °C</span>
                          {r.heat_index_screening_level && (
                            <span className={`status-badge-inline ${getHeatIndexBadgeClass(r.heat_index_screening_level)}`}>
                              {r.heat_index_screening_level.replace('_', ' ')}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted">N/A</span>
                      )}
                    </td>
                    <td>
                      <span className={`status-pill pill-${r.quality_status}`}>
                        {r.quality_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="table-pagination-bar" role="navigation" aria-label="Pagination">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onPageChange(page - 1)}
                disabled={page <= 1 || isLoading}
                aria-label="Previous page"
              >
                &larr; Previous
              </button>
              <span className="page-indicator">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onPageChange(page + 1)}
                disabled={page >= totalPages || isLoading}
                aria-label="Next page"
              >
                Next &rarr;
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
