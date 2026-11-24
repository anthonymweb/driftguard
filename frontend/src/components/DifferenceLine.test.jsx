import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DifferenceLine } from './DifferenceLine';

describe('DifferenceLine', () => {
  it('renders counts and the compared scan id', () => {
    render(<DifferenceLine model={{
      latestComparable: {
        id: 13,
        summary: { state: 'CHANGED', counts: { NEW: 1, PERSISTENT: 2, FIXED: 1, RECURRING: 0 } },
      },
      previousComparable: { id: 12 },
    }} />);
    expect(screen.getByText('1 new · 2 persistent · 1 fixed since scan #12.')).toBeTruthy();
  });
});
