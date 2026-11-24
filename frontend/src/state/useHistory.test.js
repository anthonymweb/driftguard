import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useHistory } from './useHistory';

const payload = { target: { id: 1 }, scans: [], fingerprints: {} };

describe('useHistory', () => {
  it('loads one history page and clears the loading state', async () => {
    const client = { history: vi.fn().mockResolvedValue(payload) };
    const { result } = renderHook(() => useHistory(client, 1));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(client.history).toHaveBeenCalledWith(1, { signal: expect.any(AbortSignal) });
    expect(result.current.history).toEqual(payload);
  });

  it('aborts the in-flight request when the subject changes', () => {
    const signals = [];
    const client = {
      history: vi.fn().mockImplementation((_id, { signal }) => {
        signals.push(signal);
        return new Promise(() => {});
      }),
    };
    const { rerender } = renderHook(({ id }) => useHistory(client, id), {
      initialProps: { id: 1 },
    });
    rerender({ id: 2 });
    expect(signals[0].aborted).toBe(true);
    expect(client.history).toHaveBeenLastCalledWith(2, { signal: expect.any(AbortSignal) });
  });

  it('exposes a quiet reload', async () => {
    const client = { history: vi.fn().mockResolvedValue(payload) };
    const { result } = renderHook(() => useHistory(client, 1));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await result.current.reload();
    expect(client.history).toHaveBeenCalledTimes(2);
  });
});
