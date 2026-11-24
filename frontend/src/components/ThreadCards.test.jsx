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
});
