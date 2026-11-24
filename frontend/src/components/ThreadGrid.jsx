import { Fragment } from 'react';

import { ScanAxis } from './ScanAxis';
import { ThreadRow } from './ThreadRow';

export function ThreadGrid({ model, selected, onSelect }) {
  const drawIndex = model.scans.reduce(
    (found, scan, index) => (scan.comparable ? index : found),
    -1,
  );
  let rowIndex = 0;

  return (
    <div className="thread-wrap">
      <table className="thread-grid">
        <caption className="visually-hidden">
          Evidence threads across {model.scans.length} scans. Columns marked not compared
          are excluded from the comparison.
        </caption>
        <ScanAxis scans={model.scans} />
        <tbody>
          {model.groups.map((group) => (
            <Fragment key={group.key}>
              <tr className="thread-group">
                <th scope="colgroup" colSpan={model.scans.length + 2}>{group.key}</th>
              </tr>
              {group.rows.map((row) => {
                const index = rowIndex;
                rowIndex += 1;
                return (
                  <ThreadRow
                    key={row.fingerprint}
                    row={row}
                    scans={model.scans}
                    selected={selected === row.fingerprint}
                    onSelect={onSelect}
                    rowIndex={index}
                    drawIndex={drawIndex}
                  />
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
