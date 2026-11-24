import { useState } from 'react';

import {
  downloadText, redactedRecordFor, scanCsvFilename, toCsv,
} from '../lib/csv';
import { formatDateTime } from '../lib/format';

const clipboardCopy = async (text) => {
  if (!navigator.clipboard?.writeText) {
    throw new Error('Clipboard access is not available in this browser.');
  }
  await navigator.clipboard.writeText(text);
};

function lastObservedIndex(row) {
  for (let index = row.cells.length - 1; index >= 0; index -= 1) {
    if (['baseline', 'present', 'new', 'recurring'].includes(row.cells[index].kind)) {
      return index;
    }
  }
  return -1;
}

export function EvidenceDetail({
  row, scans, client, targetName,
  copy = clipboardCopy,
  download = downloadText,
}) {
  const [busy, setBusy] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const observedIndex = lastObservedIndex(row);
  const scan = observedIndex >= 0 ? scans[observedIndex] : null;

  async function withRecords(action, label) {
    if (!scan) {
      setError('This fingerprint has no completed observation in the current window.');
      return;
    }
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      const records = await client.redactedEvidence(scan.id);
      const record = redactedRecordFor(records, row.fingerprint);
      if (!record) {
        setError(`No redacted record was returned for this fingerprint in scan #${scan.id}.`);
        return;
      }
      await action(record, records);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(null);
    }
  }

  const copyRecord = () => withRecords(
    (record) => copy(JSON.stringify(record, null, 2))
      .then(() => setMessage('Redacted record copied.')),
    'copy',
  );

  const exportScan = () => withRecords(
    (_record, records) => {
      download(scanCsvFilename(targetName, scan.id), toCsv(records));
      setMessage(`Redacted evidence for scan #${scan.id} downloaded.`);
    },
    'export',
  );

  return (
    <aside className="detail-rail" aria-labelledby="detail-title">
      <div>
        <p className="engraved">SELECTED FINGERPRINT</p>
        <h2 id="detail-title">{row.title}</h2>
        <dl>
          <div><dt>Resource</dt><dd className="mono">{row.resource}</dd></div>
          <div><dt>Severity</dt><dd>{row.severity}</dd></div>
          <div><dt>Fingerprint</dt><dd className="mono">{row.fingerprint}</dd></div>
          <div>
            <dt>Last observed</dt>
            <dd>
              {scan
                ? `#${scan.id} · ${formatDateTime(scan.completedAt ?? scan.startedAt)}`
                : 'Never in this window'}
            </dd>
          </div>
          <div><dt>Current</dt><dd className="mono">{row.current.classification}</dd></div>
        </dl>
        <div className="detail-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={copyRecord}
            disabled={busy !== null || !scan}
          >
            {busy === 'copy' ? 'Copying…' : 'Copy redacted record'}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={exportScan}
            disabled={busy !== null || !scan}
          >
            {busy === 'export' ? 'Exporting…' : `Export scan #${scan?.id ?? '—'}`}
          </button>
        </div>
        <p className="detail-note">
          Export and copy use the redacted evidence endpoint. The token map never leaves
          the backend process.
        </p>
        {message && <p className="detail-status" role="status">{message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </div>

      <div className="detail-local">
        <p className="engraved">LOCAL DETAIL · NOT REDACTED</p>
        <pre>{JSON.stringify(row.detail ?? {}, null, 2)}</pre>
      </div>
    </aside>
  );
}
