import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EvidenceSnapshots } from './EvidenceSnapshots';

describe('EvidenceSnapshots', () => {
  it('renders stored snapshot cards without explanatory invention', () => {
    render(<EvidenceSnapshots snapshots={[
      { scanId: 1, state: 'BASELINE', time: '12 Nov 2026 · 09:30 UTC', detail: {} },
      { scanId: 3, state: 'FIXED', time: '14 Nov 2026 · 09:30 UTC', detail: {} },
    ]} />);

    expect(screen.getAllByRole('article')).toHaveLength(2);
    expect(screen.getByText('BASELINE')).toBeTruthy();
    expect(screen.getByText('FIXED')).toBeTruthy();
    expect(screen.queryByText(/Verified Fix/)).toBeNull();
  });

  it('shows the stored scan id and detail on each card', () => {
    const { container } = render(<EvidenceSnapshots snapshots={[
      {
        scanId: 4, state: 'RECURRING', time: '24 Nov 2026 · 10:00 UTC',
        detail: { cipher: 'RC4' },
      },
    ]} />);

    const card = container.querySelector('.snapshot-card.state-recurring');
    expect(card.textContent).toContain('#4');
    expect(card.textContent).toContain('24 Nov 2026 · 10:00 UTC');
    expect(card.querySelector('pre').textContent).toContain('RC4');
  });

  it('slugs multi-word stored states for the state class', () => {
    const { container } = render(<EvidenceSnapshots snapshots={[
      { scanId: 5, state: 'NO DRIFT', time: '24 Nov 2026 · 10:00 UTC', detail: {} },
    ]} />);

    expect(container.querySelector('.snapshot-card.state-no-drift')).toBeTruthy();
  });

  it('renders nothing when no snapshot is stored', () => {
    const { container } = render(<EvidenceSnapshots snapshots={[]} />);
    expect(container.querySelector('.snapshot-card')).toBeNull();
  });
});
