import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

const target = {
  id: 1,
  name: 'eservices-lab',
  address: 'https://127.0.0.1:8443',
  target_type: 'web',
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls'],
  approved_ports: [8443],
  last_scan: null,
  scannable: true,
  refusal_reasons: [],
};

const history = {
  target,
  scans: [{
    scan: {
      id: 1, target_id: 1, status: 'completed',
      started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z',
      is_baseline: true, label: null, error: null,
    },
    comparable: true,
    evidence: [{
      id: 1, scan_id: 1, fingerprint: 'eservices-lab/TLS/a', category: 'TLS',
      title: 'Legacy TLS', severity: 'High', resource: '127.0.0.1:8443',
      details: {}, observed_at: '2026-11-12T09:30:00Z',
    }],
    drift: [],
    summary: { state: 'BASELINE', counts: { NEW: 0, PERSISTENT: 0, FIXED: 0, RECURRING: 0 } },
  }],
  fingerprints: {
    'eservices-lab/TLS/a': {
      title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: '127.0.0.1:8443',
    },
  },
};

function makeClient() {
  return {
    targets: vi.fn().mockResolvedValue([target]),
    history: vi.fn().mockResolvedValue(history),
    stats: vi.fn().mockResolvedValue({ targets: 1, scans: 1, evidence: 1, drift_events: 0, auth_mode: 'local_research', redaction: { enabled: true } }),
    evaluation: vi.fn().mockResolvedValue({ available: false, reason: 'no scans' }),
    runScan: vi.fn(),
    createTarget: vi.fn(),
    login: vi.fn(),
    redactedEvidence: vi.fn().mockResolvedValue([]),
  };
}

beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState(null, '', '#/');
});

describe('App', () => {
  it('resolves the default Drift route to the first target', async () => {
    const client = makeClient();
    render(<App makeClient={() => client} />);

    await waitFor(() => expect(window.location.hash).toBe('#/drift/1'));
    expect(await screen.findByRole('heading', { name: 'eservices-lab' })).toBeTruthy();
    expect(client.history).toHaveBeenCalledTimes(1);
  });

  it('sends an empty installation to the target register', async () => {
    const client = makeClient();
    client.targets.mockResolvedValue([]);
    render(<App makeClient={() => client} />);

    await waitFor(() => expect(window.location.hash).toBe('#/targets'));
    expect(await screen.findByText('No targets registered.')).toBeTruthy();
    expect(client.history).not.toHaveBeenCalled();
  });

  it('opens sign-in when the API answers 401 and closes it after a token', async () => {
    const client = makeClient();
    let seam = null;
    const makeClientWithSeam = (options) => {
      seam = options;
      return client;
    };
    render(<App makeClient={makeClientWithSeam} />);
    await screen.findByRole('heading', { name: 'eservices-lab' });

    seam.onUnauthorized();
    expect(await screen.findByRole('dialog')).toBeTruthy();

    client.login.mockResolvedValue({
      access_token: 'jwt', expires_in: 3600, username: 'alice', role: 'admin',
    });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'alice');
    await user.type(screen.getByLabelText('Password'), 'hunter2');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(window.sessionStorage.getItem('driftguard.session')).toContain('alice');
    expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
  });
});
