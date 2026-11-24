import { describe, expect, it, vi } from 'vitest';

import { navigate, parseHash, routeToHash } from './useHashRoute';

describe('hash routing', () => {
  it('parses the four destinations', () => {
    expect(parseHash('')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/drift')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/targets')).toEqual({ page: 'targets', targetId: null });
    expect(parseHash('#/evaluation')).toEqual({ page: 'evaluation', targetId: null });
    expect(parseHash('#/settings')).toEqual({ page: 'settings', targetId: null });
  });

  it('deep-links a target', () => {
    expect(parseHash('#/drift/12')).toEqual({ page: 'drift', targetId: 12 });
    expect(parseHash('#/drift/12/')).toEqual({ page: 'drift', targetId: 12 });
  });

  it('falls back to Drift for unknown or malformed input', () => {
    expect(parseHash('#/nope')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/drift/abc')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/drift/0')).toEqual({ page: 'drift', targetId: null });
  });

  it('round-trips destinations', () => {
    expect(routeToHash({ page: 'targets' })).toBe('#/targets');
    expect(routeToHash({ page: 'drift', targetId: 3 })).toBe('#/drift/3');
    expect(parseHash(routeToHash({ page: 'drift', targetId: 9 })))
      .toEqual({ page: 'drift', targetId: 9 });
  });

  it('replaces history without stacking entries', () => {
    const win = {
      location: { hash: '#/targets' },
      history: { replaceState: vi.fn() },
      dispatchEvent: vi.fn(),
      Event: globalThis.Event,
    };
    navigate({ page: 'drift', targetId: 2 }, { replace: true, win });
    expect(win.history.replaceState).toHaveBeenCalledWith(null, '', '#/drift/2');
    expect(win.dispatchEvent).toHaveBeenCalledOnce();
  });
});
