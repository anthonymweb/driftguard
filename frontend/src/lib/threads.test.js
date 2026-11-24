import { describe, expect, it } from 'vitest';

import { buildThreadModel } from './threads';

const META = {
  't/TLS/a': { title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: 't:8443' },
  't/Network/b': { title: 'Plain HTTP', category: 'Network', severity: 'High', resource: 't:8080' },
  't/Network/c': { title: 'Open port', category: 'Network', severity: 'Medium', resource: 't:9000' },
  't/API/d': { title: 'Debug endpoint', category: 'API', severity: 'Medium', resource: '/debug' },
};

function history(scans, fingerprints = META) {
  return {
    target: { id: 1, name: 't' },
    scans: scans.map(({
      id, status = 'completed', evidence = [], drift = {},
      state = 'CHANGED', counts = {},
    }) => ({
      scan: {
        id,
        target_id: 1,
        status,
        started_at: '2026-11-12T09:30:00Z',
        completed_at: status === 'completed' ? '2026-11-12T09:31:00Z' : null,
        is_baseline: state === 'BASELINE',
        label: null,
        error: null,
      },
      comparable: status === 'completed',
      evidence: evidence.map((fingerprint, index) => ({
        id: id * 10 + index, scan_id: id, fingerprint,
      })),
      drift: Object.entries(drift).map(([evidence_fingerprint, classification], index) => ({
        id: index, scan_id: id, evidence_fingerprint, classification,
      })),
      summary: {
        state,
        counts: { NEW: 0, PERSISTENT: 0, FIXED: 0, RECURRING: 0, ...counts },
      },
    })),
    fingerprints,
  };
}

function row(model, fingerprint) {
  return model.groups.flatMap((group) => group.rows)
    .find((candidate) => candidate.fingerprint === fingerprint);
}

describe('thread model', () => {
  it('orders scans oldest first and classifies presence, new, fixed, and never observed', () => {
    const model = buildThreadModel(history([
      {
        id: 2, evidence: ['t/TLS/a', 't/Network/c'],
        drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'FIXED', 't/Network/c': 'NEW' },
        counts: { PERSISTENT: 1, FIXED: 1, NEW: 1 },
      },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a', 't/Network/b'] },
    ]));

    expect(model.scans.map((scan) => scan.id)).toEqual([1, 2]);
    expect(model.latestComparable.id).toBe(2);
    expect(model.previousComparable.id).toBe(1);

    expect(row(model, 't/TLS/a').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'present']);
    expect(row(model, 't/TLS/a').current.classification).toBe('PERSISTENT');

    expect(row(model, 't/Network/b').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'fixed']);
    expect(row(model, 't/Network/b').current.classification).toBe('FIXED');

    expect(row(model, 't/Network/c').cells.map((cell) => cell.kind))
      .toEqual(['never', 'new']);
    expect(row(model, 't/Network/c').current.classification).toBe('NEW');
  });

  it('keeps FIXED current through later absences and clears it only on a recurrence', () => {
    const fixedThenAbsent = buildThreadModel(history([
      { id: 3, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT' } },
      { id: 2, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'FIXED' } },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a', 't/Network/b'] },
    ]));
    expect(row(fixedThenAbsent, 't/Network/b').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'fixed', 'absent']);
    expect(row(fixedThenAbsent, 't/Network/b').current.classification).toBe('FIXED');

    const recurring = buildThreadModel(history([
      {
        id: 3, evidence: ['t/TLS/a', 't/Network/b'],
        drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'RECURRING' },
      },
      { id: 2, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'FIXED' } },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a', 't/Network/b'] },
    ]));
    expect(row(recurring, 't/Network/b').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'fixed', 'recurring']);
    expect(row(recurring, 't/Network/b').current.classification).toBe('RECURRING');
  });

  it('does not advance the thread through an incomplete scan', () => {
    const model = buildThreadModel(history([
      { id: 5 },
      { id: 4, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT' } },
      {
        id: 3, status: 'completed_with_errors',
        evidence: ['t/TLS/a', 't/API/d'], drift: { 't/TLS/a': 'FIXED' },
      },
      { id: 2, state: 'BASELINE', evidence: ['t/TLS/a'] },
    ]));

    expect(model.scans.map((scan) => scan.kind))
      .toEqual(['baseline', 'incomplete', 'compared', 'compared']);
    expect(row(model, 't/TLS/a').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'incomplete', 'present', 'absent']);
    expect(row(model, 't/API/d')).toBeUndefined();
    expect(model.groups.flatMap((group) => group.rows)).toHaveLength(1);
  });

  it('keeps pending scans as pending columns without comparing them', () => {
    const model = buildThreadModel(history([
      { id: 2, status: 'running' },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a'] },
    ]));
    expect(model.pendingScans.map((scan) => scan.id)).toEqual([2]);
    expect(model.scans.map((scan) => scan.kind)).toEqual(['baseline', 'pending']);
    expect(row(model, 't/TLS/a').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'pending']);
    expect(row(model, 't/TLS/a').current.classification).toBe('BASELINE');
  });

  it('reports no comparable history when only incomplete scans exist', () => {
    const model = buildThreadModel(history([
      { id: 1, status: 'failed', evidence: ['t/TLS/a'] },
    ]));
    expect(model.hasComparable).toBe(false);
    expect(model.latestComparable).toBeNull();
    expect(model.groups).toEqual([]);
  });

  it('groups rows in TLS, NETWORK, API order and sorts by title', () => {
    const model = buildThreadModel(history([
      {
        id: 1, state: 'BASELINE',
        evidence: ['t/API/d', 't/Network/c', 't/TLS/a'],
      },
    ]));
    expect(model.groups.map((group) => group.key)).toEqual(['TLS', 'NETWORK', 'API']);
    expect(model.groups[1].rows.map((entry) => entry.title)).toEqual(['Open port']);
  });
});
