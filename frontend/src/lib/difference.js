import { formatDate } from './format';

const PARTS = [
  ['NEW', 'new'],
  ['PERSISTENT', 'persistent'],
  ['FIXED', 'fixed'],
  ['RECURRING', 'recurring'],
];

export function describeDifference(model) {
  const latest = model?.latestComparable;
  if (!latest) {
    return { text: 'No completed observations yet.', state: 'EMPTY' };
  }

  const state = latest.summary?.state ?? 'CHANGED';
  if (state === 'BASELINE') {
    return {
      text: `Baseline recorded ${formatDate(latest.completedAt ?? latest.startedAt)}.`,
      state: 'BASELINE',
    };
  }

  const counts = latest.summary?.counts ?? {};
  const since = model.previousComparable
    ? ` since scan #${model.previousComparable.id}`
    : '';
  const parts = PARTS
    .filter(([key]) => (counts[key] ?? 0) > 0)
    .map(([key, label]) => `${counts[key]} ${label}`);

  if (state === 'NO DRIFT' || parts.length === 0) {
    return state === 'NO DRIFT'
      ? { text: `No change${since}.`, state: 'NO DRIFT' }
      : { text: `Changed${since}.`, state: 'CHANGED' };
  }

  return { text: `${parts.join(' · ')}${since}.`, state: 'CHANGED' };
}
