export const SESSION_KEY = 'driftguard.session';

export function toSession(tokenResponse, now = Date.now()) {
  return {
    token: tokenResponse.access_token,
    username: tokenResponse.username,
    role: tokenResponse.role,
    expiresAt: now + tokenResponse.expires_in * 1000,
  };
}

export function loadSession(storage = globalThis.sessionStorage, now = Date.now()) {
  let raw;
  try { raw = storage.getItem(SESSION_KEY); } catch { return null; }
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    const valid = value
      && typeof value.token === 'string'
      && typeof value.username === 'string'
      && typeof value.role === 'string'
      && Number.isFinite(value.expiresAt);
    if (!valid || value.expiresAt <= now) {
      storage.removeItem(SESSION_KEY);
      return null;
    }
    return value;
  } catch {
    storage.removeItem(SESSION_KEY);
    return null;
  }
}

export function saveSession(session, storage = globalThis.sessionStorage) {
  storage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(storage = globalThis.sessionStorage) {
  storage.removeItem(SESSION_KEY);
}
