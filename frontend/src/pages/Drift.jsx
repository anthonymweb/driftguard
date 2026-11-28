import { useEffect, useMemo, useState } from 'react';

import { AuthorisationStamp } from '../components/AuthorisationStamp';
import { DifferenceLine } from '../components/DifferenceLine';
import { EvidenceDetail } from '../components/EvidenceDetail';
import { Icon } from '../components/Icon';
import {
  EmptySheet, PendingScanPanel, SheetError, SheetLoading,
} from '../components/StateBlocks';
import { TargetIndex } from '../components/TargetIndex';
import { ThreadCards } from '../components/ThreadCards';
import { ThreadGrid } from '../components/ThreadGrid';
import { buildThreadModel } from '../lib/threads';
import { useHistory } from '../state/useHistory';
import { useMediaQuery } from '../state/useMediaQuery';

export function Drift({
  client, targets, targetsLoading, targetsError, targetId, onSelectTarget,
  onOpenTargets, session,
}) {
  const { history, loading, error, reload } = useHistory(client, targetId);
  const narrow = useMediaQuery('(max-width: 900px)');
  const [selectedFingerprint, setSelectedFingerprint] = useState(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [scanMessage, setScanMessage] = useState(null);
  const [scanError, setScanError] = useState(null);

  const model = useMemo(() => (history ? buildThreadModel(history) : null), [history]);
  const target = history?.target ?? targets.find((entry) => entry.id === targetId) ?? null;
  const selectedRow = model?.groups
    .flatMap((group) => group.rows)
    .find((row) => row.fingerprint === selectedFingerprint) ?? null;
  const canScan = !session || ['operator', 'admin'].includes(session.role);

  useEffect(() => {
    setSelectedFingerprint(null);
    setScanMessage(null);
    setScanError(null);
  }, [targetId]);

  async function runScan() {
    if (!target) return;
    setScanBusy(true);
    setScanMessage(null);
    setScanError(null);
    try {
      const scan = await client.runScan(target.id);
      setScanMessage(
        `Scan #${scan.id} queued. The column becomes comparable when it completes.`,
      );
      await reload();
    } catch (requestError) {
      setScanError(requestError.message);
    } finally {
      setScanBusy(false);
    }
  }

  if (targetsLoading) return <SheetLoading label="Loading the target register" />;
  if (targetsError) {
    return <SheetError message={targetsError.message} onRetry={() => window.location.reload()} />;
  }
  if (targets.length === 0) {
    return (
      <EmptySheet
        title="No targets registered."
        action={(
          <button type="button" className="primary-button" onClick={onOpenTargets}>
            Register a target
          </button>
        )}
      >
        <p>Nothing has been observed. Register an authorised target to start the record.</p>
      </EmptySheet>
    );
  }
  if (targetId == null || !target) {
    return (
      <EmptySheet
        title={targetId == null ? 'No target selected.' : 'Target not found.'}
        action={(
          <button type="button" className="secondary-button" onClick={onOpenTargets}>
            Open the target register
          </button>
        )}
      >
        <p>Choose a target to read its observation record.</p>
      </EmptySheet>
    );
  }

  const scanDisabled = !target.scannable || !canScan || scanBusy;
  const refusal = !canScan
    ? 'Scanning requires an operator role.'
    : !target.scannable
      ? target.refusal_reasons.join(' ') || 'Scanning is not permitted for this target.'
      : null;

  return (
    <div className="drift-page">
      <TargetIndex
        targets={targets}
        selectedId={targetId}
        onSelect={onSelectTarget}
        narrow={narrow}
      />

      <section className="drift-subject">
        <header className="subject surface-card">
          <div>
            <p className="eyebrow">SUBJECT</p>
            <div className="subject-title">
              <h1>{target.name}</h1>
              {target.status && (
                <span className="status-pill subject-status">{target.status}</span>
              )}
            </div>
            <p className="mono subject-meta">
              {target.address} · {target.target_type}
            </p>
          </div>
          <div className="subject-actions">
            <button type="button" className="secondary-button" onClick={reload}>
              <Icon name="refresh" />
              Refresh
            </button>
            <button
              type="button"
              className="primary-button"
              disabled={scanDisabled}
              title={refusal ?? undefined}
              onClick={runScan}
            >
              <Icon name="play_arrow" />
              {scanBusy ? 'Queueing…' : 'Run scan'}
            </button>
          </div>
        </header>

        <AuthorisationStamp target={target} />
        {refusal && <p className="refusal">{refusal}</p>}
        {scanMessage && <p className="detail-status" role="status">{scanMessage}</p>}
        {scanError && <p className="form-error" role="alert">{scanError}</p>}

        {loading && <SheetLoading label="Loading the observation record" />}
        {!loading && error && (
          <SheetError message={error.message} onRetry={reload} />
        )}

        {!loading && !error && model && !model.hasComparable && (
          <>
            <PendingScanPanel scans={model.pendingScans} />
            <EmptySheet
              title="No observations yet."
              action={target.scannable && canScan ? (
                <button
                  type="button"
                  className="primary-button"
                  onClick={runScan}
                  disabled={scanBusy}
                >
                  Run baseline
                </button>
              ) : undefined}
            >
              <p>Run a baseline to start the record. Nothing is inferred from an empty database.</p>
            </EmptySheet>
          </>
        )}

        {!loading && !error && model?.hasComparable && (
          <>
            <DifferenceLine model={model} />
            {model.latestComparable?.summary?.counts && (
              <ul className="metric-cards" aria-label="Counts in the latest comparable scan">
                {[
                  ['NEW', 'New findings', 'metric-new'],
                  ['PERSISTENT', 'Persistent findings', 'metric-persistent'],
                  ['FIXED', 'Fixed findings', 'metric-fixed'],
                  ['RECURRING', 'Recurring findings', 'metric-recurring'],
                ].map(([key, label, cls]) => (
                  <li key={key} className={`metric-card kpi-card ${cls}`}>
                    <div className="metric-head">
                      <p className="metric-label">{label}</p>
                      <span className="status-pill metric-badge">{key}</span>
                    </div>
                    <div className="metric-readout">
                      <p className="metric-value">
                        {model.latestComparable.summary.counts[key] ?? 0}
                      </p>
                      <p className="metric-note">in the latest comparable scan</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <PendingScanPanel scans={model.pendingScans} />
            {narrow ? (
              <ThreadCards
                model={model}
                selected={selectedFingerprint}
                onSelect={setSelectedFingerprint}
              />
            ) : (
              <ThreadGrid
                model={model}
                selected={selectedFingerprint}
                onSelect={setSelectedFingerprint}
              />
            )}
            {selectedRow ? (
              <EvidenceDetail
                row={selectedRow}
                scans={model.scans}
                client={client}
                targetName={target.name}
              />
            ) : (
              <p className="detail-prompt">
                Select a thread to inspect its evidence. Hover or focus a row; the rail
                never invents detail.
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
