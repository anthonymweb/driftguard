export const CSV_COLUMNS = [
  'fingerprint', 'category', 'title', 'severity', 'resource', 'observed_at', 'details',
];

function cell(value) {
  const text = value == null
    ? ''
    : typeof value === 'string' ? value : JSON.stringify(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv(rows) {
  const lines = [CSV_COLUMNS.join(',')];
  for (const row of rows) {
    lines.push(CSV_COLUMNS.map((column) => cell(row[column])).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}

export function safeFilename(name, fallback = 'target') {
  const slug = String(name ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || fallback;
}

export function scanCsvFilename(targetName, scanId) {
  return `driftguard-${safeFilename(targetName)}-scan-${scanId}-redacted.csv`;
}

export function redactedRecordFor(records, fingerprint) {
  return records.find((record) => record.fingerprint === fingerprint) ?? null;
}

export function downloadText(filename, text, mime = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
