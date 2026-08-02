import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { StickyHeader } from '../components/holomind/StickyHeader';
import { InicioSection } from './sections/InicioSection';
import { HablarSection } from './sections/HablarSection';
import { EntrenarSection } from './sections/EntrenarSection';
import { InfoSection } from './sections/InfoSection';
import { useScrollSpy } from '../hooks/useScrollSpy';

const SECTION_IDS = ['inicio', 'hablar', 'entrenar', 'info'] as const;
type SectionId = (typeof SECTION_IDS)[number];

// Mismo criterio que `ScreenHero`'s `backdrop` en cada sección: tone 'light' es
// texto blanco (sobre malla/navy), 'dark' es tinta oscura (sobre crema).
const SECTION_TONE: Record<SectionId, 'light' | 'dark'> = {
  inicio: 'light',
  hablar: 'dark',
  entrenar: 'light',
  info: 'dark',
};

/**
 * Landing de una sola página: fusiona INICIO + HABLAR + ENTRENAR VISIÓN +
 * INFO. UNEV (nodos 10:53/63:2, 30:1729, 44:220, 48:334) en un único recorrido
 * de scroll, con una cabecera compartida y sticky en vez de una por pantalla
 * (ver `StickyHeader`, que reemplaza el `HolomindHeader` que cada `ScreenHero`
 * renderizaba antes). CONFIGURACIÓN queda fuera — ver `App.tsx` — porque el
 * diseño la trata como pantalla aparte, no como un frame más del recorrido.
 *
 * El pie (nodo 63:91) NO se renderiza aquí: `AppShell.tsx` ya lo monta una vez
 * para todas las rutas (landing y Configuración incluidas). Renderizarlo
 * también aquí duplicaba el footer solo en "/".
 */
export function LandingScreen() {
  const location = useLocation();
  const activeId = useScrollSpy(SECTION_IDS);
  const tone = SECTION_TONE[(activeId as SectionId) ?? 'inicio'];

  // El nav y el pie navegan aquí con `navigate({ pathname: '/', hash: '#id' })`
  // (ver HolomindHeader/HolomindFooter). Este efecto es el único lugar que
  // traduce ese hash en un desplazamiento real, así que funciona igual si
  // LandingScreen ya estaba montada (solo cambia el hash) que si acaba de montar
  // viniendo de Configuración.
  useEffect(() => {
    if (!location.hash) return;
    const id = location.hash.slice(1);
    document.getElementById(id)?.scrollIntoView();
  }, [location.hash]);

  return (
    <>
      <StickyHeader tone={tone} activeAnchorId={activeId} />
      <InicioSection />
      <HablarSection />
      <EntrenarSection />
      <InfoSection />
    </>
  );
}
