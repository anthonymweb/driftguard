const DESTINATIONS = [
  ['drift', 'Drift'],
  ['targets', 'Targets'],
  ['evaluation', 'Evaluation'],
  ['settings', 'Settings'],
];

export function AppShell({ route, mode, onSignOut, children }) {
  return (
    <div className="shell">
      <header className="top-strip">
        <a className="wordmark" href="#/drift" aria-label="DriftGuard drift console">
          driftguard
        </a>
        <nav className="top-nav" aria-label="Primary">
          {DESTINATIONS.map(([page, label]) => (
            <a
              key={page}
              href={page === 'drift' ? '#/drift' : `#/${page}`}
              aria-current={route.page === page ? 'page' : undefined}
            >
              {label}
            </a>
          ))}
        </nav>
        <div className="mode">
          <span className="mode-chip mono">
            {mode.kind === 'operator' ? `OPERATOR · ${mode.username}` : 'LOCAL RESEARCH'}
          </span>
          {mode.kind === 'operator' && (
            <button type="button" className="text-button" onClick={onSignOut}>
              Sign out
            </button>
          )}
        </div>
      </header>
      <main className="console">{children}</main>
    </div>
  );
}
