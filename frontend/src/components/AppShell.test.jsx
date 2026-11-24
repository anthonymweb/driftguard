import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AppShell } from './AppShell';

describe('AppShell', () => {
  it('renders typographic navigation and marks the current page', () => {
    render(
      <AppShell
        route={{ page: 'targets', targetId: null }}
        mode={{ kind: 'operator', username: 'alice', role: 'admin' }}
        onSignOut={vi.fn()}
      >
        <p>body</p>
      </AppShell>,
    );

    expect(screen.getByRole('link', { name: 'Drift' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Targets' }).getAttribute('aria-current'))
      .toBe('page');
    expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
    expect(screen.getByText('body')).toBeTruthy();
  });

  it('collapses navigation behind a menu at narrow widths', async () => {
    render(<AppShell route={{ page: 'drift', targetId: 1 }} mode={{ kind: 'local' }} navNarrow>
      <p>body</p>
    </AppShell>);
    const menu = screen.getByRole('button', { name: 'Menu' });
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    await userEvent.setup().click(menu);
    expect(screen.getByRole('button', { name: 'Menu' }).getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByRole('link', { name: 'Drift' })).toBeTruthy();
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
