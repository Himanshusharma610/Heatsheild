/**
 * Type-safe HTTP API client for HeatShield Bharat backend.
 *
 * Configured via VITE_API_BASE_URL (defaults to http://localhost:8000/api/v1).
 * Never embed sensitive tokens or secrets here.
 */

export interface BackendErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface BackendErrorResponse {
  error: BackendErrorDetail;
}

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details: unknown;
  public readonly isNetworkError: boolean;

  constructor(message: string, status = 0, code = 'CLIENT_ERROR', details: unknown = null, isNetworkError = false) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.isNetworkError = isNetworkError;
  }
}

export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return 'http://localhost:8000/api/v1';
}

const TOKEN_STORAGE_KEY = 'heatshield_auth_token';
let inMemoryToken: string | null = null;

export function getAuthToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  inMemoryToken = token;
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // SessionStorage may be restricted in some browser settings
  }
}

type UnauthorizedListener = () => void;
const unauthorizedListeners: Set<UnauthorizedListener> = new Set();

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}

function notifyUnauthorized(): void {
  unauthorizedListeners.forEach((fn) => {
    try {
      fn();
    } catch {
      // Ignore listener errors
    }
  });
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  const { timeoutMs = 10000, headers, ...restOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const requestHeaders: Record<string, string> = {
    'Accept': 'application/json',
    ...(headers as Record<string, string>),
  };

  const token = getAuthToken();
  if (token && !requestHeaders['Authorization']) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  }

  if (restOptions.body && typeof restOptions.body === 'string' && !requestHeaders['Content-Type']) {
    requestHeaders['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...restOptions,
      headers: requestHeaders,
      signal: options.signal || controller.signal,
    });
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiClientError(
        `Request to backend timed out after ${timeoutMs}ms. Ensure the backend server is running at ${baseUrl}.`,
        0,
        'TIMEOUT',
        null,
        true
      );
    }
    const message = err instanceof Error ? err.message : 'Network connection failure';
    throw new ApiClientError(
      `Unable to reach backend service at ${url}: ${message}. Verify backend connectivity and CORS configuration.`,
      0,
      'NETWORK_ERROR',
      null,
      true
    );
  } finally {
    clearTimeout(timeoutId);
  }

  // Handle empty successful responses (e.g. 204 No Content)
  if (response.status === 204) {
    return null as unknown as T;
  }

  // Parse JSON response safely
  let responseData: unknown;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      responseData = await response.json();
    } catch {
      throw new ApiClientError(
        `Received malformed JSON from backend (${response.status} ${response.statusText}).`,
        response.status,
        'MALFORMED_JSON'
      );
    }
  } else {
    const rawText = await response.text();
    responseData = { text: rawText };
  }

  if (!response.ok) {
    if (response.status === 401 && !cleanEndpoint.startsWith('/auth/login')) {
      notifyUnauthorized();
    }

    // Attempt to parse standard backend error format: { error: { code, message, details } }
    if (responseData && typeof responseData === 'object' && 'error' in responseData) {
      const backendErr = (responseData as BackendErrorResponse).error;
      throw new ApiClientError(
        backendErr.message || `Backend returned error ${response.status}`,
        response.status,
        backendErr.code || `HTTP_${response.status}`,
        backendErr.details
      );
    }

    throw new ApiClientError(
      `HTTP ${response.status} (${response.statusText}): ${JSON.stringify(responseData)}`,
      response.status,
      `HTTP_${response.status}`
    );
  }

  return responseData as T;
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),
};
