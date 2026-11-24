const AREA_ORDER = ['TLS', 'NETWORK', 'API'];
const PRESENT_KINDS = new Set(['present', 'baseline', 'new', 'recurring']);

function areaOf(category) {
  const key = String(category ?? '').toUpperCase();
  return AREA_ORDER.includes(key) ? key : 'OTHER';
}

function isPending(status) {
  return status === 'queued' || status === 'running';
}

function nextComparableCell(cells, scans, index) {
  for (let cursor = index + 1; cursor < cells.length; cursor += 1) {
    if (scans[cursor].comparable) return cells[cursor];
  }
  return null;
}

function previousComparableCell(cells, scans, index) {
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    if (scans[cursor].comparable) return cells[cursor];
  }
  return null;
}

export function buildThreadModel(history = {}) {
  const fingerprints = history.fingerprints ?? {};
  const items = [...(history.scans ?? [])].sort((a, b) => a.scan.id - b.scan.id);

  const scans = items.map((item) => {
    const comparable = item.comparable === true && item.scan.status === 'completed';
    const summary = item.summary
      ?? { state: comparable ? 'CHANGED' : 'INCOMPLETE', counts: {} };
    let kind = 'incomplete';
    if (comparable) kind = summary.state === 'BASELINE' ? 'baseline' : 'compared';
    else if (isPending(item.scan.status)) kind = 'pending';
    return {
      id: item.scan.id,
      status: item.scan.status,
      startedAt: item.scan.started_at,
      completedAt: item.scan.completed_at,
      label: item.scan.label ?? null,
      comparable,
      pending: isPending(item.scan.status),
      summary,
      kind,
      item,
    };
  });

  const comparableScans = scans.filter((scan) => scan.comparable);
  const latestComparable = comparableScans.at(-1) ?? null;
  const previousComparable = comparableScans.at(-2) ?? null;

  const driftByScan = new Map();
  const referenced = new Set();
  for (const scan of scans) {
    if (!scan.comparable) continue;
    const drift = new Map();
    for (const event of scan.item.drift ?? []) {
      drift.set(event.evidence_fingerprint, event.classification);
      referenced.add(event.evidence_fingerprint);
    }
    driftByScan.set(scan.id, drift);
    for (const evidence of scan.item.evidence ?? []) {
      referenced.add(evidence.fingerprint);
    }
  }

  const rows = [];
  for (const fingerprint of referenced) {
    const meta = fingerprints[fingerprint] ?? {
      title: fingerprint,
      category: 'OTHER',
      severity: 'Unknown',
      resource: '—',
    };
    const cells = [];
    let everSeen = false;
    let latestEvidence = null;
    let current = null;

    for (const scan of scans) {
      if (!scan.comparable) {
        cells.push({
          scanId: scan.id,
          kind: scan.pending ? 'pending' : 'incomplete',
          classification: null,
          lineLeft: false,
          lineRight: false,
        });
        continue;
      }

      const evidence = (scan.item.evidence ?? [])
        .find((candidate) => candidate.fingerprint === fingerprint);
      const observed = Boolean(evidence);
      const classification = driftByScan.get(scan.id)?.get(fingerprint) ?? null;
      let kind;

      if (observed) {
        everSeen = true;
        latestEvidence = evidence;
        if (scan.kind === 'baseline') kind = 'baseline';
        else if (classification === 'NEW') kind = 'new';
        else if (classification === 'RECURRING') kind = 'recurring';
        else kind = 'present';
        current = {
          classification: kind === 'baseline'
            ? 'BASELINE'
            : kind === 'present' ? 'PERSISTENT' : classification,
          scanId: scan.id,
        };
      } else if (classification === 'FIXED') {
        kind = 'fixed';
        current = { classification: 'FIXED', scanId: scan.id };
      } else {
        kind = everSeen ? 'absent' : 'never';
      }

      cells.push({
        scanId: scan.id, kind, classification, lineLeft: false, lineRight: false,
      });
    }

    if (!current) continue;

    for (let index = 0; index < cells.length; index += 1) {
      const cell = cells[index];
      if (cell.kind === 'present') {
        cell.lineLeft = true;
        cell.lineRight = true;
      } else if (PRESENT_KINDS.has(cell.kind)) {
        cell.lineRight = PRESENT_KINDS.has(
          nextComparableCell(cells, scans, index)?.kind,
        );
      } else if (cell.kind === 'fixed') {
        cell.lineLeft = PRESENT_KINDS.has(
          previousComparableCell(cells, scans, index)?.kind,
        );
      }
    }

    rows.push({
      fingerprint,
      title: meta.title,
      category: meta.category,
      area: areaOf(meta.category),
      severity: meta.severity,
      resource: meta.resource,
      cells,
      current,
      detail: latestEvidence?.details ?? null,
      observedAt: latestEvidence?.observed_at ?? null,
    });
  }

  const groups = [...AREA_ORDER, 'OTHER']
    .map((key) => ({
      key,
      rows: rows
        .filter((entry) => entry.area === key)
        .sort((a, b) => a.title.localeCompare(b.title)
          || a.resource.localeCompare(b.resource)
          || a.fingerprint.localeCompare(b.fingerprint)),
    }))
    .filter((group) => group.rows.length > 0);

  return {
    scans,
    groups,
    latestComparable,
    previousComparable,
    hasComparable: comparableScans.length > 0,
    pendingScans: scans.filter((scan) => scan.pending),
  };
}
