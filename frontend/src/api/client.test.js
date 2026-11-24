import { describe, expect, it, vi } from 'vitest';

import { ApiError, createApiClient } from './client';

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function makeClient(overrides = {}) {
  const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
  const onUnauthorized = vi.fn();
  const client = createApiClient({
    baseUrl: 'http://127.0.0.1:8000',
    getToken: () => 'tok-123',
    fetchImpl,
    onUnauthorized,
    ...overrides,
  });
  return { client, fetchImpl, onUnauthorized };
}

describe('api client', () => {
  it('sends the bearer token and parses JSON', async () => {
    const { client, fetchImpl } = makeClient();
    await client.targets();

    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8000/api/targets');
    expect(init.headers.Authorization).toBe('Bearer tok-123');
  });

  it('omits the token header in local-research mode', async () => {
    const { client, fetchImpl } = makeClient({ getToken: () => null });
    await client.stats();
    expect(fetchImpl.mock.calls[0][1].headers).not.toHaveProperty('Authorization');
  });

  it('requests one history page with the default limit and forwards abort signals', async () => {
    const { client, fetchImpl } = makeClient();
    const controller = new AbortController();
    await client.history(7, { signal: controller.signal });

    expect(fetchImpl.mock.calls[0][0]).toBe(
      'http://127.0.0.1:8000/api/targets/7/history?limit=20',
    );
    expect(fetchImpl.mock.calls[0][1].signal).toBe(controller.signal);
  });

  it('posts credentials and target payloads as JSON', async () => {
    const { client, fetchImpl } = makeClient();
    await client.login('alice', 'correct horse');
    await client.createTarget({ name: 'svc' });

    const [, loginInit] = fetchImpl.mock.calls[0];
    expect(loginInit.method).toBe('POST');
    expect(loginInit.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(loginInit.body)).toEqual({ username: 'alice', password: 'correct horse' });
    expect(fetchImpl.mock.calls[1][1].method).toBe('POST');
  });

  it('reports 401, notifies the shell, and keeps the status', async () => {
    const { client, onUnauthorized } = makeClient({
      fetchImpl: vi.fn().mockResolvedValue(jsonResponse({ detail: 'Not authenticated' }, 401)),
    });
    await expect(client.targets()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('turns a transport failure into actionable copy', async () => {
    const { client } = makeClient({
      fetchImpl: vi.fn().mockRejectedValue(new TypeError('fetch failed')),
    });
    await expect(client.targets()).rejects.toBeInstanceOf(ApiError);
    await expect(client.targets()).rejects.toThrow(
      'API unreachable at 127.0.0.1:8000. Start the backend, then retry.',
    );
  });

  it('surfaces a scan refusal without the raw FastAPI prefix', async () => {
    const { client } = makeClient({
      fetchImpl: vi.fn().mockResolvedValue(jsonResponse(
        { detail: 'Scan refused: target must be explicitly authorized' }, 422,
      )),
    });
    await expect(client.runScan(4)).rejects.toThrow(
      'The request was refused: target must be explicitly authorized',
    );
  });

  it('does not notify on abort', async () => {
    const abort = Object.assign(new Error('aborted'), { name: 'AbortError' });
    const { client, onUnauthorized } = makeClient({
      fetchImpl: vi.fn().mockRejectedValue(abort),
    });
    await expect(client.targets()).rejects.toBe(abort);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
