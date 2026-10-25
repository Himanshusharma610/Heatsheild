import React from 'react';

export interface StatusBadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = '' }) => {
  const normalized = status.toLowerCase().replace(/\s+/g, '_');
  const displayLabel = label || status.replace(/_/g, ' ');

  return (
    <span className={`status-badge ${normalized} ${className}`} aria-label={`Status: ${displayLabel}`}>
      <span className="status-dot" aria-hidden="true" />
      <span>{displayLabel}</span>
    </span>
  );
};
