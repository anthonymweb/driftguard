import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SignIn } from './SignIn';

describe('SignIn', () => {
  it('submits trimmed credentials', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<SignIn onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('Username'), '  alice  ');
    await user.type(screen.getByLabelText('Password'), 'correct horse');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(onSubmit).toHaveBeenCalledWith('alice', 'correct horse');
  });

  it('explains a missing field before calling the API', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SignIn onSubmit={onSubmit} />);

    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(screen.getByRole('alert').textContent).toContain('username and password');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows the API error verbatim', () => {
    render(<SignIn onSubmit={vi.fn()} error="Invalid credentials" />);
    expect(screen.getByRole('alert').textContent).toBe('Invalid credentials');
  });
});
