import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useMediaQuery } from './useMediaQuery';

describe('useMediaQuery', () => {
  it('returns the fallback when matchMedia is unavailable', () => {
    const { result } = renderHook(() => useMediaQuery('(max-width: 900px)'));
    expect(result.current).toBe(false);
    const { result: held } = renderHook(() => useMediaQuery('(max-width: 900px)', { fallback: true }));
    expect(held.current).toBe(true);
  });

  it('follows a real media query when one exists', () => {
    const listeners = [];
    window.matchMedia = (query) => ({
      matches: query.includes('900'),
      media: query,
      addEventListener: (_type, fn) => listeners.push(fn),
      removeEventListener: (_type, fn) => listeners.splice(listeners.indexOf(fn), 1),
    });
    const { result, unmount } = renderHook(() => useMediaQuery('(max-width: 900px)'));
    expect(result.current).toBe(true);
    unmount();
    expect(listeners).toHaveLength(0);
    delete window.matchMedia;
  });
});
