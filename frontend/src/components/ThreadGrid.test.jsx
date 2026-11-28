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
      fingerprint: 't/TLS/a', title: 'Legacy TLS', resource: 't:8443',
      category: 'TLS', severity: 'High',
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
    const { container } = render(
      <ThreadGrid model={model} selected={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /Category/ })).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /Severity/ })).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /#2/ })).toBeTruthy();
    expect(screen.getByText('NOT COMPARED')).toBeTruthy();
    expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
    expect(screen.getByText('FIXED')).toBeTruthy();
    expect(screen.getByText('baseline observation')).toBeTruthy();
    expect(container.querySelector('.thread-category .mono-chip').textContent).toBe('TLS');
    expect(container.querySelector('.thread-severity').textContent).toBe('High');
  });

  it('renders a visible frozen token only for stored cell classifications', () => {
    const classified = {
      scans: [
        {
          id: 1, kind: 'baseline', status: 'completed',
          startedAt: '2026-11-12T09:30:00Z', completedAt: '2026-11-12T09:31:00Z',
          summary: { state: 'BASELINE' },
        },
        {
          id: 2, kind: 'pending', status: 'queued',
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
          fingerprint: 't/TLS/b', title: 'Stored drift', resource: 't:8443',
          category: 'TLS', severity: 'High',
          cells: [
            { kind: 'baseline', classification: null },
            { kind: 'pending', classification: null },
            { kind: 'new', classification: 'NEW' },
          ],
          current: { classification: 'NEW', scanId: 3 },
        }],
      }],
    };
    const { container } = render(
      <ThreadGrid model={classified} selected={null} onSelect={vi.fn()} />,
    );
    const cells = container.querySelectorAll('.thread-cell');
    const pills = [...cells].map((cell) => cell.querySelector('.state-pill'));

    expect(pills.every(Boolean)).toBe(true);
    expect(pills[0].querySelector('.state-token')).toBeNull();
    expect(pills[1].querySelector('.state-token')).toBeNull();
    expect(pills[2].querySelector('.state-token').textContent).toBe('NEW');
    expect(cells[1].textContent).toContain('scan pending');
    expect(cells[0].textContent).toContain('baseline observation');
  });

  it('selects a thread on activation', async () => {
    const onSelect = vi.fn();
    render(<ThreadGrid model={model} selected={null} onSelect={onSelect} />);
    await userEvent.setup().click(screen.getByRole('rowheader', { name: /Legacy TLS/ }));
    expect(onSelect).toHaveBeenCalledWith('t/TLS/a');
  });
});
