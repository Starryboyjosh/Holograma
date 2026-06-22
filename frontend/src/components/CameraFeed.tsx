import { useEffect, useState } from 'react';
import { mediaUrl } from '../lib/backend';
import { useBackendUrl } from '../hooks/useBackendUrl';

interface CameraFeedProps {
  /** Whether the YOLO stream should be shown (yoloEnabled && cameraOn). */
  enabled: boolean;
  /** Bumped to force the MJPEG <img> to reconnect. */
  nonce: number;
  showBadge?: boolean;
  offLabel?: string;
  errorLabel?: string;
  className?: string;
  imgClassName?: string;
}

// One MJPEG viewer for the assistant panel, the floating PiP, and the detached
// camera widget. Resolving the backend base (Tauri vs web) lives here so callers
// never build the /api/video_feed URL themselves.
export function CameraFeed({
  enabled,
  nonce,
  showBadge = true,
  offLabel = 'Cámara apagada',
  errorLabel = 'Cámara no disponible en el servidor',
  className = '',
  imgClassName = 'w-full h-full object-cover',
}: CameraFeedProps) {
  const base = useBackendUrl(); // re-render once the Tauri port resolves.
  const [error, setError] = useState(false);

  // A new nonce means a deliberate reconnect — clear any stale error.
  useEffect(() => {
    setError(false);
  }, [nonce, base]);

  return (
    <div
      className={`relative overflow-hidden bg-slate-950 flex items-center justify-center ${className}`}
    >
      {enabled ? (
        error ? (
          <span className="text-xs text-slate-500 font-bold px-4 text-center">{errorLabel}</span>
        ) : (
          <img
            src={mediaUrl(`/api/video_feed?n=${nonce}`)}
            alt="Detección YOLO en vivo"
            onError={() => setError(true)}
            className={imgClassName}
          />
        )
      ) : (
        <span className="text-xs text-slate-500 font-bold">{offLabel}</span>
      )}

      {showBadge && enabled && !error && (
        <div className="absolute top-2 left-2 bg-slate-900/90 border border-red-500/40 px-2 py-0.5 rounded-full flex items-center gap-1 text-[9px] text-white font-semibold">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse"></span>
          <span>LIVE · YOLO</span>
        </div>
      )}
    </div>
  );
}
