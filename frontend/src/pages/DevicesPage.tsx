import React from 'react';
import { StatusBadge } from '../components/feedback/StatusBadge';
import { EmptyState } from '../components/feedback/EmptyState';

export const DevicesPage: React.FC = () => {
  return (
    <div>
      <section style={{ marginBottom: 'var(--space-2xl)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: 'var(--space-xs)' }}>
          <StatusBadge status="unconfirmed" label="Physical Hardware Unconfirmed" />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Procurement & Board Selection In Progress</span>
        </div>
        <h1>Hardware Devices & Sensor Nodes</h1>
        <p style={{ fontSize: '1.05rem', maxWidth: '850px' }}>
          This page represents the management surface for physical and diagnostic sensor nodes. In accordance with project requirements, no fabricated sensor telemetry or simulated production devices are presented.
        </p>
      </section>

      {/* Hardware Status Banner */}
      <section className="card" style={{ marginBottom: 'var(--space-xl)', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
          <span style={{ fontSize: '2rem' }} aria-hidden="true">⚠️</span>
          <div>
            <h3 style={{ color: 'var(--accent-amber)', marginBottom: '0.25rem' }}>
              Physical Hardware Procurement Boundary
            </h3>
            <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
              Physical ESP32 microcontrollers and environmental sensor modules (DHT22 / SHT31 / BME280) have not yet been purchased or deployed to physical worksites.
            </p>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
              The embedded firmware scaffolding and Hardware Abstraction Layer (HAL) were completed in Module 5, establishing strongly typed C++ interfaces (<code style={{ color: 'var(--accent-cyan)' }}>reading_types.h</code>, <code style={{ color: 'var(--accent-cyan)' }}>ISensor</code>, <code style={{ color: 'var(--accent-cyan)' }}>alert_logic.h</code>) ready for pinout configuration upon board delivery.
            </p>
          </div>
        </div>
      </section>

      {/* Disconnected State / No Connected Devices */}
      <section style={{ marginBottom: 'var(--space-xl)' }}>
        <EmptyState
          title="No Connected Physical Devices"
          description="Backend device listing endpoint (GET /api/v1/devices) is scheduled for subsequent modules. The telemetry ingestion endpoint (POST /api/v1/readings) is operational and accepts authenticated telemetry over HTTPS with SHA-256 pre-shared key validation."
        />
      </section>

      {/* Telemetry Contract Specification Reference */}
      <section className="card">
        <h3 style={{ marginBottom: 'var(--space-sm)' }}>Telemetry Ingestion Contract (Module 6)</h3>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: 'var(--space-md)' }}>
          When hardware is connected, telemetry will transmit according to the established JSON schema:
        </p>

        <div className="table-container">
          <table className="data-table" aria-label="Device Telemetry Contract">
            <thead>
              <tr>
                <th scope="col">Field</th>
                <th scope="col">Type</th>
                <th scope="col">Validation Rule</th>
                <th scope="col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>device_code</code></td>
                <td>String</td>
                <td>Required, registered device code</td>
                <td>Unique alphanumeric identifier for the node</td>
              </tr>
              <tr>
                <td><code>event_id</code></td>
                <td>String</td>
                <td>Required, unique per device</td>
                <td>Idempotency key for deduplication</td>
              </tr>
              <tr>
                <td><code>temperature_c</code></td>
                <td>Number</td>
                <td>Physical bounds: [-50°C, 100°C]</td>
                <td>Ambient dry-bulb temperature</td>
              </tr>
              <tr>
                <td><code>relative_humidity_pct</code></td>
                <td>Number</td>
                <td>Physical bounds: [0%, 100%]</td>
                <td>Relative ambient humidity percentage</td>
              </tr>
              <tr>
                <td><code>source_mode</code></td>
                <td>String</td>
                <td><code>hardware | simulated | diagnostic</code></td>
                <td>Distinguishes real physical from bench test data</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
