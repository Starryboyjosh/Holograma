/**
 * Elementos de navegación del diseño, en su orden (nodo 79:18).
 *
 * Viven en su propio módulo y no en `HolomindHeader.tsx` porque el header y el
 * footer los comparten, y un archivo de componentes que también exporta constantes
 * rompe el fast-refresh de Vite.
 *
 * El rediseño en una sola página convierte "Hablar" / "Entrenar Visión" /
 * "Información UNEV" en anclas de scroll dentro de `/` (kind: 'anchor'), mientras
 * que "Configuración" sigue siendo una ruta real (kind: 'route') — es la única
 * sección que el diseño mantiene fuera del recorrido de una sola página.
 */
export type NavItem =
  | { kind: 'anchor'; id: string; label: string }
  | { kind: 'route'; to: string; label: string };

export const NAV_ITEMS: NavItem[] = [
  { kind: 'anchor', id: 'hablar', label: 'Hablar' },
  { kind: 'anchor', id: 'entrenar', label: 'Entrenar Visión' },
  { kind: 'anchor', id: 'info', label: 'Información UNEV' },
  { kind: 'route', to: '/settings', label: 'Configuración' },
];
