import { useCallback, useEffect, useState } from 'react';

export function useTargets(client) {
  const [state, setState] = useState({ targets: [], loading: true, error: null });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const targets = await client.targets();
      setState({ targets, loading: false, error: null });
      return targets;
    } catch (error) {
      setState((current) => ({ ...current, loading: false, error }));
      return [];
    }
  }, [client]);

  useEffect(() => { load(); }, [load]);

  return { ...state, reload: load };
}
