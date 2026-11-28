import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useTargetStates } from './useTargetStates';

const cleanHistory = (id) => ({ scans: [
  { comparable: true, scan: { id }, drift: [], summary: { state: 'NO DRIFT' } },
] });

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

describe('useTargetStates', () => {
  it('reads one stored history per target and exposes the latest state', async () => {
    const client = {
      history: vi.fn().mockResolvedValue({ scans: [
        { comparable: true, scan: { id: 9 }, drift: [], summary: { state: 'NO DRIFT' } },
      ] }),
    };
    const { result } = renderHook(() => useTargetStates(client, [{ id: 1 }, { id: 2 }]));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(client.history).toHaveBeenCalledTimes(2);
    expect(client.history).toHaveBeenCalledWith(1);
    expect(client.history).toHaveBeenCalledWith(2);
    expect(result.current.states[1]).toEqual({ classification: 'NO DRIFT', scanId: 9 });
  });

  it('ignores stale responses and stops loading when the current reads settle', async () => {
    const first = deferred();
    const second = deferred();
    const client = {
      history: vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise),
    };
    const { result, rerender } = renderHook(
      ({ ids }) => useTargetStates(client, ids.map((id) => ({ id }))),
      { initialProps: { ids: [1] } },
    );

    rerender({ ids: [2] });

    await act(async () => { second.resolve(cleanHistory(22)); });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.states[2]).toEqual({ classification: 'NO DRIFT', scanId: 22 });

    await act(async () => { first.resolve(cleanHistory(11)); });
    expect(client.history).toHaveBeenCalledTimes(2);
    expect(result.current.states[1]).toBeUndefined();
    expect(result.current.states[2]).toEqual({ classification: 'NO DRIFT', scanId: 22 });
  });

  it('records no state and makes no retry after a failed history read', async () => {
    const client = { history: vi.fn().mockRejectedValue(new Error('history unavailable')) };
    const { result } = renderHook(() => useTargetStates(client, [{ id: 3 }]));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(client.history).toHaveBeenCalledTimes(1);
    expect(result.current.states[3]).toBeNull();
  });

  it('settles without reads when there are no targets', async () => {
    const client = { history: vi.fn() };
    const { result } = renderHook(() => useTargetStates(client, []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(client.history).not.toHaveBeenCalled();
    expect(result.current.states).toEqual({});
  });

  it('does not refetch when the same target ids are passed in a new array', async () => {
    const targets = [{ id: 1 }];
    const client = { history: vi.fn().mockResolvedValue(cleanHistory(1)) };
    const { rerender } = renderHook(({ items }) => useTargetStates(client, items), {
      initialProps: { items: targets },
    });

    await waitFor(() => expect(client.history).toHaveBeenCalledTimes(1));
    rerender({ items: [...targets] });
    expect(client.history).toHaveBeenCalledTimes(1);
  });
});
