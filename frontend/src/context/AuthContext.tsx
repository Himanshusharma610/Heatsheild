import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { AuthState, LoginCredentials, User, UserRole } from '../features/auth/types';
import { getAuthToken, onUnauthorized, setAuthToken } from '../services/api';
import { authService } from '../services/authService';

export interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
  canManageAlerts: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize session on mount
  useEffect(() => {
    let isMounted = true;
    const initialToken = getAuthToken();

    if (!initialToken) {
      setIsLoading(false);
      return;
    }

    authService
      .getCurrentUser()
      .then((currentUser) => {
        if (isMounted) {
          setUser(currentUser);
          setTokenState(initialToken);
        }
      })
      .catch(() => {
        if (isMounted) {
          setAuthToken(null);
          setUser(null);
          setTokenState(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Listen for 401 Unauthorized events from API calls to handle session expiry
  useEffect(() => {
    const unsubscribe = onUnauthorized(() => {
      setAuthToken(null);
      setUser(null);
      setTokenState(null);
    });
    return unsubscribe;
  }, []);

  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await authService.login(credentials);
      setUser(response.user);
      setTokenState(response.access_token);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setTokenState(null);
      setIsLoading(false);
    }
  }, []);

  const hasRole = useCallback(
    (roles: UserRole | UserRole[]): boolean => {
      if (!user) return false;
      const roleList = Array.isArray(roles) ? roles : [roles];
      return roleList.includes(user.role);
    },
    [user]
  );

  const canManageAlerts = useMemo(() => {
    return user ? user.role === 'supervisor' || user.role === 'admin' : false;
  }, [user]);

  const isAdmin = useMemo(() => {
    return user ? user.role === 'admin' : false;
  }, [user]);

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      token,
      isAuthenticated: !!user && !!token,
      isLoading,
      login,
      logout,
      hasRole,
      canManageAlerts,
      isAdmin,
    }),
    [user, token, isLoading, login, logout, hasRole, canManageAlerts, isAdmin]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
