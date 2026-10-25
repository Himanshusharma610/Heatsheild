/**
 * Authentication service communicating with FastAPI backend /api/v1/auth endpoints.
 */

import type { AuthResponse, LoginCredentials, User } from '../features/auth/types';
import { apiClient, setAuthToken } from './api';

export const authService = {
  /**
   * Submit credentials to authenticate user and store token.
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const data = await apiClient.post<AuthResponse>('/auth/login', credentials);
    if (data && data.access_token) {
      setAuthToken(data.access_token);
    }
    return data;
  },

  /**
   * Retrieve current user profile from backend using stored token.
   */
  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/auth/me');
  },

  /**
   * Acknowledge logout with backend and clear stored token.
   */
  async logout(): Promise<void> {
    try {
      await apiClient.post<{ message: string }>('/auth/logout');
    } catch {
      // Clear token locally regardless of backend availability
    } finally {
      setAuthToken(null);
    }
  },
};
