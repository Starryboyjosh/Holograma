import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from './backend';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllEnvs();
});

describe('apiFetch hologram token transport', () => {
  it('adds the token only to hologram requests and preserves existing headers', async () => {
    vi.stubEnv('VITE_HOLOGRAM_API_TOKEN', 'local-capability');
    fetchMock.mockResolvedValue(new Response('{}'));

    await apiFetch('/api/hologram/status', { headers: { 'Content-Type': 'application/json', 'X-Existing': 'keep' } });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(url).toBe('/api/hologram/status');
    expect(url).not.toContain('local-capability');
    expect(headers.get('X-API-Token')).toBe('local-capability');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('X-Existing')).toBe('keep');
  });

  it('does not add a token when absent or to non-hologram requests', async () => {
    fetchMock.mockResolvedValue(new Response('{}'));
    await apiFetch('/api/hologram/status');
    await apiFetch('/api/config', { method: 'POST' });

    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('X-API-Token')).toBeNull();
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get('X-API-Token')).toBeNull();
  });
});
