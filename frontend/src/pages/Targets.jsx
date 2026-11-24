import { useState } from 'react';

import { AuthorisationStamp } from '../components/AuthorisationStamp';
import { RegisterTargetSheet } from '../components/RegisterTargetSheet';
import { EmptySheet, SheetError, SheetLoading } from '../components/StateBlocks';
import { formatDateTime, formatPorts, formatScope } from '../lib/format';

export function Targets({
  client, targets, loading, error, onReload, onOpen, onScanQueued, onRegistered,
  session,
}) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const canRegister = !session || session.role === 'admin';
  const canScan = !session || ['operator', 'admin'].includes(session.role);

  async function register(payload) {
    setSubmitting(true);
    setFormError(null);
    try {
      const target = await client.createTarget(payload);
      setSheetOpen(false);
      await onRegistered(target);
    } catch (requestError) {
      setFormError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function scan(target) {
    setBusyId(target.id);
    setActionError(null);
    try {
      const queued = await client.runScan(target.id);
      onScanQueued(target, queued);
    } catch (requestError) {
      setActionError(requestError.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SheetLoading label="Loading the target register" />;
  if (error) return <SheetError message={error.message} onRetry={onReload} />;

  return (
    <section className="targets-page">
      <header className="page-head">
        <div>
          <p className="engraved">TARGET REGISTER</p>
          <h1>Targets</h1>
          <p className="lede">
            A target is observed only after an explicit, attributable authorisation record.
          </p>
        </div>
        <button
          type="button"
          className="primary-button"
          disabled={!canRegister}
          title={canRegister ? undefined : 'Registration requires an admin role.'}
          onClick={() => { setFormError(null); setSheetOpen(true); }}
        >
          Register target
        </button>
      </header>

      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      {targets.length === 0 ? (
        <EmptySheet
          title="No targets registered."
          action={(
            <button
              type="button"
              className="primary-button"
              disabled={!canRegister}
              onClick={() => setSheetOpen(true)}
            >
              Register the first target
            </button>
          )}
        >
          <p>Nothing has been observed. Register an authorised target to start the record.</p>
        </EmptySheet>
      ) : (
        <ul className="roster">
          {targets.map((target) => (
            <li className="roster-row" key={target.id}>
              <div className="roster-identity">
                <button type="button" className="roster-name" onClick={() => onOpen(target.id)}>
                  {target.name}
                </button>
                <span className="mono roster-address">
                  {target.address} · {target.target_type}
                </span>
              </div>

              <AuthorisationStamp target={target} compact />

              <div className="roster-field">
                <span className="engraved">SCOPE</span>
                <span>{formatScope(target.approved_scope)}</span>
                <span className="mono">{formatPorts(target.approved_ports)}</span>
              </div>

              <div className="roster-field">
                <span className="engraved">LAST SCAN</span>
                {target.last_scan ? (
                  <span>
                    #{target.last_scan.id} · {target.last_scan.status} ·{' '}
                    {formatDateTime(target.last_scan.completed_at ?? target.last_scan.started_at)}
                  </span>
                ) : <span>No scans</span>}
              </div>

              <div className="roster-actions">
                <button type="button" className="secondary-button" onClick={() => onOpen(target.id)}>
                  Open
                </button>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!target.scannable || !canScan || busyId === target.id}
                  title={!canScan ? 'Scanning requires an operator role.' : undefined}
                  onClick={() => scan(target)}
                >
                  {busyId === target.id ? 'Queueing…' : 'Run scan'}
                </button>
                {!target.scannable && (
                  <p className="refusal">
                    {target.refusal_reasons.length > 0
                      ? target.refusal_reasons.join(' ')
                      : 'Scanning is not permitted for this target.'}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {sheetOpen && (
        <RegisterTargetSheet
          onSubmit={register}
          onClose={() => setSheetOpen(false)}
          busy={submitting}
          error={formError}
        />
      )}
    </section>
  );
}
