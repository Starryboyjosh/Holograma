import { createContext, useCallback, useContext, useRef, useState } from 'react';
import type { ReactNode } from 'react';

type ShowToast = (msg: string) => void;

const ToastCtx = createContext<ShowToast | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback<ShowToast>((msg) => {
    setMessage(msg);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setMessage(null), 3000);
  }, []);

  return (
    <ToastCtx.Provider value={showToast}>
      {children}
      {message && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] bg-[#1C2D5A] border border-[#E25C1D]/30 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 animate-[fade-in_0.2s_ease-out]">
          <svg
            className="w-5 h-5 text-[#E25C1D] shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-sm font-semibold">{message}</span>
        </div>
      )}
    </ToastCtx.Provider>
  );
}

export function useToast(): ShowToast {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
