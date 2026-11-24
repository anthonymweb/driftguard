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
      {row.cells.map((cell, index) => (
        <td
          key={scans[index].id}
          className={`thread-cell kind-${cell.kind}${index === drawIndex ? ' is-drawing' : ''}`}
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
          <span className="visually-hidden">{MARK_TEXT[cell.kind]}</span>
        </td>
      ))}
      <td className={`thread-current current-${row.current.classification.toLowerCase().replaceAll(' ', '-')}`}>
        <span className="mono">{row.current.classification}</span>
        {['Critical', 'High'].includes(row.severity) && (
          <span className="severity mono">{row.severity}</span>
        )}
      </td>
    </tr>
  );
}
