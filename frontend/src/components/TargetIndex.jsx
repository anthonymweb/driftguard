import { formatDate } from '../lib/format';

export function TargetIndex({ targets, selectedId, onSelect, narrow = false }) {
  return (
    <nav className="target-index" aria-label="Targets">
      <p className="engraved">TARGETS</p>
      {narrow ? (
        <label className="target-select-label">
          <span className="engraved">SUBJECT</span>
          <select
            aria-label="Subject"
            value={selectedId ?? ''}
            onChange={(event) => onSelect(Number(event.target.value))}
          >
            {targets.map((target) => (
              <option key={target.id} value={target.id}>{target.name}</option>
            ))}
          </select>
        </label>
      ) : (
        <ul>
        {targets.map((target) => {
          const selected = target.id === selectedId;
          return (
            <li key={target.id}>
              <a
                href={`#/drift/${target.id}`}
                className={`target-chip${selected ? ' is-selected' : ''}`}
                aria-current={selected ? 'page' : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onSelect(target.id);
                }}
              >
                <span
                  className="index-mark"
                  data-authorized={target.authorization_status === 'authorized'}
                  aria-hidden="true"
                />
                <span className="index-name">{target.name}</span>
                <span className="mono index-address">{target.address}</span>
                <span className="index-last">
                  {target.last_scan
                    ? `Last scan #${target.last_scan.id} · ${target.last_scan.status} · ${formatDate(target.last_scan.completed_at ?? target.last_scan.started_at)}`
                    : 'No scans'}
                </span>
              </a>
            </li>
          );
        })}
        </ul>
      )}
    </nav>
  );
}
