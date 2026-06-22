// Single source of truth for reaching the FastAPI backend.
//
// - Web mode (browser served by FastAPI): same origin, so the base is '' and
//   every path stays relative exactly like before (`/api/...`, `/ws/chat`).
// - Tauri desktop: the Rust shell starts the backend on a free port and exposes
//   it via the `get_backend_url` command, so the base is an absolute
//   `http://127.0.0.1:<port>` that all fetch/websocket/media URLs are built on.

let cachedBase: string | null = null;
let inflight: Promise<string> | null = null;

async function detectBase(): Promise<string> {
  try {
    const core = await import('@tauri-apps/api/core');
    if (core.isTauri()) {
      const url = await core.invoke<string>('get_backend_url');
      return (url || '').replace(/\/+$/, '');
    }
  } catch {
    // Not running inside Tauri (or the API is unavailable): fall through to
    // same-origin web mode.
  }
  return '';
}

/** Resolve (and cache) the backend base URL. Safe to call repeatedly. */
export function resolveBackendUrl(): Promise<string> {
  if (cachedBase !== null) return Promise.resolve(cachedBase);
  if (!inflight) {
    inflight = detectBase().then((base) => {
      cachedBase = base;
      return base;
    });
  }
  return inflight;
}

/** Cached base URL ('' until resolved, '' permanently in web mode). */
export function backendBase(): string {
  return cachedBase ?? '';
}

function withSlash(path: string): string {
  return path.startsWith('/') ? path : `/${path}`;
}

/** Absolute URL for an API path, e.g. apiUrl('/api/config'). */
export function apiUrl(path: string): string {
  return `${backendBase()}${withSlash(path)}`;
}

/** fetch() that targets the backend regardless of runtime. */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  await resolveBackendUrl();
  return fetch(apiUrl(path), init);
}

/** URL for media served by the backend (MJPEG feed, /data thumbnails). Leaves
 *  absolute/data/blob URLs untouched. */
export function mediaUrl(path: string): string {
  if (!path) return path;
  if (/^(https?:|data:|blob:)/.test(path)) return path;
  return apiUrl(path);
}

/** WebSocket URL for a backend path, e.g. wsUrl('/ws/chat'). */
export function wsUrl(path: string): string {
  const base = backendBase();
  if (base) {
    return base.replace(/^http/, 'ws') + withSlash(path);
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}${withSlash(path)}`;
}

/** Best-effort synchronous check for the Tauri runtime (UI branching only). */
export function isTauriRuntime(): boolean {
  return (
    typeof window !== 'undefined' &&
    ('__TAURI_INTERNALS__' in window || '__TAURI__' in window)
  );
}
