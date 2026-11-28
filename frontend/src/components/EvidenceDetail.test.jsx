import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EvidenceDetail } from './EvidenceDetail';

const row = {
  fingerprint: 't/TLS/a',
  title: 'Legacy TLS',
  category: 'TLS',
  resource: 't:8443',
  severity: 'High',
  current: { classification: 'PERSISTENT', scanId: 2 },
  cells: [
    { kind: 'baseline', scanId: 1, classification: null },
    { kind: 'present', scanId: 2, classification: 'PERSISTENT' },
  ],
  detail: { cipher: 'RC4' },
  observedAt: '2026-11-12T09:30:00Z',
};

const scans = [
  {
    id: 1, startedAt: '2026-11-12T09:30:00Z',
    completedAt: '2026-11-12T09:31:00Z', summary: { state: 'BASELINE' },
    item: { evidence: [{ fingerprint: 't/TLS/a', details: { cipher: 'RC4' } }] },
  },
  {
    id: 2, startedAt: '2026-11-13T09:30:00Z',
    completedAt: '2026-11-13T09:31:00Z', label: 'DEMO-1',
    summary: { state: 'CHANGED' },
    item: { evidence: [{ fingerprint: 't/TLS/a', details: { cipher: 'RC4' } }] },
  },
];

function renderDetail(overrides = {}) {
  const props = {
    row,
    scans,
    client: {
      redactedEvidence: vi.fn().mockResolvedValue([
        { fingerprint: 't/TLS/a', title: 'Legacy TLS' },
      ]),
    },
    targetName: 'svc',
    copy: vi.fn().mockResolvedValue(undefined),
    download: vi.fn(),
    ...overrides,
  };
  const { container } = render(<EvidenceDetail {...props} />);
  return { ...props, container };
}

describe('EvidenceDetail', () => {
  it('marks raw local detail and copies only the redacted record', async () => {
    const props = renderDetail();
    expect(screen.getByText('LOCAL DETAIL · NOT REDACTED')).toBeTruthy();
    expect(props.container.querySelector('.detail-local').textContent).toContain('RC4');

    await userEvent.setup().click(
      screen.getByRole('button', { name: /Copy redacted record/ }),
    );

    expect(props.client.redactedEvidence).toHaveBeenCalledWith(2);
    expect(props.copy).toHaveBeenCalledWith(
      expect.stringContaining('"fingerprint": "t/TLS/a"'),
    );
    expect(props.copy.mock.calls[0][0]).not.toContain('RC4');
    expect(screen.getByRole('status').textContent).toContain('Redacted record copied.');
  });

  it('downloads the last observed scan as redacted CSV', async () => {
    const props = renderDetail();
    await userEvent.setup().click(
      screen.getByRole('button', { name: /Export scan #2/ }),
    );
    expect(props.download).toHaveBeenCalledWith(
      'driftguard-svc-scan-2-redacted.csv',
      expect.stringContaining('fingerprint'),
    );
  });

  it('reports a missing redacted record instead of exporting silently', async () => {
    const props = renderDetail({
      client: { redactedEvidence: vi.fn().mockResolvedValue([]) },
    });
    await userEvent.setup().click(
      screen.getByRole('button', { name: /Copy redacted record/ }),
    );
    expect(props.copy).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('No redacted record');
  });

  it('shows the stored badges and only the stored snapshot states', () => {
    const { container } = renderDetail();

    const header = container.querySelector('.detail-header');
    expect(header.textContent).toContain('PERSISTENT');
    expect(header.textContent).toContain('TLS');
    expect(header.textContent).toContain('t:8443');
    expect(screen.getByRole('heading', { name: 'Legacy TLS' })).toBeTruthy();

    expect(container.querySelectorAll('.snapshot-card')).toHaveLength(2);
    expect(screen.getAllByText('BASELINE')).toHaveLength(1);
    expect(screen.getAllByText('PERSISTENT')).toHaveLength(2);
    expect(screen.queryByText(/Verified Fix/)).toBeNull();
  });

  it('does not present a derived persistent label as stored evidence', () => {
    const { container } = renderDetail({
      row: {
        ...row,
        current: { classification: 'PERSISTENT', scanId: 2 },
        cells: [
          { kind: 'baseline', scanId: 1, classification: null },
          { kind: 'present', scanId: 2, classification: null },
        ],
      },
    });

    const header = container.querySelector('.detail-header');
    expect(header.textContent).not.toContain('PERSISTENT');
    expect(header.textContent).toContain('NO STORED CLASSIFICATION');
  });

  it('keeps provenance collapsed until opened and shows only stored fields', async () => {
    const { container } = renderDetail();
    const details = container.querySelector('details.accordion-trigger');
    expect(details.open).toBe(false);
    expect(within(details).getByText(/Evidence provenance/)).toBeTruthy();

    await userEvent.setup().click(within(details).getByText(/Evidence provenance/));

    expect(details.open).toBe(true);
    expect(within(details).getByText('#2')).toBeTruthy();
    expect(within(details).getByText('DEMO-1')).toBeTruthy();
    expect(within(details).getByText('2026-11-12T09:30:00Z')).toBeTruthy();
  });
});
