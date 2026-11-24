import { useState } from 'react';

const DESTINATIONS = [
  ['drift', 'Drift'],
  ['targets', 'Targets'],
  ['evaluation', 'Evaluation'],
  ['settings', 'Settings'],
];

export function AppShell({ route, mode, onSignOut, navNarrow = false, children }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const nav = (
    <nav
      className="top-nav"
      aria-label="Primary"
      id="primary-nav"
      hidden={navNarrow && !menuOpen ? true : undefined}
    >
      {DESTINATIONS.map(([page, label]) => (
        <a
          key={page}
          href={page === 'drift' ? '#/drift' : `#/${page}`}
          aria-current={route.page === page ? 'page' : undefined}
          onClick={() => setMenuOpen(false)}
        >
          {label}
        </a>
      ))}
    </nav>
  );

  return (
    <div className="shell">
      <header className="top-strip">
        <a className="wordmark" href="#/drift" aria-label="DriftGuard drift console">
          driftguard
        </a>
        {navNarrow ? (
          <div className="nav-menu">
            <button
              type="button"
              className="secondary-button"
              aria-expanded={menuOpen}
              aria-controls="primary-nav"
              onClick={() => setMenuOpen((open) => !open)}
            >
              Menu
            </button>
            {nav}
          </div>
        ) : nav}
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
