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
        { scanId: 1, kind: 'baseline', classification: null, lineLeft: false, lineRight: false },
        { scanId: 2, kind: 'incomplete', classification: null, lineLeft: false, lineRight: false },
        { scanId: 3, kind: 'fixed', classification: 'FIXED', lineLeft: true, lineRight: false },
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
    expect(screen.getAllByText('FIXED').length).toBeGreaterThan(0);
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
            { scanId: 1, kind: 'baseline', classification: null },
            { scanId: 2, kind: 'pending', classification: null },
            { scanId: 3, kind: 'new', classification: 'NEW' },
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

  it('does not present an observed finding without stored drift as a classification', () => {
    const unclassified = {
      ...model,
      groups: [{
        key: 'TLS',
        rows: [{
          fingerprint: 't/TLS/c', title: 'Unclassified observation', resource: 't:8443',
          category: 'TLS', severity: 'High',
          cells: [
            { scanId: 1, kind: 'baseline', classification: null, lineLeft: false, lineRight: false },
            { scanId: 3, kind: 'present', classification: null, lineLeft: true, lineRight: true },
          ],
          current: { classification: 'PERSISTENT', scanId: 3 },
        }],
      }],
    };
    render(<ThreadGrid model={unclassified} selected={null} onSelect={vi.fn()} />);

    expect(screen.queryByText('PERSISTENT')).toBeNull();
    expect(screen.getByText('NO STORED CLASSIFICATION')).toBeTruthy();
  });

  it('selects a thread on activation', async () => {
    const onSelect = vi.fn();
    render(<ThreadGrid model={model} selected={null} onSelect={onSelect} />);
    await userEvent.setup().click(screen.getByRole('rowheader', { name: /Legacy TLS/ }));
    expect(onSelect).toHaveBeenCalledWith('t/TLS/a');
  });
});
