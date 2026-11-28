import { describe, expect, it } from 'vitest';

import { storedSnapshots } from './snapshots';

describe('storedSnapshots', () => {
  it('returns only states present in the stored thread', () => {
    const row = {
      cells: [
        { kind: 'baseline', classification: null, scanId: 1 },
        { kind: 'present', classification: null, scanId: 2 },
        { kind: 'fixed', classification: 'FIXED', scanId: 3 },
        { kind: 'recurring', classification: 'RECURRING', scanId: 4 },
      ],
      current: { classification: 'RECURRING', scanId: 4 },
      observedAt: '2026-11-24T10:00:00Z',
      detail: { cipher: 'RC4' },
    };
    const scans = [1, 2, 3, 4].map((id) => ({
      id,
      completedAt: `2026-11-2${id - 1}T10:00:00Z`,
      summary: { state: id === 1 ? 'BASELINE' : 'CHANGED' },
    }));

    const snapshots = storedSnapshots(row, scans);

    expect(snapshots.map((snapshot) => snapshot.state)).toEqual([
      'BASELINE', 'FIXED', 'RECURRING',
    ]);
    expect(snapshots.every((snapshot) => ['BASELINE', 'FIXED', 'RECURRING']
      .includes(snapshot.state))).toBe(true);
  });

  it('orders stored states by scan id when a fix precedes the last observation', () => {
    const row = {
      cells: [
        { kind: 'baseline', classification: null, scanId: 1 },
        { kind: 'present', classification: 'PERSISTENT', scanId: 2 },
        { kind: 'fixed', classification: 'FIXED', scanId: 3 },
      ],
      current: { classification: 'FIXED', scanId: 3 },
      detail: { cipher: 'RC4' },
    };
    const scans = [
      { id: 1, completedAt: '2026-11-12T09:31:00Z', summary: { state: 'BASELINE' } },
      { id: 2, completedAt: '2026-11-13T09:31:00Z', summary: { state: 'CHANGED' } },
      { id: 3, completedAt: '2026-11-14T09:31:00Z', summary: { state: 'CHANGED' } },
    ];

    const snapshots = storedSnapshots(row, scans);

    expect(snapshots.map((snapshot) => snapshot.scanId)).toEqual([1, 2, 3]);
    expect(snapshots.map((snapshot) => snapshot.state)).toEqual([
      'BASELINE', 'PERSISTENT', 'FIXED',
    ]);
  });

  it('does not project the latest classification onto an older observation', () => {
    const row = {
      cells: [
        { kind: 'present', classification: null, scanId: 2 },
        { kind: 'fixed', classification: 'FIXED', scanId: 3 },
        { kind: 'recurring', classification: null, scanId: 4 },
      ],
      current: { classification: 'RECURRING', scanId: 4 },
      detail: {},
    };
    const scans = [2, 3, 4].map((id) => ({
      id, completedAt: '2026-11-24T10:00:00Z', summary: { state: 'CHANGED' },
    }));

    const snapshots = storedSnapshots(row, scans);

    expect(snapshots.map((snapshot) => snapshot.scanId)).toEqual([3, 4]);
    expect(snapshots.map((snapshot) => snapshot.state)).toEqual(['FIXED', 'RECURRING']);
  });

  it('does not invent a fixed snapshot when none is stored', () => {
    const snapshots = storedSnapshots(
      { cells: [{ kind: 'baseline', classification: null, scanId: 1 }],
        current: { classification: 'BASELINE', scanId: 1 },
        observedAt: null, detail: null },
      [{ id: 1, completedAt: null, summary: { state: 'BASELINE' } }],
    );

    expect(snapshots.some((snapshot) => snapshot.state === 'FIXED')).toBe(false);
  });

  it('skips cells that were not observed or fixed', () => {
    const row = {
      cells: [
        { kind: 'pending', classification: null, scanId: 1 },
        { kind: 'incomplete', classification: null, scanId: 2 },
        { kind: 'absent', classification: null, scanId: 3 },
        { kind: 'never', classification: null, scanId: 4 },
        { kind: 'present', classification: 'NEW', scanId: 5 },
      ],
      current: { classification: 'NEW', scanId: 5 },
      detail: {},
    };
    const scans = [1, 2, 3, 4, 5].map((id) => ({
      id, completedAt: '2026-11-24T10:00:00Z', summary: { state: 'CHANGED' },
    }));

    expect(storedSnapshots(row, scans)).toEqual([{
      scanId: 5, state: 'NEW', time: '24 Nov 2026 · 10:00 UTC', detail: {},
    }]);
  });

  it('deduplicates the first and last observation by scan id', () => {
    const row = {
      cells: [{ kind: 'baseline', classification: 'BASELINE', scanId: 1 }],
      current: { classification: 'BASELINE', scanId: 1 },
      detail: { cipher: 'RC4' },
    };
    const scans = [{
      id: 1, startedAt: '2026-11-12T09:30:00Z',
      completedAt: '2026-11-12T09:31:00Z', summary: { state: 'BASELINE' },
    }];

    expect(storedSnapshots(row, scans)).toHaveLength(1);
    expect(storedSnapshots(row, scans)[0].time).toBe('12 Nov 2026 · 09:31 UTC');
  });
});
