import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { healthService, type ReadyResponse } from '../../services/healthService';
import { StatusBadge } from '../feedback/StatusBadge';

export const Header: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [readiness, setReadiness] = useState<ReadyResponse | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(true);
  const [hasError, setHasError] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    async function probeBackend() {
      setIsChecking(true);
      try {
        const res = await healthService.checkReadiness();
        if (isMounted) {
          setReadiness(res);
          setHasError(false);
        }
      } catch {
        if (isMounted) {
          setHasError(true);
          setReadiness(null);
        }
      } finally {
        if (isMounted) {
          setIsChecking(false);
        }
      }
    }

    probeBackend();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="app-header" role="banner">
      <div className="header-inner">
        <NavLink to="/" className="brand-link" aria-label="HeatShield Bharat Home">
          <div className="brand-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
              <path d="M16 2L4 7V15C4 22.5 9.1 29.2 16 31C22.9 29.2 28 22.5 28 15V7L16 2Z" fill="#1e293b" stroke="#f59e0b" strokeWidth="2"/>
              <path d="M16 6L7 10V15C7 20.8 10.8 26.2 16 27.8C21.2 26.2 25 20.8 25 15V10L16 6Z" fill="#0f172a"/>
              <circle cx="16" cy="15" r="4" fill="#f59e0b"/>
            </svg>
          </div>
          <div className="brand-title">
            <span className="brand-title-main">HeatShield Bharat</span>
            <span className="brand-title-sub">Early-Warning Decision Support</span>
          </div>
        </NavLink>

        <nav aria-label="Main Navigation">
          <ul className="nav-links">
            <li>
              <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Dashboard
              </NavLink>
            </li>
            <li>
              <NavLink to="/overview" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Overview
              </NavLink>
            </li>
            <li>
              <NavLink to="/analytics" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Analytics
              </NavLink>
            </li>
            <li>
              <NavLink to="/devices" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Devices
              </NavLink>
            </li>
            <li>
              <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Alerts
              </NavLink>
            </li>
            <li>
              <NavLink to="/calculator" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                Risk Calculator
              </NavLink>
            </li>
          </ul>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="header-status" title="Backend Live Readiness Probe">
            <span style={{ color: 'var(--text-muted)' }}>Backend:</span>
            {isChecking ? (
              <StatusBadge status="info" label="Checking..." />
            ) : hasError ? (
              <StatusBadge status="error" label="Disconnected" />
            ) : readiness?.status === 'ready' ? (
              <StatusBadge status="ready" label="Connected (DB Ready)" />
            ) : (
              <StatusBadge status="warning" label="Not Ready" />
            )}
          </div>

          <div className="header-auth" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {isAuthenticated && user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8125rem' }}>
                <span
                  style={{
                    backgroundColor:
                      user.role === 'admin'
                        ? '#dc2626'
                        : user.role === 'supervisor'
                        ? '#ea580c'
                        : '#3b82f6',
                    color: '#ffffff',
                    padding: '0.15rem 0.45rem',
                    borderRadius: '4px',
                    fontWeight: 700,
                    fontSize: '0.7rem',
                    textTransform: 'uppercase',
                  }}
                  title={`Role: ${user.role}`}
                >
                  {user.role}
                </span>
                <span
                  style={{ color: '#cbd5e1', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  title={user.email}
                >
                  {user.display_name || user.email}
                </span>
                <button
                  onClick={handleLogout}
                  style={{
                    background: 'transparent',
                    border: '1px solid #475569',
                    borderRadius: '4px',
                    color: '#94a3b8',
                    padding: '0.2rem 0.5rem',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                  }}
                  title="Sign out of your session"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <NavLink
                to="/login"
                style={{
                  backgroundColor: '#f97316',
                  color: '#ffffff',
                  padding: '0.3rem 0.75rem',
                  borderRadius: '4px',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                Sign In
              </NavLink>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
