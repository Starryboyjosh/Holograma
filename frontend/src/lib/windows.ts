// Detachable widget windows.
//
// In Tauri each widget opens as a real OS window (WebviewWindow) pointing at a
// hash route in the same bundle. In the browser we fall back to window.open so
// nothing regresses on the web build. The backend broadcasts WS events to every
// connection, so each window can hold its own socket independently.

import { backendBase, isTauriRuntime } from './backend';

export type WidgetName = 'camera' | 'chat' | 'transcript' | 'controls';

interface WidgetMeta {
  title: string;
  width: number;
  height: number;
}

const WIDGET_META: Record<WidgetName, WidgetMeta> = {
  camera: { title: 'Cámara · Holograma UNEV', width: 480, height: 860 },
  chat: { title: 'Conversación · Holograma UNEV', width: 460, height: 680 },
  transcript: { title: 'Transcripción · Holograma UNEV', width: 460, height: 540 },
  controls: { title: 'Control del Holograma · UNEV', width: 540, height: 760 },
};

// HashRouter keeps deep links working under Tauri's asset protocol, the bundled
// app, and FastAPI's web mode without any server-side rewrite.
function widgetHash(name: WidgetName): string {
  return `#/widget/${name}`;
}

export async function openWidgetWindow(name: WidgetName): Promise<void> {
  const meta = WIDGET_META[name];

  try {
    const core = await import('@tauri-apps/api/core');
    if (core.isTauri()) {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      const label = `widget-${name}`;
      const existing = await WebviewWindow.getByLabel(label);
      if (existing) {
        await existing.setFocus();
        return;
      }
      const win = new WebviewWindow(label, {
        url: `/${widgetHash(name)}`,
        title: meta.title,
        width: meta.width,
        height: meta.height,
        resizable: true,
      });
      win.once('tauri://error', (e) => console.error('[widget]', name, e));
      return;
    }
  } catch (err) {
    console.warn('[widget] Tauri window unavailable, using browser window', err);
  }

  // Browser fallback.
  const base = backendBase();
  window.open(
    `${base}/${widgetHash(name)}`,
    `widget-${name}`,
    `width=${meta.width},height=${meta.height},menubar=no,toolbar=no`,
  );
}

/** Whether to surface "pop out" affordances natively vs. the in-app PiP. */
export function widgetsAreDetachable(): boolean {
  return isTauriRuntime() || typeof window.open === 'function';
}
