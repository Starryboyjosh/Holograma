import { useState } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useSession } from '../context/SessionContext';
import { CameraFeed } from './CameraFeed';

const NAV_ITEMS = [
  { to: '/', label: 'Inicio', end: true },
  { to: '/assistant', label: 'Hablar', end: false },
  { to: '/teaching', label: 'Entrenar Visión', shortLabel: 'Entrenar', end: false },
  { to: '/remote', label: 'Control', end: false },
  { to: '/settings', label: 'Configuración', shortLabel: 'Ajustes', end: false },
];

function WsChip({ connected }: { connected: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
        connected
          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${connected ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
      {connected ? 'Conectado' : 'Reconectando...'}
    </span>
  );
}

export function AppShell() {
  const { isDark, toggle } = useTheme();
  const { chat, camera } = useSession();
  const navigate = useNavigate();
  const location = useLocation();

  // Floating PiP — only when the camera is on and we're not already on the
  // full assistant view. Drag is a browser-only nicety; in Tauri the real
  // detachable camera window is preferred.
  const [pipPosition, setPipPosition] = useState({ x: 74, y: 72 });
  const [drag, setDrag] = useState<{ x: number; y: number; px: number; py: number } | null>(null);
  const pipVisible = camera.cameraOn && location.pathname !== '/assistant';

  const onPipDragMove = (e: ReactMouseEvent) => {
    if (!drag) return;
    const dx = ((e.clientX - drag.x) / window.innerWidth) * 100;
    const dy = ((e.clientY - drag.y) / window.innerHeight) * 100;
    setPipPosition({
      x: Math.min(Math.max(drag.px + dx, 2), 85),
      y: Math.min(Math.max(drag.py + dy, 5), 90),
    });
  };

  return (
    <div className="min-h-screen font-sans flex flex-col justify-between">
      {/* HEADER */}
      <header className="sticky top-0 z-40 backdrop-blur-md border-b transition-colors bg-white/90 border-gray-200 dark:bg-[#0B0F19]/90 dark:border-slate-800 py-4 px-6 md:px-12 flex justify-between items-center">
        <button className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-9 h-9 rounded-xl bg-[#1C2D5A] border border-[#E25C1D]/20 flex items-center justify-center shadow-lg shadow-[#1C2D5A]/30">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="#E25C1D" className="w-5 h-5">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9s2.015-9 4.5-9m0 18c-1.18 0-2.053-.94-2.28-2.191M15.5 15.5c0 1.1-.9 2-2 2h-3c-1.1 0-2-.9-2-2"
              />
            </svg>
          </div>
          <span className="font-extrabold text-xl tracking-tight inline-flex items-center">
            <span className="text-[#E25C1D]">U</span>
            <span className="text-[#1C2D5A] dark:text-slate-100">NE</span>
            <span className="relative inline-block font-extrabold select-none">
              <span className="text-[#1C2D5A] dark:text-slate-100">V</span>
              <span className="absolute top-0 left-0 text-[#E25C1D]" style={{ clipPath: 'inset(0 0 0 50%)' }}>V</span>
            </span>
            <span className="ml-1 text-[10px] font-bold tracking-widest text-[#E25C1D] uppercase border border-[#E25C1D]/30 px-1.5 py-0.5 rounded-md align-middle">
              AI
            </span>
          </span>
        </button>

        <nav className="hidden md:flex items-center gap-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `font-semibold text-sm transition-all py-1.5 px-3.5 rounded-xl ${
                  isActive
                    ? 'bg-[#E25C1D]/10 text-[#E25C1D] font-bold'
                    : 'text-[#5B6B6B] hover:text-[#E25C1D] hover:bg-gray-200/50 dark:text-slate-300 dark:hover:bg-slate-800/20'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <WsChip connected={chat.wsConnected} />
          <button
            onClick={toggle}
            className="p-2 rounded-xl transition-all bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-orange-950/40 dark:text-[#E25C1D] dark:border dark:border-orange-500/10"
            title="Cambiar tema"
          >
            {isDark ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-11.314l.707.707m11.314 11.314l.707.707M12 17a5 5 0 110-10 5 5 0 010 10z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* SCREEN CONTENT */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 flex flex-col justify-center items-center relative">
        <Outlet />
      </main>

      {/* FLOATING PiP */}
      {pipVisible && (
        <div
          style={{ left: `${pipPosition.x}%`, top: `${pipPosition.y}%` }}
          onMouseMove={onPipDragMove}
          onMouseUp={() => setDrag(null)}
          onMouseLeave={() => setDrag(null)}
          className="fixed w-64 p-3 rounded-2xl shadow-2xl backdrop-blur-md bg-slate-900/95 border border-[#E25C1D]/30 select-none z-50 cursor-grab flex items-stretch gap-2"
        >
          <div
            onMouseDown={(e) => setDrag({ x: e.clientX, y: e.clientY, px: pipPosition.x, py: pipPosition.y })}
            className="flex flex-col justify-center gap-1 cursor-grabbing p-1 text-[#E25C1D]"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-[#E25C1D]"></div>
            <div className="w-1.5 h-1.5 rounded-full bg-[#E25C1D]"></div>
            <div className="w-1.5 h-1.5 rounded-full bg-[#E25C1D]"></div>
          </div>
          <div className="flex-1 min-w-0 relative">
            <CameraFeed
              enabled={camera.cameraOn}
              nonce={camera.feedNonce}
              errorLabel="Cámara no disponible"
              className="w-full h-36 rounded-xl border border-slate-800 pointer-events-none"
              imgClassName="w-full h-full object-cover pointer-events-none"
            />
            <button
              onClick={() => navigate('/assistant')}
              className="absolute top-1 right-1 p-1.5 bg-slate-900/80 hover:bg-[#E25C1D] text-white rounded-lg text-xs border border-slate-700 hover:border-[#E25C1D] transition-colors"
              title="Maximizar al asistente"
            >
              ⛶
            </button>
          </div>
        </div>
      )}

      {/* MOBILE NAV */}
      <div className="md:hidden sticky bottom-0 z-40 border-t flex justify-around items-center py-3.5 backdrop-blur-md transition-colors bg-white/95 border-gray-200 text-[#1C2D5A] dark:bg-[#0B0F19]/95 dark:border-slate-800 dark:text-white">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 text-[10px] font-bold ${
                isActive ? 'text-[#E25C1D]' : 'text-[#5B6B6B] dark:text-slate-400'
              }`
            }
          >
            {item.shortLabel ?? item.label}
          </NavLink>
        ))}
      </div>
    </div>
  );
}
