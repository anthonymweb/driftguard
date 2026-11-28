import { FROZEN_CLASSIFICATIONS } from './target-state';

export const NO_STORED_CLASSIFICATION = 'NO STORED CLASSIFICATION';

/**
 * Display lookup for the current column and detail badge. The thread model may
 * carry a UI fallback; this helper accepts only a classification stored for the
 * current scan or a BASELINE stored in that scan's summary.
 */
export function storedCurrentState(row) {
  const current = row?.current;
  const cell = (row?.cells ?? []).find((item) => item.scanId === current?.scanId);
  if (FROZEN_CLASSIFICATIONS.has(cell?.classification)) {
    return { classification: cell.classification, scanId: current.scanId, stored: true };
  }
  if (cell?.kind === 'baseline' && current?.classification === 'BASELINE') {
    return { classification: current.classification, scanId: current.scanId, stored: true };
  }
  return { classification: null, scanId: current?.scanId ?? null, stored: false };
}

export function storedCurrentLabel(row) {
  const { classification } = storedCurrentState(row);
  return classification ?? NO_STORED_CLASSIFICATION;
}
