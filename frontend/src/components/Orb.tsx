import { ORB_RING } from '../theme';
import type { AssistantState } from '../theme';

interface OrbProps {
  state: AssistantState;
  onActivate: () => void;
}

// The tappable assistant orb. Visuals key off the assistant state machine:
// listening (green ping + bars), thinking (amber spinner), speaking (orange
// bars), idle (mic). Extracted verbatim from the original assistant screen.
export function Orb({ state, onActivate }: OrbProps) {
  const interactive = state === 'idle' || state === 'listening';
  const bars = state === 'listening' || state === 'speaking';

  return (
    <button
      type="button"
      onClick={onActivate}
      className={`relative flex justify-center items-center h-40 w-40 mb-4 rounded-full transition-all ${
        interactive ? 'cursor-pointer hover:scale-105 active:scale-95' : 'cursor-default'
      }`}
      title="Toca para hablar"
      aria-label="Toca para hablar"
    >
      <span
        className={`absolute inset-0 rounded-full bg-[#E25C1D] opacity-10 blur-xl ${
          state !== 'idle' ? 'animate-pulse' : ''
        }`}
      ></span>
      {state === 'listening' && (
        <span className="absolute inset-0 rounded-full border-2 border-emerald-400/50 animate-ping"></span>
      )}
      <span
        className={`absolute w-36 h-36 rounded-full border ${
          state === 'thinking' ? 'border-amber-400/40 spin-slow' : 'border-orange-500/15'
        }`}
      ></span>
      <span
        className={`relative w-24 h-24 rounded-full bg-gradient-to-tr from-[#0F172A] to-[#2B1B15] border-2 ${ORB_RING[state]} flex items-center justify-center shadow-inner transition-all`}
      >
        {state === 'thinking' ? (
          <svg className="w-9 h-9 text-amber-400 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        ) : bars ? (
          <span className="flex items-end gap-1 h-8">
            <span
              className={`w-1.5 rounded-full animate-pulse h-5 ${state === 'listening' ? 'bg-emerald-400' : 'bg-[#E25C1D]'}`}
              style={{ animationDelay: '0.1s' }}
            ></span>
            <span
              className={`w-1.5 rounded-full animate-pulse h-8 ${state === 'listening' ? 'bg-emerald-300' : 'bg-orange-400'}`}
              style={{ animationDelay: '0.3s' }}
            ></span>
            <span
              className={`w-1.5 rounded-full animate-pulse h-6 ${state === 'listening' ? 'bg-emerald-400' : 'bg-[#E25C1D]'}`}
              style={{ animationDelay: '0.5s' }}
            ></span>
            <span
              className={`w-1.5 rounded-full animate-pulse h-4 ${state === 'listening' ? 'bg-emerald-300' : 'bg-orange-400'}`}
              style={{ animationDelay: '0.2s' }}
            ></span>
          </span>
        ) : (
          <svg className="w-10 h-10 text-[#E25C1D]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        )}
      </span>
    </button>
  );
}
