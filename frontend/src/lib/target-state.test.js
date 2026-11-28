import { describe, expect, it } from 'vitest';

import { latestStoredState } from './target-state';

describe('latestStoredState', () => {
  it('reads the newest stored drift classification', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 1 }, drift: [], summary: { state: 'BASELINE' } },
      { comparable: true, scan: { id: 2 },
        drift: [{ classification: 'RECURRING', recorded_at: '2026-11-24T10:00:00Z' }],
        summary: { state: 'CHANGED' } },
    ] })).toEqual({ classification: 'RECURRING', scanId: 2 });
  });

  it('reads a stored clean state without inventing a finding', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 1 }, drift: [], summary: { state: 'NO DRIFT' } },
    ] })).toEqual({ classification: 'NO DRIFT', scanId: 1 });
  });

  it('returns null when no comparable scan exists', () => {
    expect(latestStoredState({ scans: [
      { comparable: false, scan: { id: 1, status: 'queued' }, drift: [], summary: {} },
    ] })).toBeNull();
  });

  it('takes the newest comparable scan even when the response is out of order', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 9 }, drift: [], summary: { state: 'NO DRIFT' } },
      { comparable: false, scan: { id: 10, status: 'queued' }, drift: [], summary: {} },
      { comparable: true, scan: { id: 8 },
        drift: [{ classification: 'NEW', recorded_at: '2026-11-25T10:00:00Z' }],
        summary: { state: 'CHANGED' } },
    ] })).toEqual({ classification: 'NO DRIFT', scanId: 9 });
  });

  it('uses the drift event with the greatest recorded_at', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 4 }, drift: [
        { classification: 'NEW', recorded_at: '2026-11-24T10:00:00Z' },
        { classification: 'FIXED', recorded_at: '2026-11-25T10:00:00Z' },
        { classification: 'PERSISTENT', recorded_at: '2026-11-23T10:00:00Z' },
      ], summary: { state: 'CHANGED' } },
    ] })).toEqual({ classification: 'FIXED', scanId: 4 });
  });

  it('falls back to stored array order when recorded_at is absent', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 5 }, drift: [
        { classification: 'NEW' },
        { classification: 'PERSISTENT' },
      ], summary: { state: 'CHANGED' } },
    ] })).toEqual({ classification: 'PERSISTENT', scanId: 5 });
  });

  it('does not turn a non-frozen summary state into a classification', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 6 }, drift: [], summary: { state: 'CHANGED' } },
    ] })).toBeNull();
  });

  it('ignores non-frozen drift classifications', () => {
    expect(latestStoredState({ scans: [
      { comparable: true, scan: { id: 7 }, drift: [
        { classification: 'NEW', recorded_at: '2026-11-20T10:00:00Z' },
        { classification: 'REGRESSED', recorded_at: '2026-11-21T10:00:00Z' },
      ], summary: { state: 'CHANGED' } },
    ] })).toEqual({ classification: 'NEW', scanId: 7 });
  });

  it('returns null for an empty or missing history', () => {
    expect(latestStoredState(null)).toBeNull();
    expect(latestStoredState({})).toBeNull();
    expect(latestStoredState({ scans: [] })).toBeNull();
  });
});
