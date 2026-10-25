import React from 'react';
import { Link } from 'react-router-dom';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="feedback-box" style={{ maxWidth: '600px', margin: 'var(--space-2xl) auto' }}>
      <svg
        className="feedback-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--accent-amber)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M16 16s-1.5-2-4-2-4 2-4 2" />
        <line x1="9" y1="9" x2="9.01" y2="9" />
        <line x1="15" y1="9" x2="15.01" y2="9" />
      </svg>
      <h1>404 — Page Not Found</h1>
      <p className="feedback-desc">
        The requested URL was not recognized by the HeatShield Bharat application router.
      </p>
      <Link to="/" className="btn btn-primary">
        Return to System Overview
      </Link>
    </div>
  );
};
