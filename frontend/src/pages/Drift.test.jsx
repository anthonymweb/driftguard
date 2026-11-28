import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Drift } from './Drift';

const target = {
  id: 1,
  name: 'eservices-lab',
  address: 'https://127.0.0.1:8443',
  target_type: 'web',
  status: 'active',
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

const originalMatchMedia = window.matchMedia;

afterEach(() => {
  window.matchMedia = originalMatchMedia;
});

function renderDrift(overrides = {}, { narrow = false } = {}) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: narrow && query === '(max-width: 900px)',
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
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
  const { container } = render(<Drift {...props} />);
  return { ...props, container };
}

function twoThreadHistory() {
  return {
    target,
    scans: [{
      scan: {
        id: 1, target_id: 1, status: 'completed',
        started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z',
        is_baseline: true, label: 'DEMO-0', error: null,
      },
      comparable: true,
      evidence: [
        {
          id: 1, scan_id: 1, fingerprint: 'eservices-lab/TLS/a', category: 'TLS',
          title: 'First thread', severity: 'High', resource: '127.0.0.1:8443',
          details: { cipher: 'RC4' }, observed_at: '2026-11-12T09:30:00Z',
        },
        {
          id: 2, scan_id: 1, fingerprint: 'eservices-lab/TLS/b', category: 'TLS',
          title: 'Second thread', severity: 'Low', resource: '127.0.0.1:8444',
          details: { protocol: 'TLSv1.0' }, observed_at: '2026-11-12T09:30:00Z',
        },
      ],
      drift: [],
      summary: { state: 'BASELINE', counts: {} },
    }],
    fingerprints: {
      'eservices-lab/TLS/a': {
        title: 'First thread', category: 'TLS', severity: 'High', resource: '127.0.0.1:8443',
      },
      'eservices-lab/TLS/b': {
        title: 'Second thread', category: 'TLS', severity: 'Low', resource: '127.0.0.1:8444',
      },
    },
  };
}

describe('Drift', () => {
  it('reads the subject, authorisation, baseline, and thread from stored data', async () => {
    renderDrift();
    expect(await screen.findByRole('heading', { name: 'eservices-lab' })).toBeTruthy();
    expect(screen.getByText('A. Owner')).toBeTruthy();
    expect(screen.getByText('Baseline recorded 12 Nov 2026.')).toBeTruthy();
    expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
  });

  it('keeps the reference section order with real stored values', async () => {
    const { container } = await renderDrift();
    await screen.findByRole('heading', { name: 'eservices-lab' });

    const order = [
      '.subject',
      '.stamp',
      '.difference-line',
      '.metric-cards',
      '.thread-wrap',
    ].map((selector) => container.querySelector(selector));

    for (let index = 1; index < order.length; index += 1) {
      expect(order[index - 1].compareDocumentPosition(order[index])
        & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
    expect(screen.getByText('TLS / NETWORK · PORTS 8443, 8080')).toBeTruthy();
  });

  it('shows the stored subject status with only Refresh and Run scan actions', async () => {
    const { container } = await renderDrift();
    await screen.findByRole('heading', { name: 'eservices-lab' });

    expect(screen.getByText('active')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Run scan' })).toBeTruthy();
    expect(container.querySelectorAll('.subject-actions button')).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /Export Report/i })).toBeNull();
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

  it('shows the latest comparable counts as four metric cards', async () => {
    const counts = { NEW: 1, PERSISTENT: 3, FIXED: 2, RECURRING: 1 };
    renderDrift({
      client: {
        history: vi.fn().mockResolvedValue({
          target,
          scans: [{
            scan: {
              id: 2, target_id: 1, status: 'completed',
              started_at: '2026-11-14T09:30:00Z', completed_at: '2026-11-14T09:31:00Z',
              is_baseline: false, label: null, error: null,
            },
            comparable: true,
            evidence: [{
              id: 9, scan_id: 2, fingerprint: 'eservices-lab/TLS/a', category: 'TLS',
              title: 'Legacy TLS', severity: 'High', resource: '127.0.0.1:8443',
              details: {}, observed_at: '2026-11-14T09:30:00Z',
            }],
            drift: [],
            summary: { state: 'CHANGED', counts },
          }],
          fingerprints: {
            'eservices-lab/TLS/a': {
              title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: '127.0.0.1:8443',
            },
          },
        }),
        runScan: vi.fn(),
      },
    });

    await screen.findByRole('heading', { name: 'eservices-lab' });
    expect(screen.getByText('New findings').closest('li').textContent).toContain('1');
    expect(screen.getByText('Persistent findings').closest('li').textContent).toContain('3');
    expect(screen.getByText('Fixed findings').closest('li').textContent).toContain('2');
    expect(screen.getByText('Recurring findings').closest('li').textContent).toContain('1');
  });

  it('omits the metric cards when the latest summary carries no counts', async () => {
    renderDrift({
      client: {
        history: vi.fn().mockResolvedValue({
          target,
          scans: [{
            scan: {
              id: 2, target_id: 1, status: 'completed',
              started_at: '2026-11-14T09:30:00Z', completed_at: '2026-11-14T09:31:00Z',
              is_baseline: false, label: null, error: null,
            },
            comparable: true, evidence: [], drift: [],
            summary: { state: 'CHANGED' },
          }],
          fingerprints: {},
        }),
        runScan: vi.fn(),
      },
    });

    await screen.findByRole('heading', { name: 'eservices-lab' });
    expect(screen.queryByText('New findings')).toBeNull();
    expect(screen.queryByText('Persistent findings')).toBeNull();
  });

  it('selects the first stored thread and keeps the selection on reload', async () => {
    const props = renderDrift({
      client: {
        history: vi.fn()
          .mockResolvedValueOnce(twoThreadHistory())
          .mockResolvedValue(twoThreadHistory()),
        runScan: vi.fn(),
      },
    });
    const { container } = props;
    await screen.findByRole('heading', { name: 'eservices-lab' });
    await waitFor(() => expect(container.querySelector('.detail-rail h2').textContent)
      .toBe('First thread'));

    await userEvent.setup().click(
      screen.getByRole('rowheader', { name: /Second thread/ }),
    );
    expect(container.querySelector('.detail-rail h2').textContent).toBe('Second thread');

    await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(props.client.history).toHaveBeenCalledTimes(2));
    expect(container.querySelector('.detail-rail h2').textContent).toBe('Second thread');
  });

  it('keeps every stored thread reachable before the detail on narrow screens', async () => {
    const { container } = renderDrift({
      client: {
        history: vi.fn().mockResolvedValue(twoThreadHistory()),
        runScan: vi.fn(),
      },
    }, { narrow: true });

    await screen.findByRole('heading', { name: 'eservices-lab' });
    await waitFor(() => expect(container.querySelector('.thread-cards')).toBeTruthy());

    expect(screen.getByRole('button', { name: /First thread/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Second thread/ })).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    await waitFor(() => expect(container.querySelectorAll('.thread-card.is-expanded'))
      .toHaveLength(1));
    expect(container.querySelector('.thread-card.is-expanded h2').textContent)
      .toBe('First thread');
    expect(container.querySelector('.detail-rail h2').textContent).toBe('First thread');
    expect(container.querySelector('.thread-cards').compareDocumentPosition(
      container.querySelector('.detail-rail'),
    ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await userEvent.setup().click(screen.getByRole('button', { name: /Second thread/ }));
    await waitFor(() => expect(container.querySelector('.thread-card.is-expanded h2').textContent)
      .toBe('Second thread'));
    expect(container.querySelector('.detail-rail h2').textContent).toBe('Second thread');
  });
});
