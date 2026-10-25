import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="app-footer" role="contentinfo">
      <div className="footer-inner">
        <div className="footer-disclaimer">
          <strong>Important Safety Declaration:</strong> HeatShield Bharat provides environmental screening indicators and decision-support notifications for worksite supervisors. This system <strong>does not</strong> provide medical diagnoses, predict individual heatstroke or thermal strain, or certify occupational safety compliance. Thresholds are provisional development settings.
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <span>HeatShield Bharat — Final Year Major Project (B.Tech / Engineering)</span>
            <span style={{ margin: '0 0.5rem', color: 'var(--border-medium)' }}>•</span>
            <span>ESP32 Physical Hardware Status: <span style={{ color: 'var(--accent-amber)' }}>Unconfirmed (Procurement Pending)</span></span>
          </div>
          <div>
            <span>Backend: FastAPI + PostgreSQL</span>
            <span style={{ margin: '0 0.5rem', color: 'var(--border-medium)' }}>•</span>
            <span>Frontend: React + TypeScript (Module 9 Foundation)</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
