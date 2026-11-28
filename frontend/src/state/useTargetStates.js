import { useEffect, useRef, useState } from 'react';

import { latestStoredState } from '../lib/target-state';

/**
 * Read one stored history page per target. Results are verbatim lookups; stale
 * responses are discarded and a failed read leaves that target without a state.
 */
export function useTargetStates(client, targets = []) {
  // Key on ids, not array identity, so a parent re-render does not reread history.
  const ids = targets.map((target) => target.id).join('|');
  const generationRef = useRef(0);
  const [states, setStates] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    const current = targets;

    if (current.length === 0) {
      setStates({});
      setLoading(false);
      return undefined;
    }

    const collected = {};
    let outstanding = current.length;
    setStates({});
    setLoading(true);

    function settle() {
      outstanding -= 1;
      if (outstanding === 0 && generation === generationRef.current) setLoading(false);
    }

    for (const target of current) {
      Promise.resolve()
        .then(() => client.history(target.id))
        .then((history) => {
          if (generation !== generationRef.current) return;
          collected[target.id] = latestStoredState(history);
          setStates({ ...collected });
        })
        .catch(() => {
          if (generation !== generationRef.current) return;
          collected[target.id] = null;
          setStates({ ...collected });
        })
        .finally(settle);
    }
    return undefined;
  }, [client, ids]); // eslint-disable-line react-hooks/exhaustive-deps

  return { states, loading };
}
