import type { ReactNode } from 'react';
import { CARD, GLASS, SECTION_TITLE } from '../../theme';
import { SurfaceProvider } from './SurfaceProvider';
import { useSurface } from './surfaceContext';

interface CardProps {
  children: ReactNode;
  /** Use inside a masonry `columns-*` container (break-inside-avoid). */
  masonry?: boolean;
  className?: string;
}

/**
 * Tarjeta neutra sobre fondo crema: rgba(0,0,0,0.05) y radio 30px (nodo 53:584).
 * `masonry` mantiene el guard de salto de columna que ya usaba Configuración.
 *
 * Sobre una superficie oscura (malla o navy) cambia sola a la variante de cristal,
 * de modo que un bloque como el panel del holograma se adapta solo envolviéndolo en
 * un `SurfaceProvider tone="glass"` — sin tocar cada tarjeta anidada.
 */
export function Card({ children, masonry = false, className = '' }: CardProps) {
  const glass = useSurface() === 'glass';
  return (
    <div
      className={`${glass ? GLASS : CARD} p-8 space-y-4 ${
        masonry ? 'mb-6 inline-block w-full break-inside-avoid' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Tarjeta con el degradado naranja→navy de INFO. UNEV (nodo 48:334).
 *
 * Su contenido va sobre fondo oscuro, así que los campos de dentro deben usar
 * `INPUT_GLASS` en vez de `INPUT` — con `INPUT` el texto quedaría negro sobre navy.
 */
export function GradientCard({ children, masonry = false, className = '' }: CardProps) {
  return (
    <SurfaceProvider tone="glass">
      <div
        className={`rounded-[30px] bg-[linear-gradient(135deg,#FF7208_0%,#CC5E15_38%,#2E3A70_100%)]
                    p-8 space-y-4 text-white shadow-[0_8px_32px_rgba(0,0,0,0.18)] ${
                      masonry ? 'mb-6 inline-block w-full break-inside-avoid' : ''
                    } ${className}`}
      >
        {children}
      </div>
    </SurfaceProvider>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className={SECTION_TITLE}>{children}</h3>;
}
