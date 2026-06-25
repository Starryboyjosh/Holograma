import { openWidgetWindow } from '../lib/windows';
import type { WidgetName } from '../lib/windows';

interface DetachButtonProps {
  widget: WidgetName;
  title?: string;
  className?: string;
}

// "Pop out ⧉" affordance. In Tauri it opens a real OS window; in the browser it
// falls back to window.open (see lib/windows).
export function DetachButton({ widget, title = 'Abrir en ventana aparte', className = '' }: DetachButtonProps) {
  return (
    <button
      type="button"
      onClick={() => void openWidgetWindow(widget)}
      title={title}
      aria-label={title}
      className={`p-1.5 rounded-lg border border-white/10 bg-white/[0.04] hover:bg-white/[0.1] hover:border-[#E25C1D]/40 text-slate-200 transition-all ${className}`}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M14 5h5m0 0v5m0-5L10 14M9 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-3"
        />
      </svg>
    </button>
  );
}
