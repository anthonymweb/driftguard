import { describe, expect, it } from 'vitest';

import { describeDifference } from './difference';

const previous = { id: 12 };

describe('difference line', () => {
  it('says there are no completed observations yet', () => {
    expect(describeDifference({ latestComparable: null })).toEqual({
      text: 'No completed observations yet.', state: 'EMPTY',
    });
  });

  it('dates the baseline instead of inventing a count', () => {
    expect(describeDifference({
      latestComparable: {
        id: 13, kind: 'baseline', startedAt: '2026-11-12T09:30:00Z',
        completedAt: '2026-11-12T09:31:00Z',
        summary: { state: 'BASELINE', counts: {} },
      },
      previousComparable: null,
    })).toEqual({ text: 'Baseline recorded 12 Nov 2026.', state: 'BASELINE' });
  });

  it('names the scan that was compared against', () => {
    expect(describeDifference({
      latestComparable: {
        id: 13, summary: { state: 'NO DRIFT', counts: {} },
      },
      previousComparable: previous,
    })).toEqual({ text: 'No change since scan #12.', state: 'NO DRIFT' });
  });

  it('prints exact counts in scan-level order', () => {
    expect(describeDifference({
      latestComparable: {
        id: 13,
        summary: {
          state: 'CHANGED',
          counts: { NEW: 1, PERSISTENT: 2, FIXED: 1, RECURRING: 0 },
        },
      },
      previousComparable: previous,
    })).toEqual({
      text: '1 new · 2 persistent · 1 fixed since scan #12.', state: 'CHANGED',
    });
  });

  it('falls back honestly when a changed scan has no counts', () => {
    expect(describeDifference({
      latestComparable: { id: 13, summary: { state: 'CHANGED', counts: {} } },
      previousComparable: previous,
    })).toEqual({ text: 'Changed since scan #12.', state: 'CHANGED' });
  });
});
