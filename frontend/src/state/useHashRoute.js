import { useEffect, useState } from 'react';

export const PAGES = ['drift', 'targets', 'evaluation', 'settings'];
const TARGET_HASH = /^\/drift\/([1-9]\d*)\/?$/;

export function parseHash(hash = '') {
  const raw = hash.replace(/^#/, '');
  if (!raw || raw === '/') return { page: 'drift', targetId: null };
  if (raw === '/drift' || raw === '/drift/') {
    return { page: 'drift', targetId: null };
  }
  const target = TARGET_HASH.exec(raw);
  if (target) return { page: 'drift', targetId: Number(target[1]) };
  const page = raw.replace(/^\/|\/$/g, '');
  if (PAGES.includes(page)) return { page, targetId: null };
  return { page: 'drift', targetId: null };
}

export function routeToHash({ page = 'drift', targetId = null } = {}) {
  if (page === 'drift') {
    return targetId == null ? '#/drift' : `#/drift/${targetId}`;
  }
  return `#/${page}`;
}

export function navigate(route, { replace = false, win = window } = {}) {
  const hash = routeToHash(route);
  if (win.location.hash === hash) return;
  if (replace) {
    win.history.replaceState(null, '', hash);
    win.dispatchEvent(new win.Event('hashchange'));
  } else {
    win.location.hash = hash;
  }
}

export function useHashRoute(win = window) {
  const [route, setRoute] = useState(() => parseHash(win.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(win.location.hash));
    onChange();
    win.addEventListener('hashchange', onChange);
    return () => win.removeEventListener('hashchange', onChange);
  }, [win]);

  return route;
}
