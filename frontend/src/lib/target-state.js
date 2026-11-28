export const FROZEN_CLASSIFICATIONS = new Set([
  'BASELINE',
  'NEW',
  'PERSISTENT',
  'FIXED',
  'RECURRING',
  'NO DRIFT',
]);

function recordedAt(event) {
  const time = Date.parse(event?.recorded_at);
  return Number.isNaN(time) ? null : time;
}

function latestDriftEvent(drift) {
  if (drift.length === 0) return null;

  let chosen = drift[0];
  let chosenAt = recordedAt(chosen);
  for (let index = 1; index < drift.length; index += 1) {
    const event = drift[index];
    const at = recordedAt(event);
    if (at === null && chosenAt === null) {
      chosen = event; // no timestamps: preserve stored array order
    } else if (at !== null && (chosenAt === null || at >= chosenAt)) {
      chosen = event;
      chosenAt = at;
    }
  }
  return chosen;
}

/**
 * Read the most recent stored drift state for a target. This is a lookup, not a
 * classifier: only classifications already stored by the backend can be returned.
 */
export function latestStoredState(history) {
  const comparable = [...(history?.scans ?? [])]
    .filter((entry) => entry?.comparable === true && entry.scan != null)
    .sort((a, b) => a.scan.id - b.scan.id);
  const latest = comparable.at(-1);
  if (!latest) return null;

  const scanId = latest.scan.id;
  const drift = latestDriftEvent(latest.drift ?? []);
  if (drift) {
    return FROZEN_CLASSIFICATIONS.has(drift.classification)
      ? { classification: drift.classification, scanId }
      : null;
  }

  const state = latest.summary?.state;
  if (state === 'BASELINE' || state === 'NO DRIFT') {
    return { classification: state, scanId };
  }
  return null;
}
