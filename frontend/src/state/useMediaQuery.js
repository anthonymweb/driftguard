import { useEffect, useState } from 'react';

export function useMediaQuery(query, { fallback = false } = {}) {
  const [matches, setMatches] = useState(() => {
    if (typeof window !== 'object' || typeof window.matchMedia !== 'function') {
      return fallback;
    }
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window !== 'object' || typeof window.matchMedia !== 'function') return undefined;
    const list = window.matchMedia(query);
    const onChange = (event) => setMatches(event.matches);
    setMatches(list.matches);
    if (typeof list.addEventListener === 'function') {
      list.addEventListener('change', onChange);
      return () => list.removeEventListener('change', onChange);
    }
    return undefined;
  }, [query]);

  return matches;
}
