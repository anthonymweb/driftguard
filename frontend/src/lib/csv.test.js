import { describe, expect, it } from 'vitest';

import { redactedRecordFor, scanCsvFilename, toCsv } from './csv';

describe('redacted CSV', () => {
  it('writes a fixed header and escapes commas, quotes, and objects', () => {
    const csv = toCsv([{
      fingerprint: 'a', category: 'TLS', title: 'x,y', severity: 'High',
      resource: 'r', observed_at: '2026-11-12T09:30:00Z', details: { a: 1 },
    }]);
    const lines = csv.split('\r\n');
    expect(lines[0]).toBe('fingerprint,category,title,severity,resource,observed_at,details');
    expect(lines[1]).toBe('a,TLS,"x,y",High,r,2026-11-12T09:30:00Z,"{""a"":1}"');
    expect(csv.endsWith('\r\n')).toBe(true);
  });

  it('quotes embedded newlines and doubles embedded quotes', () => {
    const csv = toCsv([{ fingerprint: 'a', title: 'line one\nline "two"' }]);
    expect(csv).toContain('"line one\nline ""two"""');
  });

  it('builds a filesystem-safe filename from the target name', () => {
    expect(scanCsvFilename('eservices lab / 127.0.0.1', 12))
      .toBe('driftguard-eservices-lab-127-0-0-1-scan-12-redacted.csv');
    expect(scanCsvFilename('', 3)).toBe('driftguard-target-scan-3-redacted.csv');
  });

  it('finds the redacted record for one fingerprint', () => {
    const records = [{ fingerprint: 'a' }, { fingerprint: 'b' }];
    expect(redactedRecordFor(records, 'b')).toEqual({ fingerprint: 'b' });
    expect(redactedRecordFor(records, 'missing')).toBeNull();
  });
});
