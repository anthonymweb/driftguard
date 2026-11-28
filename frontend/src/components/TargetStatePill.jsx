import { FROZEN_CLASSIFICATIONS } from '../lib/target-state';

export function TargetStatePill({ state }) {
  const classification = FROZEN_CLASSIFICATIONS.has(state?.classification)
    ? state.classification
    : null;

  if (!classification) {
    return (
      <span className="status-pill target-state-pill is-unmeasured" aria-label="No stored drift state">
        <span aria-hidden="true">—</span>
        <span className="visually-hidden">No stored drift state</span>
      </span>
    );
  }

  const variant = classification.toLowerCase().replaceAll(' ', '-');
  return (
    <span
      className={`status-pill target-state-pill state-${variant}`}
      aria-label={`Stored drift state: ${classification} from scan ${state.scanId}`}
    >
      {classification}
    </span>
  );
}
