import type { ReactNode } from 'react';

/**
 * Palabra destacada de los titulares ("HoloMind", "UNEV"): Montserrat ExtraBold
 * itálica con el degradado recortado al glifo (nodo 30:1847).
 *
 * `onCream` usa la variante que arranca en naranja, porque el tramo blanco inicial
 * del degradado original es invisible sobre el fondo crema.
 */
export function Wordmark({
  children,
  onCream = false,
}: {
  children: ReactNode;
  onCream?: boolean;
}) {
  return (
    <span
      className={`font-extrabold italic ${
        onCream ? 'wordmark-gradient-on-cream' : 'wordmark-gradient'
      }`}
    >
      {children}
    </span>
  );
}
