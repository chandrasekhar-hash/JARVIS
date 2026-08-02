const API_BASE = 'http://localhost:8000/api';

export async function fetchWithAuth(endpoint, options = {}) {
  const { timeout = 15000, ...customOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  const config = {
    ...customOptions,
    signal: customOptions.signal || controller.signal,
    credentials: 'include', // Sends HTTP-Only cookies
    headers: {
      ...defaultHeaders,
      ...customOptions.headers,
    },
  };

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

  let response;
  try {
    response = await fetch(url, config);
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw new Error('JARVIS services are temporarily unavailable. Please try again.');
  } finally {
    clearTimeout(timeoutId);
  }

  // If 401 Unauthorized, attempt silent token refresh once
  if (response.status === 401 && !endpoint.includes('/session/refresh') && !endpoint.includes('/auth/login')) {
    try {
      const refreshRes = await fetch(`${API_BASE}/session/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshRes.ok) {
        // Retry original request
        response = await fetch(url, config);
      }
    } catch (e) {
      console.warn('AXL ApiInterceptor: Silent session refresh failed', e);
    }
  }

  return response;
}
