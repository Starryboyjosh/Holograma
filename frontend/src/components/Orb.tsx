import { ORB_RING } from '../theme';
import type { AssistantState } from '../theme';
import micIcon from '../assets/holomind/icon-microphone.webp';

interface OrbProps {
  state: AssistantState;
  onActivate: () => void;
}

/**
 * Orbe del asistente (nodos 29:1410 / 29:1411 / 29:1412 / 31:1881).
 *
 * El diseño lo compone con tres círculos concéntricos naranjas — halo difuso, aro
 * fino y disco central — y el icono de micrófono encima. Los círculos van en CSS
 * porque laten y giran según el estado; el micrófono sí es el asset exportado, que
 * es la única parte con forma propia que no puedo redibujar.
 */
export function Orb({ state, onActivate }: OrbProps) {
  const interactive = state === 'idle' || state === 'listening';
  const bars = state === 'listening' || state === 'speaking';

  return (
    <button
      type="button"
      onClick={onActivate}
      className={`relative flex h-48 w-48 items-center justify-center rounded-full transition-transform ${
        interactive ? 'cursor-pointer hover:scale-105 active:scale-95' : 'cursor-default'
      }`}
      // No puede llamarse "Toca para hablar": ese es el nombre del selector de modo
      // de voz del diseño, y dos controles distintos con el mismo nombre accesible
      // son indistinguibles para un lector de pantalla.
      title="Activar micrófono"
      aria-label="Activar micrófono"
    >
      {/* Halo difuso exterior. */}
      <span
        aria-hidden
        className={`absolute inset-0 rounded-full bg-orange/30 blur-2xl ${
          state === 'idle' ? 'organic-orb' : 'animate-pulse'
        }`}
      />
      {state === 'listening' && (
        <span
          aria-hidden
          className="absolute inset-2 animate-ping rounded-full border-2 border-emerald-500/50"
        />
      )}
      {/* Aro fino (177px en el diseño). */}
      <span
        aria-hidden
        className={`absolute h-[177px] w-[177px] rounded-full border-2 ${
          state === 'thinking' ? 'spin-slow border-amber-500/50' : ORB_RING[state]
        }`}
      />
      {/* Disco central (132px en el diseño). */}
      <span
        aria-hidden
        className="absolute h-[132px] w-[132px] rounded-full bg-orange/35"
      />

      <span className="relative flex h-[44px] w-[44px] items-center justify-center">
        {state === 'thinking' ? (
          <svg className="h-9 w-9 animate-spin text-amber-600" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        ) : bars ? (
          <span className="flex h-8 items-end gap-1">
            <span
              className={`h-5 w-1.5 animate-pulse rounded-full ${state === 'listening' ? 'bg-emerald-600' : 'bg-orange-deep'}`}
              style={{ animationDelay: '0.1s' }}
            ></span>
            <span
              className={`h-8 w-1.5 animate-pulse rounded-full ${state === 'listening' ? 'bg-emerald-500' : 'bg-orange'}`}
              style={{ animationDelay: '0.3s' }}
            ></span>
            <span
              className={`h-6 w-1.5 animate-pulse rounded-full ${state === 'listening' ? 'bg-emerald-600' : 'bg-orange-deep'}`}
              style={{ animationDelay: '0.5s' }}
            ></span>
            <span
              className={`h-4 w-1.5 animate-pulse rounded-full ${state === 'listening' ? 'bg-emerald-500' : 'bg-orange'}`}
              style={{ animationDelay: '0.2s' }}
            ></span>
          </span>
        ) : (
          <img
            src={micIcon}
            alt=""
            draggable={false}
            className="h-full w-full object-contain"
          />
        )}
      </span>
    </button>
  );
}
