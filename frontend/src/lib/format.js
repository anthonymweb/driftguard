const DATE = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
});
const TIME = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
});

function asDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value) {
  const date = asDate(value);
  return date ? DATE.format(date) : '—';
}

export function formatDateTime(value) {
  const date = asDate(value);
  return date ? `${DATE.format(date)} · ${TIME.format(date)} UTC` : '—';
}

export function formatPorts(ports) {
  return ports?.length ? ports.join(', ') : '—';
}

const SCOPE_LABELS = { tls: 'TLS', network: 'NETWORK', http_api: 'API' };

export function formatScope(scope) {
  return scope?.length
    ? scope.map((item) => SCOPE_LABELS[item] ?? item.toUpperCase()).join(' / ')
    : '—';
}

export function countLabel(count, label) {
  return `${count} ${label}`;
}

export function formatRate(rate) {
  return rate == null ? '—' : `${(rate * 100).toFixed(1)}%`;
}
