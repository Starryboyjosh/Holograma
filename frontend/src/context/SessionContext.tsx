import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useToast } from './ToastContext';
import { useChatSocket } from '../hooks/useChatSocket';
import { useConfig } from '../hooks/useConfig';
import { useHologram } from '../hooks/useHologram';
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
// config, camera) for the main window's five screens. Detachable widget windows
// run in their own React root and instantiate their own hooks instead.
export function SessionProvider({ children }: { children: ReactNode }) {
  const showToast = useToast();

  const chat = useChatSocket({ onToast: showToast });
  const config = useConfig();
  const hologram = useHologram({ onToast: showToast });

  const [cameraOn, setCameraOnState] = useState(true);
  const [feedNonce, setFeedNonce] = useState(0);

  const setCameraOn = useCallback((on: boolean) => {
    setCameraOnState(on);
    if (on) setFeedNonce((n) => n + 1); // reconnect the stream when turning back on.
  }, []);

  const toggleCamera = useCallback(() => {
    setCameraOnState((prev) => {
      const next = !prev;
      if (next) setFeedNonce((n) => n + 1);
      return next;
    });
  }, []);

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
