import { useEffect, useState } from 'react';

import { Icon } from '../components/Icon';
import { SheetError, SheetLoading } from '../components/StateBlocks';
import { formatDateTime, formatPorts, formatScope } from '../lib/format';
import { APP_VERSION } from '../lib/version';

const FOOTPRINT = [
  ['targets', 'targets'],
  ['scans', 'scans'],
  ['evidence', 'evidence'],
  ['drift_events', 'drift events'],
];

const REDACTED_FIELDS = ['Authorization', 'Cookie', 'X-Api-Key'];

function Panel({ letter, title, subtitle, icon, footer, children }) {
  return (
    <section className="settings-panel">
      <div className="settings-panel-body">
        <div className="settings-panel-head">
          <div>
            <div className="settings-panel-heading">
              <span className="panel-badge" aria-hidden="true">{letter}</span>
              <h2>{title}</h2>
            </div>
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {icon && <span className="panel-icon"><Icon name={icon} /></span>}
        </div>
        <div className="settings-panel-content">{children}</div>
      </div>
      {footer && <div className="settings-panel-footer">{footer}</div>}
    </section>
  );
}

function Row({ label, value, mono = false }) {
  return (
    <div className="settings-row">
      <dt>{label}</dt>
      <dd className={mono ? 'mono' : undefined}>{value}</dd>
    </div>
  );
}

export function Settings({ client, session, apiBase, targets = [] }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ stats: null, loading: true, error: null });

  useEffect(() => {
    let active = true;
    setState({ stats: null, loading: true, error: null });
    client.stats()
      .then((stats) => active && setState({ stats, loading: false, error: null }))
      .catch((error) => active && setState({ stats: null, loading: false, error }));
    return () => { active = false; };
  }, [client, refreshKey]);

  if (state.loading) return <SheetLoading label="Reading service state" />;
  if (state.error) {
    return <SheetError message={state.error.message} onRetry={() => setRefreshKey((key) => key + 1)} />;
  }

  const { stats } = state;
  const local = stats.auth_mode === 'local_research';
  const target = targets?.[0];
  const redactionEnabled = stats.redaction?.enabled === true;

  return (
    <section className="settings-page">
      <header className="page-head settings-head">
        <div>
          <p className="engraved">SERVICE STATE</p>
          <h1>Settings</h1>
        </div>
      </header>

      <ul className="settings-ribbon" aria-label="Service telemetry">
        <li>
          <p className="ribbon-label">Registered targets</p>
          <p className="ribbon-value mono">{stats.targets ?? 0} stored</p>
        </li>
        <li>
          <p className="ribbon-label">Stored scans</p>
          <p className="ribbon-value mono">{stats.scans ?? 0} recorded</p>
        </li>
        <li>
          <p className="ribbon-label">Evidence records</p>
          <p className="ribbon-value mono">{stats.evidence ?? 0} stored</p>
        </li>
        <li>
          <p className="ribbon-label">Drift events recorded</p>
          <p className="ribbon-value mono">{stats.drift_events ?? 0} recorded</p>
        </li>
      </ul>

      <div className="settings-grid">
        <Panel
          letter="A"
          title="Connection"
          subtitle="Service connection and request mode"
          icon="link"
          footer={<span>Source · /api/stats</span>}
        >
          <dl className="settings-rows">
            <Row label="API base" value={apiBase} mono />
            <Row label="Stats endpoint" value={<>Reachable · responded to <span className="mono">/api/stats</span></>} />
            <Row label="Authentication" value={local ? 'LOCAL RESEARCH' : 'JWT'} mono />
          </dl>
          <p className="panel-note">
            {local
              ? 'No bearer token is required. Requests are attributed to the local-research principal on this machine.'
              : session
                ? `Signed in as ${session.username} · ${session.role}.`
                : 'Bearer token required. Sign in to attribute requests.'}
          </p>
        </Panel>

        <Panel
          letter="B"
          title="Authorisation provenance"
          subtitle="First stored authorisation record"
          icon="badge"
          footer={<span>Source · /api/targets</span>}
        >
          {target ? (
            <dl className="settings-rows">
              <Row label="Target" value={target.name} mono />
              <Row label="Authorised by" value={target.authorized_by ?? '—'} />
              <Row label="Authorised at" value={formatDateTime(target.authorized_at)} mono />
              <Row label="Basis" value={target.authorization_basis ?? '—'} />
              <Row label="Approved scope" value={formatScope(target.approved_scope)} mono />
              <Row label="Approved ports" value={formatPorts(target.approved_ports)} mono />
            </dl>
          ) : (
            <p className="panel-empty">
              No stored authorisation record is available for this installation.
            </p>
          )}
        </Panel>

        <Panel
          letter="C"
          title="Redaction"
          subtitle="Field names tokenised before export"
          icon="enhanced_encryption"
          footer={<span>Token map · local process only</span>}
        >
          <p className="panel-status">
            <span className={`status-dot ${redactionEnabled ? 'is-on' : 'is-off'}`} aria-hidden="true" />
            {redactionEnabled ? 'Enabled' : 'Disabled'}
          </p>
          <p className="panel-note">
            {redactionEnabled
              ? 'Exports are tokenised before they leave the process.'
              : 'Redaction is disabled on this installation.'}
          </p>
          <ul className="redaction-legend" aria-label="Tokenised header fields">
            {REDACTED_FIELDS.map((field) => (
              <li key={field}>
                <span className="legend-field mono">{field}</span>
                <span className="legend-arrow" aria-hidden="true">→</span>
                <span className="legend-result">tokenised</span>
              </li>
            ))}
          </ul>
          <p className="panel-note">
            The token map never leaves the backend process. Only the redacted evidence
            endpoint can be shared.
          </p>
        </Panel>

        <Panel
          letter="D"
          title="Data footprint"
          subtitle="Record counts from the local service"
          icon="database"
          footer={<span className="engraved">RECORD GENERATED {formatDateTime(new Date().toISOString())}</span>}
        >
          <ul className="footprint-tiles">
            {FOOTPRINT.map(([key, label]) => (
              <li key={key}>
                <p className="tile-label">{label}</p>
                <p className="tile-value mono">{String(stats[key] ?? 0)}</p>
              </li>
            ))}
          </ul>
          <p className="footprint-version mono">driftguard-ui {APP_VERSION}</p>
        </Panel>
      </div>

      <aside className="settings-banner" aria-label="Evidence guarantee">
        <span className="banner-icon"><Icon name="verified_user" /></span>
        <div>
          <p className="banner-title">Evidence only</p>
          <p>Only completed scans populate the console. Every finding comes from a stored observation.</p>
        </div>
      </aside>
    </section>
  );
}
