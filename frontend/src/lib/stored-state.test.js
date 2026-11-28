import { describe, expect, it } from 'vitest';

import { storedCurrentState } from './stored-state';

describe('storedCurrentState', () => {
  it('returns a frozen classification stored on the current scan', () => {
    expect(storedCurrentState({
      cells: [
        { scanId: 1, kind: 'baseline', classification: null },
        { scanId: 2, kind: 'new', classification: 'NEW' },
      ],
      current: { classification: 'NEW', scanId: 2 },
    })).toEqual({ classification: 'NEW', scanId: 2, stored: true });
  });

  it('accepts a baseline stored in the scan summary', () => {
    expect(storedCurrentState({
      cells: [{ scanId: 1, kind: 'baseline', classification: null }],
      current: { classification: 'BASELINE', scanId: 1 },
    })).toEqual({ classification: 'BASELINE', scanId: 1, stored: true });
  });

  it('does not accept a derived label for a baseline cell', () => {
    expect(storedCurrentState({
      cells: [{ scanId: 1, kind: 'baseline', classification: null }],
      current: { classification: 'PERSISTENT', scanId: 1 },
    })).toEqual({ classification: null, scanId: 1, stored: false });
  });

  it('does not present a derived persistent label as a stored classification', () => {
    expect(storedCurrentState({
      cells: [
        { scanId: 1, kind: 'baseline', classification: null },
        { scanId: 2, kind: 'present', classification: null },
      ],
      current: { classification: 'PERSISTENT', scanId: 2 },
    })).toEqual({ classification: null, scanId: 2, stored: false });
  });

  it('rejects a non-frozen current classification', () => {
    expect(storedCurrentState({
      cells: [{ scanId: 3, kind: 'present', classification: 'REGRESSED' }],
      current: { classification: 'REGRESSED', scanId: 3 },
    })).toEqual({ classification: null, scanId: 3, stored: false });
  });
});
