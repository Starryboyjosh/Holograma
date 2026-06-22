import type { ReactNode } from 'react';

// Shared chrome for the detached widget windows: a full-viewport dark panel with
// an optional title bar. Each widget renders standalone (no AppShell / router nav).
export function WidgetFrame({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="min-h-screen w-full bg-[#070A12] text-white flex flex-col p-4 gap-3">
      {title && (
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-2 h-2 rounded-full bg-[#E25C1D]"></span>
          <span className="text-[#E25C1D] font-bold text-sm tracking-wide">{title}</span>
        </div>
      )}
      {children}
    </div>
  );
}
