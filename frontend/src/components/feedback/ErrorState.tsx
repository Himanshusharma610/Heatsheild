import React from 'react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Connection or Processing Error',
  message,
  onRetry,
  className = '',
}) => {
  return (
    <div className={`feedback-box ${className}`} role="alert" style={{ borderColor: 'rgba(244, 63, 94, 0.4)' }}>
      <svg
        className="feedback-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--accent-rose)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <h3 className="feedback-title" style={{ color: 'var(--accent-rose)' }}>
        {title}
      </h3>
      <p className="feedback-desc">{message}</p>
      {onRetry && (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Retry Request
        </button>
      )}
    </div>
  );
};
