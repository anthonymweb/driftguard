import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ThreadCards } from './ThreadCards';

const model = {
  scans: [
    { id: 1, kind: 'baseline', status: 'completed', summary: { state: 'BASELINE' } },
    { id: 3, kind: 'compared', status: 'completed', summary: { state: 'CHANGED' } },
  ],
  groups: [{
    key: 'TLS',
    rows: [{
      fingerprint: 't/TLS/a', title: 'Legacy TLS', resource: 't:8443', severity: 'High',
      cells: [{ kind: 'baseline' }, { kind: 'fixed' }],
      current: { classification: 'FIXED', scanId: 3 },
    }],
  }],
};

describe('ThreadCards', () => {
  it('renders a card with the token and a hidden timeline', async () => {
    const onSelect = vi.fn();
    render(<ThreadCards model={model} selected={null} onSelect={onSelect} />);

    expect(screen.getByRole('heading', { name: 'Legacy TLS' })).toBeTruthy();
    expect(screen.getByText('FIXED')).toBeTruthy();
    expect(screen.getAllByText(/baseline observation/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/— fixed/).length).toBeGreaterThan(0);

    await userEvent.setup().click(screen.getByRole('button', { name: /Legacy TLS/ }));
    expect(onSelect).toHaveBeenCalledWith('t/TLS/a');
  });

  it('keeps every stored thread reachable and expands the selected one', () => {
    const twoThreads = {
      scans: [{ id: 1 }, { id: 2 }],
      groups: [{ key: 'TLS', rows: [
        { fingerprint: 'a', title: 'First thread', resource: 'r1', severity: 'High',
          cells: [{ kind: 'baseline' }, { kind: 'present' }],
          current: { classification: 'PERSISTENT', scanId: 2 } },
        { fingerprint: 'b', title: 'Second thread', resource: 'r2', severity: 'Low',
          cells: [{ kind: 'baseline' }, { kind: 'fixed' }],
          current: { classification: 'FIXED', scanId: 2 } },
      ] }],
    };

    render(<ThreadCards model={twoThreads} selected="a" onSelect={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'First thread' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Second thread' })).toBeTruthy();
    expect(screen.getByRole('button', { name: /First thread/ }).closest('li')
      .className).toContain('is-expanded');
    expect(screen.getByRole('button', { name: /Second thread/ }).closest('li')
      .className).not.toContain('is-expanded');
  });

  it('renders only stored snapshots inside the expanded card', () => {
    const stored = {
      scans: [
        { id: 1, completedAt: '2026-11-12T09:31:00Z', summary: { state: 'BASELINE' } },
        { id: 3, completedAt: '2026-11-14T09:31:00Z', summary: { state: 'CHANGED' } },
      ],
      groups: [{ key: 'TLS', rows: [{
        fingerprint: 'a', title: 'Stored thread', resource: 'r1', severity: 'High',
        cells: [
          { kind: 'baseline', classification: null, scanId: 1 },
          { kind: 'fixed', classification: 'FIXED', scanId: 3 },
        ],
        current: { classification: 'FIXED', scanId: 3 },
        detail: { cipher: 'RC4' },
      }] }],
    };
    const { container } = render(
      <ThreadCards model={stored} selected="a" onSelect={vi.fn()} />,
    );

    const expanded = container.querySelector('.thread-card.is-expanded');
    expect(expanded.querySelectorAll('.snapshot-card')).toHaveLength(2);
    expect(expanded.textContent).toContain('BASELINE');
    expect(expanded.textContent).toContain('FIXED');
    expect(expanded.textContent).toContain('RC4');
    expect(expanded.textContent).not.toMatch(/Verified|Regress|Skipped/);
  });
});
