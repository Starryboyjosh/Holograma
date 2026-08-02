import { useSession } from '../../context/SessionContext';
import { HolomindHeader } from './HolomindHeader';

/**
 * Cabecera única y fija de la landing de una sola página.
 *
 * Antes cada pantalla traía su propia cabecera vía `ScreenHero` (ver ese archivo:
 * ya no la renderiza). Fusionar INICIO + HABLAR + ENTRENAR VISIÓN + INFO. UNEV en
 * un solo recorrido de scroll exige UNA cabecera compartida en vez de cuatro
 * landmarks de navegación duplicados.
 *
 * Va en `position: sticky` sobre una barra de cristal translúcida (mismo lenguaje
 * que `GLASS` en theme.ts) en vez de intentar reproducir exactamente el fondo de
 * la sección que quede detrás en cada momento del scroll: así se lee igual de bien
 * sobre la malla naranja, el navy o el crema sin recomponer el backdrop de cada
 * sección por debajo de ella.
 */
export function StickyHeader({
  tone,
  activeAnchorId,
}: {
  tone: 'light' | 'dark';
  activeAnchorId?: string;
}) {
  const { chat } = useSession();

  return (
    <div
      className={`sticky top-0 z-50 backdrop-blur-xl transition-colors duration-300 ${
        tone === 'light'
          ? 'border-b border-white/10 bg-black/10'
          : 'border-b border-black/5 bg-white/50'
      }`}
    >
      <HolomindHeader connected={chat.wsConnected} tone={tone} activeAnchorId={activeAnchorId} />
    </div>
  );
}
