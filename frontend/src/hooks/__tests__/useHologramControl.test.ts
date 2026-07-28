import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useHologramControl } from '../useHologramControl';

const fetchMock = vi.fn();
vi.mock('../../lib/backend', () => ({ apiFetch: (...args: unknown[]) => fetchMock(...args) }));

const status = { connected: false, ip: '', port: 50200, units: [], rotation: { active: false } };
function response(body: unknown) { return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) }); }

describe('useHologramControl', () => {
  beforeEach(() => { fetchMock.mockImplementation((path: string) => path.endsWith('/status') ? response(status) : path.endsWith('/identities') ? response({ identities: [] }) : response({ promotions: [] })); });
  afterEach(() => { vi.clearAllMocks(); });

  it('starts one polling interval and does not overlap requests', async () => {
    const { result, unmount } = renderHook(() => useHologramControl());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetchMock).toHaveBeenCalledTimes(3);
    unmount();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
