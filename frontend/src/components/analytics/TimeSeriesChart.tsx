import React, { useState, useMemo } from 'react';
import type { ReadingHistoryItem } from '../../features/readings/types';

export interface TimeSeriesChartProps {
  data: ReadingHistoryItem[];
  metric: 'temperature' | 'humidity' | 'heat_index';
  title: string;
  unit: string;
  colorHex: string;
  badgeLabel?: string;
}

interface DataPoint {
  timestamp: number;
  timeLabel: string;
  measurementTime: string;
  receivedTime: string;
  value: number | null;
  quality: string;
  raw: ReadingHistoryItem;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  metric,
  title,
  unit,
  colorHex,
  badgeLabel,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<DataPoint | null>(null);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  // Parse and extract series points
  const points: DataPoint[] = useMemo(() => {
    return data.map((item) => {
      // Prioritize physical sensor measurement timestamp, fall back to server receipt
      const rawTime = item.measured_at || item.received_at;
      const d = new Date(rawTime);
      const timestamp = isNaN(d.getTime()) ? 0 : d.getTime();

      let val: number | null = null;
      if (metric === 'temperature') {
        val = item.temperature_c !== null ? Number(item.temperature_c) : null;
      } else if (metric === 'humidity') {
        val = item.relative_humidity_pct !== null ? Number(item.relative_humidity_pct) : null;
      } else if (metric === 'heat_index') {
        val = item.heat_index_c !== null ? Number(item.heat_index_c) : null;
      }

      return {
        timestamp,
        timeLabel: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
        measurementTime: item.measured_at
          ? new Date(item.measured_at).toLocaleString()
          : 'Absent (Server Received: ' + new Date(item.received_at).toLocaleString() + ')',
        receivedTime: new Date(item.received_at).toLocaleString(),
        value: val,
        quality: item.quality_status,
        raw: item,
      };
    });
  }, [data, metric]);

  // Valid points only (non-null and valid/suspect quality)
  const validPoints = useMemo(() => {
    return points.filter((p) => p.value !== null && p.quality === 'valid');
  }, [points]);

  // Chart dimensions
  const width = 760;
  const height = 240;
  const paddingLeft = 55;
  const paddingRight = 25;
  const paddingTop = 25;
  const paddingBottom = 40;
  const innerWidth = width - paddingLeft - paddingRight;
  const innerHeight = height - paddingTop - paddingBottom;

