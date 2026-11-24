import { MARK_TEXT } from './ThreadRow';

export function ThreadCards({ model, selected, onSelect }) {
  return (
    <ul className="thread-cards">
      {model.groups.map((group) => (
        <li key={group.key} className="card-group">
          <p className="engraved">{group.key}</p>
          <ul>
            {group.rows.map((row) => (
              <li
                key={row.fingerprint}
                className={`thread-card${selected === row.fingerprint ? ' is-selected' : ''}`}
              >
                <div className="card-head">
                  <h2 className="card-title">
                    <button type="button" onClick={() => onSelect(row.fingerprint)}>
                      {row.title}
                    </button>
                  </h2>
                  <span className="card-current mono">{row.current.classification}</span>
                  {['Critical', 'High'].includes(row.severity) && (
                    <span className="severity mono">{row.severity}</span>
                  )}
                </div>
                <span className="mono card-resource">{row.resource}</span>
                <ol className="compact-timeline" aria-hidden="true">
                  {row.cells.map((cell, index) => (
                    <li key={model.scans[index].id} className={`tick kind-${cell.kind}`}>
                      <span className={`mark mark-${cell.kind}`} />
                    </li>
                  ))}
                </ol>
                <div className="visually-hidden">
                  {row.cells.map((cell, index) => (
                    <span key={model.scans[index].id}>
                      {`#${model.scans[index].id} — ${MARK_TEXT[cell.kind]}`}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
