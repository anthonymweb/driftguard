import { useState } from 'react';

import { AuthorisationStamp } from '../components/AuthorisationStamp';
import { Icon } from '../components/Icon';
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
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');

  const matches = {
    all: () => true,
    authorized: (t) => t.authorization_status === 'authorized',
    pending: (t) => t.authorization_status !== 'authorized',
    refused: (t) => !t.scannable,
  };
  const countFor = (key) => targets.filter(matches[key]).length;
  const needle = query.trim().toLowerCase();
  const visible = targets.filter((target) => matches[filter](target)
    && (!needle || [target.name, target.address, target.target_type,
      formatScope(target.approved_scope), formatPorts(target.approved_ports)]
      .join(' ').toLowerCase().includes(needle)));

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
          <Icon name="add" />
          Register target
        </button>
      </header>

      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      <ul className="stat-tiles">
        <li>
          <span className="tile-icon"><Icon name="list_alt" /></span>
          <p className="tile-label">Registered</p>
          <p className="tile-value">{targets.length}</p>
        </li>
        <li>
          <span className="tile-icon"><Icon name="verified_user" /></span>
          <p className="tile-label">Authorized</p>
          <p className="tile-value">{countFor('authorized')}</p>
        </li>
        <li>
          <span className="tile-icon"><Icon name="block" /></span>
          <p className="tile-label">Refused</p>
          <p className="tile-value">{countFor('refused')}</p>
        </li>
      </ul>

      {targets.length > 0 && (
        <div className="roster-toolbar">
          <div className="search-field">
            <Icon name="search" />
            <input
              type="search"
              aria-label="Search targets"
              placeholder="Search by name, address, or scope"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div className="filter-tabs" role="group" aria-label="Filter targets">
            {[
              ['all', 'All'],
              ['authorized', 'Authorized'],
              ['pending', 'Pending'],
              ['refused', 'Refused'],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                aria-pressed={filter === key}
                onClick={() => setFilter(key)}
              >
                {label} <span className="filter-count">{countFor(key)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

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
      ) : visible.length === 0 ? (
        <p role="status">No targets match this filter or search.</p>
      ) : (
        <ul className="roster">
          {visible.map((target) => (
            <li
              className={`roster-row${target.scannable ? '' : ' is-refused'}`}
              key={target.id}
            >
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
                  <Icon name="open_in_new" />
                  Open
                </button>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!target.scannable || !canScan || busyId === target.id}
                  title={!canScan ? 'Scanning requires an operator role.' : undefined}
                  onClick={() => scan(target)}
                >
                  <Icon name="play_arrow" />
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
