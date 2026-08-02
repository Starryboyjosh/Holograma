import { useState } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useSession } from '../context/SessionContext';
import { useSectionVisible } from '../hooks/useSectionVisible';
import { CameraFeed } from './CameraFeed';
import { NAV_ITEMS } from './holomind/navItems';
import { HolomindFooter } from './holomind/HolomindFooter';

/**
 * Marco de la aplicación según el diseño Holomind-WEB.
 *
 * La cabecera NO vive aquí: en la landing de una sola página la aporta
 * `StickyHeader` (montada por `LandingScreen`), y Configuración trae la suya
 * propia — ver esos archivos. El shell se queda con lo que sí es global: el pie,
 * el PiP flotante y el nav móvil.
 */
export function AppShell() {
  const { camera } = useSession();
  const navigate = useNavigate();

  // Floating PiP — solo si la cámara está encendida y la sección Hablar (que ya
  // trae su propio panel de cámara a tamaño completo) no está en pantalla. Antes
  // esto comparaba la ruta (`pathname !== '/assistant'`); esa ruta ya no existe —
  // Hablar es una sección anclada dentro de "/", así que se detecta con
  // IntersectionObserver en vez de con el pathname. Drag es un capricho de
  // navegador; en Tauri se prefiere la ventana de cámara desprendible real.
  const [pipPosition, setPipPosition] = useState({ x: 74, y: 72 });
  const [drag, setDrag] = useState<{ x: number; y: number; px: number; py: number } | null>(null);
  const hablarVisible = useSectionVisible('hablar');
  const pipVisible = camera.cameraOn && !hablarVisible;

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
    <div className="flex min-h-screen flex-col bg-cream font-sans text-ink">
      <main className="flex-1">
        <Outlet />
      </main>

      <HolomindFooter />

      {/* FLOATING PiP */}
      {pipVisible && (
        <div
          style={{ left: `${pipPosition.x}%`, top: `${pipPosition.y}%` }}
          onMouseMove={onPipDragMove}
          onMouseUp={() => setDrag(null)}
          onMouseLeave={() => setDrag(null)}
          className="fixed z-50 hidden w-64 cursor-grab select-none items-stretch gap-2 rounded-[30px] border border-orange/30 bg-navy/95 p-3 shadow-2xl backdrop-blur-md md:flex"
        >
          <div
            onMouseDown={(e) =>
              setDrag({ x: e.clientX, y: e.clientY, px: pipPosition.x, py: pipPosition.y })
            }
            className="flex cursor-grabbing flex-col justify-center gap-1 p-1 text-orange"
          >
            <div className="h-1.5 w-1.5 rounded-full bg-orange"></div>
            <div className="h-1.5 w-1.5 rounded-full bg-orange"></div>
            <div className="h-1.5 w-1.5 rounded-full bg-orange"></div>
          </div>
          <div className="relative min-w-0 flex-1">
            <CameraFeed
              enabled={camera.cameraOn}
              nonce={camera.feedNonce}
              errorLabel="Cámara no disponible"
              className="pointer-events-none h-36 w-full rounded-[20px] border border-white/10"
              imgClassName="w-full h-full object-cover pointer-events-none"
            />
            <button
              onClick={() => navigate({ pathname: '/', hash: '#hablar' })}
              className="absolute right-1 top-1 rounded-lg border border-white/20 bg-navy/80 p-1.5 text-xs text-white transition-colors hover:border-orange hover:bg-orange"
              title="Maximizar al asistente"
            >
              ⛶
            </button>
          </div>
        </div>
      )}

      {/* MOBILE NAV — el diseño solo especifica escritorio. En móvil se conserva la
          barra inferior que ya existía, revestida con los tokens nuevos, porque
          la pastilla de nav de escritorio no cabe en un viewport estrecho. */}
      <div className="sticky bottom-0 z-40 flex items-center justify-around border-t border-black/10 bg-cream/95 py-3.5 backdrop-blur-md md:hidden">
        {NAV_ITEMS.map((item) =>
          item.kind === 'route' ? (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 text-center text-[10px] font-bold ${
                  isActive ? 'text-orange' : 'text-muted'
                }`
              }
            >
              {item.label}
            </NavLink>
          ) : (
            <button
              key={item.id}
              type="button"
              onClick={() => navigate({ pathname: '/', hash: `#${item.id}` })}
              className="flex flex-col items-center gap-1 text-center text-[10px] font-bold text-muted"
            >
              {item.label}
            </button>
          ),
        )}
      </div>
    </div>
  );
}
