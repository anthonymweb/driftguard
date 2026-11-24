import { useEffect, useState } from 'react';

import { SheetError, SheetLoading } from '../components/StateBlocks';
import { formatDateTime } from '../lib/format';

const FOOTPRINT = [
  ['targets', 'targets'],
  ['scans', 'scans'],
  ['evidence', 'evidence'],
  ['drift_events', 'drift events'],
];

function Section({ title, children }) {
  return (
    <section className="settings-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function Settings({ client, session, apiBase }) {
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
  const version = typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : '0.0.0';

  return (
    <section className="settings-page">
      <header className="page-head">
        <div>
          <p className="engraved">SERVICE STATE</p>
          <h1>Settings</h1>
        </div>
      </header>

      <Section title="Connection">
        <dl className="settings-list">
          <dt>API base</dt>
          <dd className="mono">{apiBase}</dd>
          <dt>Status</dt>
          <dd>Reachable · responded to <span className="mono">/api/stats</span></dd>
        </dl>
      </Section>

      <Section title="Mode">
        <p className="mono">{local ? 'LOCAL RESEARCH' : 'JWT'}</p>
        {local ? (
          <p>
            No bearer token is required. Requests are attributed to the local-research
            principal on this machine.
          </p>
        ) : (
          <p>
            {session
              ? `Signed in as ${session.username} · ${session.role}.`
              : 'Bearer token required. Sign in to attribute requests.'}
          </p>
        )}
      </Section>

      <Section title="Redaction">
        <p>
          {stats.redaction?.enabled
            ? 'Exports are tokenised before they leave the process.'
            : 'Redaction is disabled on this installation.'}
        </p>
        <p>
          The token map never leaves the backend process. Only the redacted evidence
          endpoint can be shared.
        </p>
      </Section>

      <Section title="Data footprint">
        <dl className="settings-list">
          {FOOTPRINT.map(([key, label]) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd className="mono">{String(stats[key] ?? 0)}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section title="Version">
        <p className="mono">driftguard-ui {version}</p>
        <p className="engraved">RECORD GENERATED {formatDateTime(new Date().toISOString())}</p>
      </Section>
    </section>
  );
}
