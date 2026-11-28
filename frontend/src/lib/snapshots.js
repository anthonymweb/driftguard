import { formatDateTime } from './format';
import { storedCurrentState } from './stored-state';

const OBSERVED_KINDS = new Set(['baseline', 'present', 'new', 'recurring']);
const STORED_STATES = new Set([
  'BASELINE', 'NEW', 'PERSISTENT', 'FIXED', 'RECURRING', 'NO DRIFT',
]);

function stateFor(cell, scan, row) {
  if (cell.classification) return cell.classification;
  if (cell.kind === 'fixed') return 'FIXED';
  if (scan.summary?.state === 'BASELINE') return 'BASELINE';
  if (scan.summary?.state === 'NO DRIFT') return scan.summary.state;
  if (cell.scanId === row.current?.scanId) {
    const stored = storedCurrentState(row);
    return stored.stored ? stored.classification : null;
  }
  return null;
}

export function storedSnapshots(row, scans = []) {
  if (!row) return [];
  const cells = row.cells ?? [];
  const observed = cells.filter((cell) => OBSERVED_KINDS.has(cell.kind));
  const fixed = cells.find((cell) => cell.kind === 'fixed');
  const candidates = [];
  if (observed[0]) candidates.push(observed[0]);
  if (fixed) candidates.push(fixed);
  if (observed.at(-1) && observed.at(-1) !== observed[0]) {
    candidates.push(observed.at(-1));
  }

  const seen = new Set();
  const snapshots = [];
  for (const cell of candidates) {
    if (seen.has(cell.scanId)) continue;
    seen.add(cell.scanId);
    const scan = scans.find((item) => item.id === cell.scanId);
    if (!scan) continue;
    const state = stateFor(cell, scan, row);
    if (!STORED_STATES.has(state)) continue;
    const evidence = (scan.item?.evidence ?? [])
      .find((item) => item.fingerprint === row.fingerprint);
    snapshots.push({
      scanId: cell.scanId,
      state,
      time: formatDateTime(scan.completedAt ?? scan.startedAt),
      detail: evidence?.details ?? null,
    });
  }
  return snapshots.sort((a, b) => a.scanId - b.scanId);
}
