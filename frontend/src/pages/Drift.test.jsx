import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Drift } from './Drift';

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
      details: { cipher: 'RC4' }, observed_at: '2026-11-12T09:30:00Z',
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

function renderDrift(overrides = {}) {
  const props = {
    client: {
      history: vi.fn().mockResolvedValue(history),
      runScan: vi.fn().mockResolvedValue({ id: 2, status: 'queued' }),
    },
    targets: [target],
    targetsLoading: false,
    targetsError: null,
    targetId: 1,
    onSelectTarget: vi.fn(),
    onOpenTargets: vi.fn(),
    session: null,
    ...overrides,
  };
  render(<Drift {...props} />);
  return props;
}

describe('Drift', () => {
  it('reads the subject, authorisation, baseline, and thread from stored data', async () => {
    renderDrift();
    expect(await screen.findByRole('heading', { name: 'eservices-lab' })).toBeTruthy();
    expect(screen.getByText('A. Owner')).toBeTruthy();
    expect(screen.getByText('Baseline recorded 12 Nov 2026.')).toBeTruthy();
    expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
  });

  it('queues a scan and reloads once', async () => {
    const props = renderDrift();
    await screen.findByRole('heading', { name: 'eservices-lab' });

    await userEvent.setup().click(screen.getByRole('button', { name: 'Run scan' }));

    expect(props.client.runScan).toHaveBeenCalledWith(1);
    await waitFor(() => expect(props.client.history).toHaveBeenCalledTimes(2));
    expect(screen.getByRole('status').textContent).toContain('Scan #2 queued');
  });

  it('refuses to scan a pending target and states why', async () => {
    const pending = {
      ...target,
      authorization_status: 'pending',
      authorized_by: null,
      authorized_at: null,
      authorization_basis: null,
      approved_scope: [],
      approved_ports: [],
      scannable: false,
      refusal_reasons: ['target must be active', 'target must be explicitly authorized'],
    };
    const props = renderDrift({
      targetId: 2,
      targets: [pending],
      client: {
        history: vi.fn().mockResolvedValue({ target: pending, scans: [], fingerprints: {} }),
        runScan: vi.fn(),
      },
    });
    await screen.findByRole('heading', { name: 'eservices-lab' });
    const run = screen.getByRole('button', { name: 'Run scan' });
    expect(run.disabled).toBe(true);
    expect(screen.getByText('target must be active target must be explicitly authorized'))
      .toBeTruthy();
    expect(props.client.runScan).not.toHaveBeenCalled();
  });

  it('shows an explicit empty observation state instead of a grid', async () => {
    renderDrift({
      client: {
        history: vi.fn().mockResolvedValue({ target, scans: [], fingerprints: {} }),
        runScan: vi.fn(),
      },
    });
    expect(await screen.findByText('No observations yet.')).toBeTruthy();
    expect(screen.getByText(/Run a baseline to start the record/)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });
});
