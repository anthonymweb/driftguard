import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Settings } from './Settings';

const stats = {
  targets: 5, scans: 9, evidence: 142, drift_events: 38,
  auth_mode: 'local_research',
  redaction: { enabled: true, token_map: 'local-only' },
};

describe('Settings', () => {
  it('reports connection, mode, redaction, footprint, and version', async () => {
    const client = { stats: vi.fn().mockResolvedValue(stats) };
    render(<Settings client={client} session={null} apiBase="http://127.0.0.1:8000" />);

    await screen.findByText('Connection');
    expect(screen.getByText('http://127.0.0.1:8000')).toBeTruthy();
    expect(screen.getByText('LOCAL RESEARCH')).toBeTruthy();
    expect(screen.getByText(/token map never leaves/)).toBeTruthy();
    expect(screen.getByText('targets')).toBeTruthy();
    expect(screen.getByText('drift events')).toBeTruthy();
    expect(screen.getByText('5')).toBeTruthy();
    expect(screen.getByText('38')).toBeTruthy();
  });

  it('names the signed-in operator in JWT mode', async () => {
    const client = { stats: vi.fn().mockResolvedValue({ ...stats, auth_mode: 'jwt' }) };
    render(<Settings client={client} session={{ username: 'alice', role: 'operator' }} apiBase="http://127.0.0.1:8000" />);

    await screen.findByText('Connection');
    expect(screen.getByText(/JWT/)).toBeTruthy();
    expect(screen.getByText(/alice · operator/)).toBeTruthy();
  });

  it('shows an actionable error instead of empty counts when unreachable', async () => {
    const client = { stats: vi.fn().mockRejectedValue(new Error('API unreachable at 127.0.0.1:8000. Start the backend, then retry.')) };
    render(<Settings client={client} session={null} apiBase="http://127.0.0.1:8000" />);
    expect((await screen.findByRole('alert')).textContent)
      .toContain('API unreachable at 127.0.0.1:8000');
    expect(screen.queryByText('drift events')).toBeNull();
  });

  it('renders the footprint as four count tiles and the real UI version', async () => {
    const client = { stats: vi.fn().mockResolvedValue(stats) };
    render(<Settings client={client} session={null} apiBase="http://127.0.0.1:8000" />);

    await screen.findByText('Connection');
    expect(document.querySelectorAll('.footprint-tiles li')).toHaveLength(4);
    expect(screen.getByText('scans')).toBeTruthy();
    expect(screen.getByText('9')).toBeTruthy();
    expect(screen.getByText('evidence')).toBeTruthy();
    expect(screen.getByText('142')).toBeTruthy();
    expect(screen.getByText(/^driftguard-ui \d+\.\d+\.\d+$/)).toBeTruthy();
  });

  it('shows real authorisation provenance in the operator panel', async () => {
    render(<Settings
      client={{ stats: vi.fn().mockResolvedValue(stats) }}
      session={null}
      apiBase="http://127.0.0.1:8000"
      targets={[{
        id: 1,
        name: 'eservices-lab',
        authorization_status: 'authorized',
        authorized_by: 'A. Owner',
        authorized_at: '2026-11-12T09:30:00Z',
        authorization_basis: 'written approval',
        approved_scope: ['tls', 'network'],
        approved_ports: [8443],
      }]}
    />);

    await screen.findByText('Connection');
    expect(screen.getByText('A. Owner')).toBeTruthy();
    expect(screen.getByText('written approval')).toBeTruthy();
    expect(screen.getByText(/TLS \/ NETWORK/)).toBeTruthy();
    expect(screen.queryByText(/PID/)).toBeNull();
    expect(screen.queryByText(/GPG/)).toBeNull();
  });
});
