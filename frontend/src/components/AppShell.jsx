import { Icon } from './Icon';
import { APP_VERSION } from '../lib/version';

const DESTINATIONS = [
  ['drift', 'Drift', 'monitoring'],
  ['targets', 'Targets', 'dns'],
  ['evaluation', 'Evaluation', 'analytics'],
  ['settings', 'Settings', 'tune'],
];

export function AppShell({ route, mode, onSignOut, narrow = false, children }) {
  const modeChip = (
    <span className="mode-chip">
      {mode.kind === 'operator' ? `OPERATOR · ${mode.username}` : 'LOCAL RESEARCH'}
    </span>
  );
  const signOut = mode.kind === 'operator' && onSignOut ? (
    <button type="button" className="text-button" onClick={onSignOut}>Sign out</button>
  ) : null;

  const links = DESTINATIONS.map(([page, label, icon]) => (
    <a
      key={page}
      href={page === 'drift' ? '#/drift' : `#/${page}`}
      aria-current={route.page === page ? 'page' : undefined}
    >
      <Icon name={icon} />
      {label}
    </a>
  ));

  if (narrow) {
    return (
      <div className="shell">
        <header className="mobile-bar">
          <a className="brand" href="#/drift" aria-label="DriftGuard drift console">
            <Icon name="shield" />
            <span>DriftGuard</span>
          </a>
          <span className="version-chip">v{APP_VERSION}</span>
          {modeChip}
          {signOut}
        </header>
        <nav className="tab-bar" aria-label="Primary" id="primary-nav">{links}</nav>
        <main className="console">{children}</main>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#/drift" aria-label="DriftGuard drift console">
          <Icon name="shield" />
          <span>DriftGuard</span>
          <span className="version-chip">v{APP_VERSION}</span>
        </a>
        <nav className="side-nav" aria-label="Primary" id="primary-nav">{links}</nav>
        <div className="sidebar-foot">{modeChip}{signOut}</div>
      </aside>
      <main className="console">{children}</main>
    </div>
  );
}
