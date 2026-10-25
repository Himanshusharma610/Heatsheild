import React from 'react';
import type { DeviceData } from '../../features/devices/types';
import { StatusBadge } from '../feedback/StatusBadge';

export interface DeviceStatusCardProps {
  devices: DeviceData[];
}

export const DeviceStatusCard: React.FC<DeviceStatusCardProps> = ({ devices }) => {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3>Registered Sensor Nodes Inventory</h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Total nodes registered in database: {devices.length}
          </span>
        </div>
        <StatusBadge status="unconfirmed" label="Hardware Procurement Pending" />
      </div>

      {devices.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-lg) 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          <p style={{ marginBottom: '0.5rem' }}>No sensor nodes are registered in the backend database.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
            Physical ESP32 boards and environmental sensor modules have not yet been purchased. Hardware interfaces and registration scripts will bind once physical hardware is delivered.
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table" aria-label="Device Node Status Table">
            <thead>
              <tr>
                <th scope="col">Device Code</th>
                <th scope="col">Display Name</th>
                <th scope="col">Status</th>
                <th scope="col">Firmware</th>
                <th scope="col">Last Heartbeat (UTC)</th>
                <th scope="col">Active?</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((dev) => (
                <tr key={dev.id}>
                  <td><strong>{dev.device_code}</strong></td>
                  <td>{dev.display_name || '—'}</td>
                  <td>
                    <StatusBadge status={dev.status} />
                  </td>
                  <td><code>{dev.firmware_version ? `v${dev.firmware_version}` : '—'}</code></td>
                  <td>
                    {dev.last_seen_at ? (
                      new Date(dev.last_seen_at).toISOString()
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>Never seen</span>
                    )}
                  </td>
                  <td>
                    <StatusBadge
                      status={dev.is_active ? 'valid' : 'disabled'}
                      label={dev.is_active ? 'Active' : 'Deactivated'}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
