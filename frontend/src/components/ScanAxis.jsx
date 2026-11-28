import { formatDate } from '../lib/format';

const COMPARED_LABEL = {
  BASELINE: 'BASELINE',
  'NO DRIFT': 'NO DRIFT',
  CHANGED: 'CHANGED',
};

export function columnState(scan) {
  if (scan.kind === 'baseline') return 'BASELINE';
  if (scan.kind === 'compared') return COMPARED_LABEL[scan.summary?.state] ?? 'CHANGED';
  if (scan.kind === 'incomplete') return 'NOT COMPARED';
  return String(scan.status).toUpperCase();
}

export function ScanAxis({ scans, latestIndex = -1 }) {
  return (
    <thead>
      <tr>
        <th scope="col" className="axis-finding">Finding</th>
        <th scope="col" className="axis-category">Category</th>
        <th scope="col" className="axis-severity">Severity</th>
        {scans.map((scan, index) => (
          <th
            key={scan.id}
            scope="col"
            className={`axis-scan kind-${scan.kind}${index === latestIndex ? ' is-latest' : ''}`}
          >
            <span className="axis-id mono">#{scan.id}</span>
            <span className="axis-date mono">
              {formatDate(scan.completedAt ?? scan.startedAt)}
            </span>
            <span className="axis-state mono">{columnState(scan)}</span>
          </th>
        ))}
        <th scope="col" className="axis-current">Current</th>
      </tr>
    </thead>
  );
}
