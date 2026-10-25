import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';

export const AppLayout: React.FC = () => {
  return (
    <div className="app-container">
      {/* Skip to main content link for keyboard/screen-reader accessibility */}
      <a
        href="#main-content"
        style={{
          position: 'absolute',
          left: '-9999px',
          top: 'auto',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
          zIndex: 999,
          padding: '0.75rem 1.5rem',
          background: 'var(--accent-amber)',
          color: 'var(--text-inverse)',
          fontWeight: 700,
          borderRadius: 'var(--radius-md)',
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = 'fixed';
          e.currentTarget.style.left = '1rem';
          e.currentTarget.style.top = '1rem';
          e.currentTarget.style.width = 'auto';
          e.currentTarget.style.height = 'auto';
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = 'absolute';
          e.currentTarget.style.left = '-9999px';
          e.currentTarget.style.width = '1px';
          e.currentTarget.style.height = '1px';
        }}
      >
        Skip to main content
      </a>

      <Header />

      <main id="main-content" className="content-wrapper" tabIndex={-1}>
        <Outlet />
      </main>

      <Footer />
    </div>
  );
};
