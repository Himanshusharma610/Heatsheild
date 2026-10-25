import React from 'react';

export interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
  className = '',
}) => {
  return (
    <div className={`feedback-box ${className}`}>
      <svg
        className="feedback-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
      <h3 className="feedback-title">{title}</h3>
      <p className="feedback-desc">{description}</p>
      {actionText && onAction && (
        <button type="button" className="btn btn-secondary" onClick={onAction}>
          {actionText}
        </button>
      )}
    </div>
  );
};
