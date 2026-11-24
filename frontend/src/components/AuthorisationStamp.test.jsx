import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AuthorisationStamp } from './AuthorisationStamp';

const authorized = {
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls', 'network'],
  approved_ports: [8443, 8080],
};

describe('AuthorisationStamp', () => {
  it('shows who, when, why, and the approved scope', () => {
    render(<AuthorisationStamp target={authorized} />);
    expect(screen.getByText('A. Owner')).toBeTruthy();
    expect(screen.getByText('written approval')).toBeTruthy();
    expect(screen.getByText('12 Nov 2026')).toBeTruthy();
    expect(screen.getByText(/SCOPE TLS \/ NETWORK · PORTS 8443, 8080/)).toBeTruthy();
  });

  it('never invents a record for a pending target', () => {
    render(<AuthorisationStamp target={{ authorization_status: 'pending' }} />);
    expect(screen.getByText('PENDING — scanning refused')).toBeTruthy();
    expect(screen.getByText('No authorisation record is stored for this target.')).toBeTruthy();
    expect(screen.queryByText('A. Owner')).toBeNull();
  });
});
