import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useToast } from './ToastContext';
import { useChatSocket } from '../hooks/useChatSocket';
import { useConfig } from '../hooks/useConfig';
import { useHologram } from '../hooks/useHologram';
import { apiFetch } from '../lib/backend';
import type { ChatSocket } from '../hooks/useChatSocket';

interface CameraState {
  cameraOn: boolean;
  setCameraOn: (on: boolean) => void;
  toggleCamera: () => void;
  /** Bumped whenever the camera is (re)enabled to force a fresh MJPEG stream. */
  feedNonce: number;
}

interface SessionValue {
  chat: ChatSocket;
  config: ReturnType<typeof useConfig>;
  hologram: ReturnType<typeof useHologram>;
  camera: CameraState;
}

const SessionCtx = createContext<SessionValue | null>(null);

// Single shared instance of the live state machine (chat socket, hologram TCP,
// config, camera) for the main window's screens. Detachable widget windows
// run in their own React root and instantiate their own hooks instead.
export function SessionProvider({ children }: { children: ReactNode }) {
  const showToast = useToast();

  const chat = useChatSocket({ onToast: showToast });
  const config = useConfig();
  const hologram = useHologram({ onToast: showToast });

  const [cameraOn, setCameraOnState] = useState(true);
  const [feedNonce, setFeedNonce] = useState(0);

  // Tell the backend to actually start/stop the capture device — turning the
  // camera "off" must release it, not just hide the <img>. Fire-and-forget.
  const applyCameraDevice = useCallback((on: boolean) => {
    apiFetch('/api/camera', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: on }),
    }).catch(() => {});
  }, []);

  const setCameraOn = useCallback(
    (on: boolean) => {
      setCameraOnState(on);
      if (on) setFeedNonce((n) => n + 1); // reconnect the stream when turning back on.
      applyCameraDevice(on);
    },
    [applyCameraDevice],
  );

  const toggleCamera = useCallback(() => setCameraOn(!cameraOn), [cameraOn, setCameraOn]);

  const camera = useMemo<CameraState>(
    () => ({ cameraOn, setCameraOn, toggleCamera, feedNonce }),
    [cameraOn, setCameraOn, toggleCamera, feedNonce],
  );

  const value = useMemo<SessionValue>(
    () => ({ chat, config, hologram, camera }),
    [chat, config, hologram, camera],
  );

  return <SessionCtx.Provider value={value}>{children}</SessionCtx.Provider>;
}

export function useSession(): SessionValue {
  const ctx = useContext(SessionCtx);
  if (!ctx) throw new Error('useSession must be used within a SessionProvider');
  return ctx;
}
