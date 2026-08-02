import { createContext, useContext } from 'react';

/**
 * Tono de la superficie que contiene un campo.
 *
 * El diseño usa dos fondos incompatibles: crema (texto negro) y las superficies
 * oscuras — malla, navy y las tarjetas con degradado (texto blanco). Un campo tiene
 * que saber sobre cuál está, o el texto queda ilegible. Se resuelve por contexto en
 * vez de un prop `tone` en cada `<Field>` porque INFO. UNEV tiene ~25 campos dentro
 * de una sola tarjeta.
 *
 * El contexto y el hook viven aparte del provider para no romper el fast-refresh.
 */
export type SurfaceTone = 'cream' | 'glass';

export const SurfaceCtx = createContext<SurfaceTone>('cream');

export function useSurface(): SurfaceTone {
  return useContext(SurfaceCtx);
}
