import { describe, expect, it } from 'vitest';

import { SESSION_KEY, clearSession, loadSession, saveSession, toSession } from './session';

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

describe('session storage', () => {
  it('converts a token response into an expiring session', () => {
    const session = toSession(
      { access_token: 'jwt', expires_in: 3600, username: 'alice', role: 'admin' },
      1_000,
    );
    expect(session).toEqual({
      token: 'jwt', username: 'alice', role: 'admin', expiresAt: 3_601_000,
    });
  });

  it('round-trips a live session', () => {
    const storage = memoryStorage();
    saveSession({ token: 'jwt', username: 'alice', role: 'admin', expiresAt: 5_000 }, storage);
    expect(loadSession(storage, 4_999)).toMatchObject({ token: 'jwt', username: 'alice' });
  });

  it('drops expired and malformed sessions instead of using them', () => {
    const expired = memoryStorage({
      [SESSION_KEY]: JSON.stringify({
        token: 'jwt', username: 'alice', role: 'admin', expiresAt: 5_000,
      }),
    });
    expect(loadSession(expired, 5_000)).toBeNull();
    expect(expired.getItem(SESSION_KEY)).toBeNull();

    const malformed = memoryStorage({ [SESSION_KEY]: '{not json' });
    expect(loadSession(malformed, 1)).toBeNull();
    expect(clearSession(malformed)).toBeUndefined();
  });
});
