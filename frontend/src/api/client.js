const DEFAULT_BASE = (import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000')
  .replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, detail = null, cause } = {}) {
    super(message, { cause });
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function hostOf(baseUrl) {
  try { return new URL(baseUrl).host; } catch { return baseUrl; }
}

function cleanDetail(detail) {
  if (typeof detail !== 'string') return null;
  return detail.replace(/^Scan refused:\s*/i, '').trim() || null;
}

export function describeStatus(status, detail) {
  const value = cleanDetail(detail);
  switch (status) {
    case 401: return 'Sign in to continue.';
    case 403: return value ?? 'This action is not permitted for your role.';
    case 404: return value ?? 'The requested record was not found.';
    case 409: return value ?? 'That record already exists.';
    case 422: return value
      ? `The request was refused: ${value}`
      : 'The request was refused. Check the fields and approved scope.';
    case 429: return 'Too many attempts. Wait a minute, then retry.';
    case 503: return 'The API is not ready. Check the database, then retry.';
    default: return value ?? `The API returned HTTP ${status}.`;
  }
}

export function createApiClient({
  baseUrl = DEFAULT_BASE,
  getToken = () => null,
  fetchImpl = globalThis.fetch,
  onUnauthorized = () => {},
} = {}) {
  async function request(path, { method = 'GET', body, signal } = {}) {
    const headers = { Accept: 'application/json' };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    let response;
    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (error) {
      if (error?.name === 'AbortError') throw error;
      throw new ApiError(
        `API unreachable at ${hostOf(baseUrl)}. Start the backend, then retry.`,
        { cause: error },
      );
    }

    if (!response.ok) {
      let detail = null;
      try { detail = (await response.json())?.detail ?? null; } catch { /* non-JSON error */ }
      if (response.status === 401) onUnauthorized();
      throw new ApiError(describeStatus(response.status, detail), {
        status: response.status,
        detail,
      });
    }

    if (response.status === 204) return null;
    return response.json();
  }

  return {
    request,
    targets: () => request('/api/targets'),
    target: (id) => request(`/api/targets/${id}`),
    history: (id, { limit = 20, signal } = {}) =>
      request(`/api/targets/${id}/history?limit=${limit}`, { signal }),
    stats: () => request('/api/stats'),
    evaluation: () => request('/api/evaluation'),
    redactedEvidence: (scanId, { signal } = {}) =>
      request(`/api/scans/${scanId}/evidence/redacted`, { signal }),
    login: (username, password) =>
      request('/api/auth/token', { method: 'POST', body: { username, password } }),
    createTarget: (payload) =>
      request('/api/targets', { method: 'POST', body: payload }),
    runScan: (id) => request(`/api/targets/${id}/scans`, { method: 'POST' }),
  };
}
