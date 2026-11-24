import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RegisterTargetSheet } from './RegisterTargetSheet';

describe('RegisterTargetSheet', () => {
  it('requires a complete authorisation record before submitting', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<RegisterTargetSheet onSubmit={onSubmit} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'svc');
    await user.type(screen.getByLabelText('Address'), 'https://127.0.0.1:8443');
    await user.click(screen.getByLabelText(/Authorized$/));
    await user.click(screen.getByRole('button', { name: 'Register target' }));

    expect(screen.getByText('Record who authorised this assessment.')).toBeTruthy();
    expect(screen.getByText('Record when authorisation was given.')).toBeTruthy();
    expect(screen.getByText('Select at least one approved area.')).toBeTruthy();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits a pending target with scope and parsed ports', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RegisterTargetSheet onSubmit={onSubmit} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'svc');
    await user.type(screen.getByLabelText('Address'), 'https://127.0.0.1:8443');
    await user.click(screen.getByLabelText('TLS'));
    await user.type(screen.getByLabelText('Approved ports'), '8443, 8080');
    await user.click(screen.getByRole('button', { name: 'Register target' }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      name: 'svc',
      authorization_status: 'pending',
      approved_scope: ['tls'],
      approved_ports: [8080, 8443],
    }));
  });

  it('closes without submitting', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<RegisterTargetSheet onSubmit={vi.fn()} onClose={onClose} />);
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
