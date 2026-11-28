export function EvidenceSnapshots({ snapshots = [] }) {
  if (snapshots.length === 0) return null;

  return (
    <div className="snapshot-grid">
      {snapshots.map((snapshot) => {
        const detail = snapshot.detail == null
          ? 'No per-scan detail stored'
          : JSON.stringify(snapshot.detail, null, 2);
        return (
          <article
            key={snapshot.scanId}
            className={`snapshot-card state-${snapshot.state.toLowerCase().replace(/\s+/g, '-')}`}
            aria-label={`${snapshot.state} scan #${snapshot.scanId}`}
          >
            <p className="snapshot-state mono">{snapshot.state}</p>
            <p className="snapshot-time mono">
              {`#${snapshot.scanId} · ${snapshot.time}`}
            </p>
            <pre className="snapshot-detail mono">{detail}</pre>
          </article>
        );
      })}
    </div>
  );
}
