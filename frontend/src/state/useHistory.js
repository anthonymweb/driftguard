import { useCallback, useEffect, useRef, useState } from 'react';

export function useHistory(client, targetId, { pollMs = 2000 } = {}) {
  const [state, setState] = useState({ history: null, loading: true, error: null });
  const controllerRef = useRef(null);
  const timerRef = useRef(null);
  const aliveRef = useRef(false);

  const load = useCallback(async ({ quiet = false } = {}) => {
    if (targetId == null) return null;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    if (!quiet) {
      setState((current) => ({ ...current, loading: true, error: null }));
    }
    try {
      const history = await client.history(targetId, { signal: controller.signal });
      if (!aliveRef.current) return history;
      setState({ history, loading: false, error: null });
      return history;
    } catch (error) {
      if (error.name === 'AbortError' || !aliveRef.current) return null;
      setState((current) => ({
        history: quiet ? current.history : null,
        loading: false,
        error,
      }));
      return null;
    }
  }, [client, targetId]);

  useEffect(() => {
    aliveRef.current = true;
    setState({ history: null, loading: true, error: null });
    load();
    return () => {
      aliveRef.current = false;
      controllerRef.current?.abort();
      clearTimeout(timerRef.current);
    };
  }, [load]);

  useEffect(() => {
    const pending = state.history?.scans?.some(({ scan }) =>
      scan.status === 'queued' || scan.status === 'running');
    clearTimeout(timerRef.current);
    if (!pending) return undefined;
    timerRef.current = setTimeout(() => load({ quiet: true }), pollMs);
    return () => clearTimeout(timerRef.current);
  }, [state.history, load, pollMs]);

  return { ...state, reload: () => load({ quiet: true }) };
}
