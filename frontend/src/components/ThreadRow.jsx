import { storedCurrentLabel, storedCurrentState } from '../lib/stored-state';

export const MARK_TEXT = {
  baseline: 'baseline observation',
  present: 'present',
  new: 'new',
  recurring: 'recurring',
  fixed: 'fixed',
  absent: 'known absent',
  never: 'not observed',
  incomplete: 'not compared',
  pending: 'scan pending',
};

export function ThreadRow({ row, scans, selected, onSelect, rowIndex = 0, drawIndex = -1 }) {
  const currentState = storedCurrentState(row);
  const currentLabel = storedCurrentLabel(row);
  return (
    <tr
      className={`thread-row${selected ? ' is-selected' : ''}`}
      tabIndex={0}
      aria-selected={selected}
      onMouseEnter={() => onSelect(row.fingerprint)}
      onFocus={() => onSelect(row.fingerprint)}
      onClick={() => onSelect(row.fingerprint)}
    >
      <th scope="row" className="thread-title">
        <span>{row.title}</span>
        <span className="mono thread-resource">{row.resource}</span>
      </th>
      <td className="thread-category">
        <span className="mono-chip">{row.category}</span>
      </td>
      <td className="thread-severity">
        <span className="mono">{row.severity}</span>
      </td>
      {row.cells.map((cell, index) => (
        <td
          key={scans[index].id}
          className={`thread-cell kind-${cell.kind}${index === drawIndex ? ' is-drawing is-latest' : ''}`}
          style={index === drawIndex
            ? { animationDelay: `${Math.min(rowIndex, 8) * 20}ms` }
            : undefined}
        >
          {cell.lineLeft && <span className="thread-line line-left" aria-hidden="true" />}
          {cell.lineRight && <span className="thread-line line-right" aria-hidden="true" />}
          {!['incomplete', 'pending', 'absent'].includes(cell.kind) && (
            <span className={`mark mark-${cell.kind}`} aria-hidden="true" />
          )}
          {cell.kind === 'absent' && <span className="mark mark-absent" aria-hidden="true" />}
          <span className="state-pill">
            <span className="visually-hidden">{MARK_TEXT[cell.kind]}</span>
            {cell.classification && (
              <span className="state-token mono">{cell.classification}</span>
            )}
          </span>
        </td>
      ))}
      <td
        className={`thread-current current-${currentLabel.toLowerCase().replaceAll(' ', '-')}${currentState.stored ? '' : ' is-unmeasured'}`}
      >
        <span className="mono">{currentLabel}</span>
      </td>
    </tr>
  );
}
