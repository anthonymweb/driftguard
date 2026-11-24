import { describe, expect, it } from 'vitest';

import {
  emptyTargetForm,
  parsePorts,
  toTargetPayload,
  validateTargetForm,
} from './target-form';

function filled(overrides = {}) {
  return {
    ...emptyTargetForm(),
    name: 'eservices-lab',
    address: 'https://127.0.0.1:8443',
    ...overrides,
  };
}

describe('target form', () => {
  it('parses, dedupes, and sorts approved ports', () => {
    expect(parsePorts('8443, 8080 8443')).toEqual({ ports: [8080, 8443], error: null });
    expect(parsePorts('')).toEqual({ ports: [], error: null });
  });

  it('rejects non-numeric and out-of-range ports with specific copy', () => {
    expect(parsePorts('8443, https').error).toBe('“https” is not a port number.');
    expect(parsePorts('0').error).toBe('Port 0 is outside 1–65535.');
    expect(parsePorts('65536').error).toBe('Port 65536 is outside 1–65535.');
  });

  it('allows a pending target with no scope, because it cannot be scanned', () => {
    expect(validateTargetForm(filled())).toEqual({});
  });

  it('requires who, when, why, scope, and ports when authorisation is claimed', () => {
    const errors = validateTargetForm(filled({ authorization_status: 'authorized' }));
    expect(errors.authorized_by).toContain('who authorised');
    expect(errors.authorized_at).toContain('when');
    expect(errors.authorization_basis).toContain('basis');
    expect(errors.approved_scope).toContain('approved area');
    expect(errors.approved_ports).toContain('approved port');
  });

  it('requires a wordlist only when discovery is enabled', () => {
    expect(validateTargetForm(filled({ discovery_enabled: true })).discovery_wordlist)
      .toContain('wordlist');
    expect(validateTargetForm(filled({ discovery_enabled: false }))).toEqual({});
  });

  it('builds the exact payload and leaves pending authorisation fields null', () => {
    const payload = toTargetPayload(filled({
      approved_scope: ['tls', 'network'],
      approved_ports: [8443],
    }));
    expect(payload).toEqual({
      name: 'eservices-lab',
      address: 'https://127.0.0.1:8443',
      target_type: 'web',
      authorization_status: 'pending',
      authorized_by: null,
      authorized_at: null,
      authorization_basis: null,
      approved_scope: ['tls', 'network'],
      approved_ports: [8443],
      discovery_enabled: false,
      discovery_wordlist: null,
      status: 'active',
    });
  });

  it('sends an ISO UTC instant for an authorised target', () => {
    const payload = toTargetPayload(filled({
      authorization_status: 'authorized',
      authorized_by: 'A. Owner',
      authorized_at: '2026-11-12',
      authorization_basis: 'written approval',
      approved_scope: ['tls'],
      approved_ports: [8443],
    }));
    expect(payload.authorized_at).toBe('2026-11-12T00:00:00.000Z');
    expect(payload.authorized_by).toBe('A. Owner');
  });
});
