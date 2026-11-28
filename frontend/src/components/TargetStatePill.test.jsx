import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TargetStatePill } from './TargetStatePill';

describe('TargetStatePill', () => {
  it('shows a stored frozen state or an honest no-state mark', () => {
    const { rerender } = render(<TargetStatePill state={{ classification: 'FIXED', scanId: 3 }} />);
    expect(screen.getByText('FIXED')).toBeTruthy();

    rerender(<TargetStatePill state={null} />);
    expect(screen.getByText('—')).toBeTruthy();
    expect(screen.getByLabelText(/No stored drift state/)).toBeTruthy();
  });

  it.each([
    'BASELINE', 'NEW', 'PERSISTENT', 'FIXED', 'RECURRING', 'NO DRIFT',
  ])('renders the stored %s label verbatim', (classification) => {
    render(<TargetStatePill state={{ classification, scanId: 4 }} />);
    expect(screen.getByText(classification)).toBeTruthy();
    expect(screen.queryByText('—')).toBeNull();
  });

  it('hides the no-state explanation from sighted users', () => {
    const { container } = render(<TargetStatePill state={null} />);
    const explanation = screen.getByText('No stored drift state');
    expect(explanation.closest('.visually-hidden')).toBeTruthy();
    expect(container.querySelector('.status-pill').getAttribute('aria-label'))
      .toMatch(/No stored drift state/);
  });

  it('never renders an invented classification', () => {
    render(<TargetStatePill state={{ classification: 'REGRESSED', scanId: 5 }} />);
    expect(screen.queryByText('REGRESSED')).toBeNull();
    expect(screen.getByLabelText(/No stored drift state/)).toBeTruthy();
  });
});
