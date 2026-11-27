import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AppShell } from './AppShell';

describe('AppShell', () => {
  it('renders a top navigation bar on desktop and marks the current page', () => {
    const { container } = render(
      <AppShell
        route={{ page: 'targets', targetId: null }}
        mode={{ kind: 'operator', username: 'alice', role: 'admin' }}
        onSignOut={vi.fn()}
      >
        <p>body</p>
      </AppShell>,
    );

    expect(container.querySelector('.topbar')).toBeTruthy();
    expect(container.querySelector('.sidebar')).toBeNull();
    expect(screen.getAllByRole('navigation')).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Targets' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
    expect(screen.getByText(/^v\d+\.\d+\.\d+$/)).toBeTruthy();
    expect(screen.getByText('body')).toBeTruthy();
  });

  it('renders a bottom tab bar at narrow widths instead of the sidebar', () => {
    render(
      <AppShell route={{ page: 'drift', targetId: 1 }} mode={{ kind: 'local' }} narrow>
        <p>body</p>
      </AppShell>,
    );

    expect(document.querySelector('.tab-bar')).toBeTruthy();
    expect(document.querySelector('.sidebar')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Menu' })).toBeNull();
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(screen.getAllByRole('navigation')).toHaveLength(1);
    expect(within(nav).getAllByRole('link')).toHaveLength(4);
    expect(screen.getByRole('link', { name: 'Drift' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('link', { name: 'Drift' }).getAttribute('href')).toBe('#/drift');
    expect(screen.getByText('LOCAL RESEARCH')).toBeTruthy();
  });

  it('states local-research mode and offers sign-out only for an operator', async () => {
    const onSignOut = vi.fn();
    const { rerender } = render(
      <AppShell route={{ page: 'drift', targetId: 2 }} mode={{ kind: 'local' }}>
        <p>body</p>
      </AppShell>,
    );
    expect(screen.getByText('LOCAL RESEARCH')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull();

    rerender(
      <AppShell
        route={{ page: 'drift', targetId: 2 }}
        mode={{ kind: 'operator', username: 'alice', role: 'admin' }}
        onSignOut={onSignOut}
      >
        <p>body</p>
      </AppShell>,
    );
    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign out' }));
    expect(onSignOut).toHaveBeenCalledOnce();
  });
});
