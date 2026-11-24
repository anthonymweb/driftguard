import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EvidenceDetail } from './EvidenceDetail';

const row = {
  fingerprint: 't/TLS/a',
  title: 'Legacy TLS',
  resource: 't:8443',
  severity: 'High',
  current: { classification: 'PERSISTENT', scanId: 2 },
  cells: [{ kind: 'baseline' }, { kind: 'present' }],
  detail: { cipher: 'RC4' },
  observedAt: '2026-11-12T09:30:00Z',
};

const scans = [
  {
    id: 1, startedAt: '2026-11-12T09:30:00Z',
    completedAt: '2026-11-12T09:31:00Z', summary: { state: 'BASELINE' },
  },
  {
    id: 2, startedAt: '2026-11-13T09:30:00Z',
    completedAt: '2026-11-13T09:31:00Z', summary: { state: 'CHANGED' },
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
  render(<EvidenceDetail {...props} />);
  return props;
}

describe('EvidenceDetail', () => {
  it('marks raw local detail and copies only the redacted record', async () => {
    const props = renderDetail();
    expect(screen.getByText('LOCAL DETAIL · NOT REDACTED')).toBeTruthy();
    expect(screen.getByText(/RC4/)).toBeTruthy();

    await userEvent.setup().click(
      screen.getByRole('button', { name: /Copy redacted record/ }),
    );

    expect(props.client.redactedEvidence).toHaveBeenCalledWith(2);
    expect(props.copy).toHaveBeenCalledWith(
      expect.stringContaining('"fingerprint": "t/TLS/a"'),
    );
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
});
