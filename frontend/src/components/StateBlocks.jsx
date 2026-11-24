export function SheetLoading({ label = 'Loading the record' }) {
  return (
    <div className="sheet-loading" role="status" aria-live="polite">
      <p className="engraved">{label}</p>
      {[0, 1, 2, 3].map((row) => <span key={row} className="skeleton-row" />)}
    </div>
  );
}

export function SheetError({ message, onRetry }) {
  return (
    <div className="sheet-error" role="alert">
      <p className="engraved">REQUEST FAILED</p>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="secondary-button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptySheet({ title, children, action }) {
  return (
    <section className="empty-sheet">
      <p className="engraved">NO RECORD</p>
      <h1>{title}</h1>
      {children}
      {action}
    </section>
  );
}

export function PendingScanPanel({ scans }) {
  if (!scans.length) return null;
  return (
    <div className="pending-panel" role="status" aria-live="polite">
      {scans.map((scan) => (
        <p key={scan.id}>
          Scan #{scan.id} is {scan.status}. The column becomes comparable only when the
          scan completes; until then it is not compared.
        </p>
      ))}
    </div>
  );
}
