import { describe, expect, it } from 'vitest';

import {
  countLabel,
  formatDate,
  formatDateTime,
  formatPorts,
  formatRate,
  formatScope,
} from './format';

describe('format', () => {
  it('formats dates in UTC so the sheet reads the same everywhere', () => {
    expect(formatDate('2026-11-12T09:30:00Z')).toBe('12 Nov 2026');
    expect(formatDateTime('2026-11-12T09:30:00Z')).toBe('12 Nov 2026 · 09:30 UTC');
  });

  it('returns an em dash for missing or invalid dates', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('not-a-date')).toBe('—');
    expect(formatDateTime(undefined)).toBe('—');
  });

  it('formats approved scope and ports without inventing values', () => {
    expect(formatScope(['tls', 'network', 'http_api'])).toBe('TLS / NETWORK / API');
    expect(formatScope([])).toBe('—');
    expect(formatPorts([8443, 8080])).toBe('8443, 8080');
    expect(formatPorts([])).toBe('—');
  });

  it('formats counts and rates for the difference line and readouts', () => {
    expect(countLabel(1, 'new')).toBe('1 new');
    expect(countLabel(2, 'persistent')).toBe('2 persistent');
    expect(formatRate(0.964)).toBe('96.4%');
    expect(formatRate(0)).toBe('0.0%');
    expect(formatRate(null)).toBe('—');
  });
});
