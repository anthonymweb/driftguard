import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TargetIndex } from './TargetIndex';

const targets = [
  {
    id: 1, name: 'eservices-lab', address: 'https://127.0.0.1:8443',
    authorization_status: 'authorized',
    last_scan: { id: 4, status: 'completed', started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z' },
  },
  {
    id: 2, name: 'civic', address: 'https://127.0.0.1:8445',
    authorization_status: 'pending', last_scan: null,
  },
];

describe('TargetIndex', () => {
  it('marks the selected subject and reports the last scan attempt', () => {
    render(<TargetIndex targets={targets} selectedId={1} onSelect={vi.fn()} />);
    const selected = screen.getByRole('link', { name: /eservices-lab/ });
    expect(selected.getAttribute('aria-current')).toBe('page');
    expect(screen.getByText(/Last scan #4 · completed · 12 Nov 2026/)).toBeTruthy();
    expect(screen.getByText('No scans')).toBeTruthy();
  });

  it('selects a target without a page reload', async () => {
    const onSelect = vi.fn();
    render(<TargetIndex targets={targets} selectedId={1} onSelect={onSelect} />);
    await userEvent.setup().click(screen.getByRole('link', { name: /civic/ }));
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
