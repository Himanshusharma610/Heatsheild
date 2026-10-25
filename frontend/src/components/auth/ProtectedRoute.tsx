import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { UserRole } from '../../features/auth/types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, user, hasRole } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '240px',
          color: 'var(--color-text-muted, #94a3b8)',
          fontSize: '0.95rem',
        }}
        role="status"
        aria-live="polite"
      >
        <span>Verifying authentication session...</span>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && !hasRole(allowedRoles)) {
    return (
      <div
        style={{
          padding: '2rem',
          maxWidth: '600px',
          margin: '2rem auto',
          backgroundColor: '#1e293b',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          color: '#f8fafc',
          textAlign: 'center',
        }}
        role="alert"
      >
        <h2 style={{ color: '#ef4444', marginBottom: '0.5rem', fontSize: '1.25rem' }}>Access Denied</h2>
        <p style={{ color: '#94a3b8', marginBottom: '1rem' }}>
          Your current account role (<strong>{user.role}</strong>) does not have authorization to access this view.
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
