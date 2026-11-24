import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ThreadGrid } from './ThreadGrid';

const model = {
  scans: [
    {
      id: 1, kind: 'baseline', status: 'completed',
      startedAt: '2026-11-12T09:30:00Z', completedAt: '2026-11-12T09:31:00Z',
      summary: { state: 'BASELINE' },
    },
    {
      id: 2, kind: 'incomplete', status: 'failed',
      startedAt: '2026-11-13T09:30:00Z', completedAt: null,
      summary: { state: 'INCOMPLETE' },
    },
    {
      id: 3, kind: 'compared', status: 'completed',
      startedAt: '2026-11-14T09:30:00Z', completedAt: '2026-11-14T09:31:00Z',
      summary: { state: 'CHANGED' },
    },
  ],
  groups: [{
    key: 'TLS',
    rows: [{
      fingerprint: 't/TLS/a', title: 'Legacy TLS', resource: 't:8443', severity: 'High',
      cells: [
        { kind: 'baseline', lineLeft: false, lineRight: false },
        { kind: 'incomplete', lineLeft: false, lineRight: false },
        { kind: 'fixed', lineLeft: true, lineRight: false },
      ],
      current: { classification: 'FIXED', scanId: 3 },
    }],
  }],
};

describe('ThreadGrid', () => {
  it('renders table semantics, the not-compared column, and the current token', () => {
    render(<ThreadGrid model={model} selected={null} onSelect={vi.fn()} />);
    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /#2/ })).toBeTruthy();
    expect(screen.getByText('NOT COMPARED')).toBeTruthy();
    expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
    expect(screen.getByText('FIXED')).toBeTruthy();
  });

  it('selects a thread on activation', async () => {
    const onSelect = vi.fn();
    render(<ThreadGrid model={model} selected={null} onSelect={onSelect} />);
    await userEvent.setup().click(screen.getByRole('rowheader', { name: /Legacy TLS/ }));
    expect(onSelect).toHaveBeenCalledWith('t/TLS/a');
  });
});