  // Extents calculation
  const { minVal, maxVal, minTime, maxTime, segments } = useMemo(() => {
    if (validPoints.length === 0) {
      return { minVal: 0, maxVal: 100, minTime: 0, maxTime: 0, segments: [] };
    }

    let minV = Infinity;
    let maxV = -Infinity;
    for (const p of validPoints) {
      if (p.value !== null) {
        if (p.value < minV) minV = p.value;
        if (p.value > maxV) maxV = p.value;
      }
    }

    if (minV === maxV) {
      minV -= 2;
      maxV += 2;
    } else {
      const margin = (maxV - minV) * 0.1;
      minV -= margin;
      maxV += margin;
    }

    const minT = points[0]?.timestamp || 0;
    const maxT = points[points.length - 1]?.timestamp || 0;

    // Detect gaps (break line if gap > 45 minutes or invalid point in between)
    const segs: { x: number; y: number; pt: DataPoint }[][] = [];
    let currentSeg: { x: number; y: number; pt: DataPoint }[] = [];

    const timeSpan = maxT - minT || 1;
    const valSpan = maxV - minV || 1;

    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      // Only connect points that are valid measurements
      if (p.value !== null && p.quality === 'valid') {
        const x = paddingLeft + ((p.timestamp - minT) / timeSpan) * innerWidth;
        const y = paddingTop + innerHeight - ((p.value - minV) / valSpan) * innerHeight;

        // Check time gap from previous point in current segment
        if (currentSeg.length > 0) {
          const prevPt = currentSeg[currentSeg.length - 1].pt;
          const diffMinutes = (p.timestamp - prevPt.timestamp) / (1000 * 60);
          if (diffMinutes > 45) {
            // Gap detected: break line, start new segment
            segs.push(currentSeg);
            currentSeg = [];
          }
        }
        currentSeg.push({ x, y, pt: p });
      } else {
        // Missing or invalid reading encountered: break line segment
        if (currentSeg.length > 0) {
          segs.push(currentSeg);
          currentSeg = [];
        }
      }
    }
    if (currentSeg.length > 0) {
      segs.push(currentSeg);
    }

    return { minVal: minV, maxVal: maxV, minTime: minT, maxTime: maxT, segments: segs };
  }, [points, validPoints, innerWidth, innerHeight, paddingLeft, paddingTop]);

  // Y-axis ticks
  const yTicks = useMemo(() => {
    if (validPoints.length === 0) return [];
    const ticks = [];
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const val = minVal + (i / steps) * (maxVal - minVal);
      const y = paddingTop + innerHeight - (i / steps) * innerHeight;
      ticks.push({ val: val.toFixed(1), y });
    }
    return ticks;
  }, [minVal, maxVal, innerHeight, paddingTop, validPoints.length]);

  // X-axis ticks
  const xTicks = useMemo(() => {
    if (points.length === 0 || minTime === maxTime) return [];
    const ticks = [];
    const steps = Math.min(5, points.length);
    for (let i = 0; i < steps; i++) {
      const idx = Math.floor((i / (steps - 1 || 1)) * (points.length - 1));
      const pt = points[idx];
      const x = paddingLeft + ((pt.timestamp - minTime) / (maxTime - minTime || 1)) * innerWidth;
      ticks.push({ label: pt.timeLabel, x });
    }
    return ticks;
  }, [points, minTime, maxTime, innerWidth, paddingLeft]);

  return (
    <div className="card time-series-card" role="region" aria-label={`${title} Time Series Chart`}>
      <div className="chart-header">
        <div className="chart-title-area">
          <h3 className="chart-title">{title}</h3>
          <span className="chart-unit-badge" style={{ borderColor: colorHex, color: colorHex }}>
            {unit}
          </span>
          {badgeLabel && <span className="chart-sub-badge">{badgeLabel}</span>}
        </div>
        <div className="chart-actions">
          <div className="chart-view-toggle" role="group" aria-label="Display View">
            <button
              type="button"
              className={`view-toggle-btn ${viewMode === 'chart' ? 'active' : ''}`}
              onClick={() => setViewMode('chart')}
              aria-pressed={viewMode === 'chart'}
            >
              Chart
            </button>
            <button
              type="button"
              className={`view-toggle-btn ${viewMode === 'table' ? 'active' : ''}`}
              onClick={() => setViewMode('table')}
              aria-pressed={viewMode === 'table'}
            >
              Table View
            </button>
          </div>
        </div>
      </div>

      {points.length === 0 ? (
        <div className="chart-empty-state" role="status">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3 3v18h18" />
            <path d="M19 9l-5 5-4-4-3 3" />
          </svg>
          <p className="empty-title">No Historical Readings Recorded</p>
          <p className="empty-desc">
            No real sensor telemetry matches the selected filter criteria. Connect a sensor node or broaden the date range.
          </p>
        </div>
      ) : validPoints.length < 2 ? (
        <div className="chart-insufficient-state" role="status">
          <p className="insufficient-title">Insufficient Valid Readings for Trend</p>
          <p className="insufficient-desc">
            Found {validPoints.length} valid measurement. At least 2 valid points are required to plot a continuous trend without misleading extrapolation.
          </p>
        </div>
      ) : viewMode === 'table' ? (
        <div className="chart-accessible-table-wrapper">
          <table className="data-table" aria-label={`${title} Data Points`}>
            <thead>
              <tr>
                <th scope="col">Measurement Time</th>
                <th scope="col">Server Received</th>
                <th scope="col">Value ({unit})</th>
                <th scope="col">Quality Status</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, idx) => (
                <tr key={`${p.raw.id || idx}`}>
                  <td>{p.measurementTime}</td>
                  <td>{p.receivedTime}</td>
                  <td className="font-mono">
                    {p.value !== null ? `${p.value.toFixed(1)} ${unit}` : <span className="text-muted">Missing / None</span>}
                  </td>
                  <td>
                    <span className={`status-pill pill-${p.quality}`}>
                      {p.quality}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="svg-chart-container" style={{ position: 'relative' }}>
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="time-series-svg"
            role="img"
            aria-label={`${title} line graph`}
          >
            {/* Horizontal Grid lines & Y-axis labels */}
            {yTicks.map((tick, i) => (
              <g key={`y-${i}`}>
                <line
                  x1={paddingLeft}
                  y1={tick.y}
                  x2={width - paddingRight}
                  y2={tick.y}
                  stroke="var(--border-subtle, rgba(255,255,255,0.08))"
                  strokeDasharray="3 3"
                />
                <text
                  x={paddingLeft - 8}
                  y={tick.y + 4}
                  textAnchor="end"
                  fill="var(--text-muted, #94a3b8)"
                  fontSize="11"
                  fontFamily="inherit"
                >
                  {tick.val}
                </text>
              </g>
            ))}

            {/* X-axis ticks */}
            {xTicks.map((tick, i) => (
              <g key={`x-${i}`}>
                <line
                  x1={tick.x}
                  y1={height - paddingBottom}
                  x2={tick.x}
                  y2={height - paddingBottom + 5}
                  stroke="var(--border-subtle, rgba(255,255,255,0.2))"
                />
                <text
                  x={tick.x}
                  y={height - paddingBottom + 18}
                  textAnchor="middle"
                  fill="var(--text-muted, #94a3b8)"
                  fontSize="11"
                  fontFamily="inherit"
                >
                  {tick.label}
                </text>
              </g>
            ))}

            {/* Axes Lines */}
            <line
              x1={paddingLeft}
              y1={paddingTop}
              x2={paddingLeft}
              y2={height - paddingBottom}
              stroke="var(--border-default, #334155)"
              strokeWidth="1.5"
            />
            <line
              x1={paddingLeft}
              y1={height - paddingBottom}
              x2={width - paddingRight}
              y2={height - paddingBottom}
              stroke="var(--border-default, #334155)"
              strokeWidth="1.5"
            />

            {/* Line Segments (Gap-Aware) */}
            {segments.map((seg, sIdx) => {
              if (seg.length === 1) {
                // Isolated point: render as a circle dot so it remains visible
                return (
                  <circle
                    key={`dot-${sIdx}`}
                    cx={seg[0].x}
                    cy={seg[0].y}
                    r="4"
                    fill={colorHex}
                  />
                );
              }
              const dPath = seg.reduce((acc, pt, idx) => {
                return `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`;
              }, '');

              return (
                <path
                  key={`seg-${sIdx}`}
                  d={dPath}
                  fill="none"
                  stroke={colorHex}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              );
            })}

            {/* Interactive Data Points */}
            {segments.flatMap((seg) =>
              seg.map((pNode, pIdx) => (
                <circle
                  key={`pt-${pIdx}-${pNode.x}`}
                  cx={pNode.x}
                  cy={pNode.y}
                  r={hoveredPoint === pNode.pt ? 6 : 3.5}
                  fill={hoveredPoint === pNode.pt ? '#ffffff' : colorHex}
                  stroke={colorHex}
                  strokeWidth="2"
                  className="chart-dot"
                  onMouseEnter={() => setHoveredPoint(pNode.pt)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  role="button"
                  tabIndex={0}
                  aria-label={`${pNode.pt.value?.toFixed(1)} ${unit} at ${pNode.pt.timeLabel}`}
                />
              ))
            )}
          </svg>

          {/* Hover Tooltip Overlay */}
          {hoveredPoint && hoveredPoint.value !== null && (
            <div
              className="chart-tooltip"
              role="tooltip"
              style={{
                position: 'absolute',
                top: 10,
                right: 20,
                pointerEvents: 'none',
              }}
            >
              <div className="tooltip-value" style={{ color: colorHex }}>
                {hoveredPoint.value.toFixed(1)} {unit}
              </div>
              <div className="tooltip-time">Measured: {hoveredPoint.measurementTime}</div>
              <div className="tooltip-quality">
                Quality: <span className={`quality-tag ${hoveredPoint.quality}`}>{hoveredPoint.quality}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
