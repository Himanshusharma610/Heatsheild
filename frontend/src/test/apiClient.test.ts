import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { apiRequest, ApiClientError, getApiBaseUrl } from '../services/api';

describe('API Client (services/api.ts)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('builds requests using the configured base URL', async () => {
    const mockResponse = { status: 'healthy', version: '0.1.0' };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockResponse,
    });
    globalThis.fetch = fetchMock;

    const data = await apiRequest<{ status: string }>('/health');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calledUrl = fetchMock.mock.calls[0][0];
    expect(calledUrl).toBe(`${getApiBaseUrl()}/health`);
    expect(data).toEqual(mockResponse);
  });

  it('handles backend ErrorResponse format appropriately', async () => {
    const backendError = {
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid reading parameters supplied.',
        details: { field: 'temperature_c' },
      },
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => backendError,
    });
    globalThis.fetch = fetchMock;

    await expect(apiRequest('/readings')).rejects.toThrow(ApiClientError);

    try {
      await apiRequest('/readings');
    } catch (err) {
      const apiErr = err as ApiClientError;
      expect(apiErr.status).toBe(422);
      expect(apiErr.code).toBe('VALIDATION_ERROR');
      expect(apiErr.message).toBe('Invalid reading parameters supplied.');
      expect(apiErr.details).toEqual({ field: 'temperature_c' });
      expect(apiErr.isNetworkError).toBe(false);
    }
  });

  it('handles network failure with isNetworkError flag', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('Failed to fetch'));
    globalThis.fetch = fetchMock;

    await expect(apiRequest('/ready')).rejects.toThrow(ApiClientError);

    try {
      await apiRequest('/ready');
    } catch (err) {
      const apiErr = err as ApiClientError;
      expect(apiErr.status).toBe(0);
      expect(apiErr.isNetworkError).toBe(true);
      expect(apiErr.message).toContain('Unable to reach backend service');
    }
  });

  it('handles malformed JSON responses deliberately', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => {
        throw new SyntaxError('Unexpected token < in JSON at position 0');
      },
    });
    globalThis.fetch = fetchMock;

    await expect(apiRequest('/broken-json')).rejects.toThrow(ApiClientError);

    try {
      await apiRequest('/broken-json');
    } catch (err) {
      const apiErr = err as ApiClientError;
      expect(apiErr.code).toBe('MALFORMED_JSON');
    }
  });

  it('handles 204 No Content responses cleanly without parsing JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      headers: new Headers(),
    });
    globalThis.fetch = fetchMock;

    const res = await apiRequest('/no-content');
    expect(res).toBeNull();
  });
});
