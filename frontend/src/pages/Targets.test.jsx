import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Targets } from './Targets';

const target = {
  id: 1,
  name: 'eservices-lab',
  address: 'https://127.0.0.1:8443',
  target_type: 'web',
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls', 'network'],
  approved_ports: [8443, 8080],
  last_scan: {
    id: 4, status: 'completed',
    started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z',
  },
  scannable: true,
  refusal_reasons: [],
};

function renderPage(overrides = {}) {
  const props = {
    client: { runScan: vi.fn(), createTarget: vi.fn() },
    targets: [target],
    loading: false,
    error: null,
    onReload: vi.fn(),
    onOpen: vi.fn(),
    onScanQueued: vi.fn(),
    onRegistered: vi.fn(),
    session: null,
    ...overrides,
  };
  render(<Targets {...props} />);
  return props;
}

describe('Targets', () => {
  it('reads as a register: identity, authorisation, scope, last scan', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Targets' })).toBeTruthy();
    expect(screen.getByText('eservices-lab')).toBeTruthy();
    expect(screen.getByText('TLS / NETWORK')).toBeTruthy();
    expect(screen.getByText(/#4 · completed · 12 Nov 2026/)).toBeTruthy();
  });

  it('disables Run scan and states every refusal reason', () => {
    renderPage({
      targets: [{
        ...target,
        scannable: false,
        refusal_reasons: ['target must be active', 'approved scope is empty'],
      }],
    });
    const run = screen.getByRole('button', { name: 'Run scan' });
    expect(run.disabled).toBe(true);
    expect(screen.getByText('target must be active approved scope is empty')).toBeTruthy();
  });

  it('queues a scan and hands the settled request to the app', async () => {
    const queued = { id: 5, status: 'queued' };
    const props = renderPage();
    props.client.runScan.mockResolvedValue(queued);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Run scan' }));

    expect(props.client.runScan).toHaveBeenCalledWith(1);
    expect(props.onScanQueued).toHaveBeenCalledWith(target, queued);
  });

  it('invites registration when the register is empty', () => {
    renderPage({ targets: [] });
    expect(screen.getByText('No targets registered.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Register the first target' })).toBeTruthy();
  });
});
