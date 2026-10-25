import React from 'react';

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data from HeatShield backend...',
  className = '',
}) => {
  return (
    <div className={`feedback-box ${className}`} role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p className="feedback-desc" style={{ marginBottom: 0 }}>
        {message}
      </p>
    </div>
  );
};
