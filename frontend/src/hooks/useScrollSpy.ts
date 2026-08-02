import { useEffect, useState } from 'react';

/** Debe coincidir con `HEADER_SCROLL_OFFSET` en ScreenHero.tsx: la sección
 *  "activa" es la última cuyo borde superior ya cruzó la cabecera sticky. */
const HEADER_OFFSET = 132;

/**
 * Observa qué sección de anclas está activa bajo la cabecera sticky, para
 * resaltar el enlace correspondiente del nav (scrollspy) en la landing de una
 * sola página.
 *
 * Usa la posición de scroll directamente (no solo IntersectionObserver): con un
 * salto de scroll grande — una rueda de ratón rápida, `scrollIntoView` desde un
 * clic de nav — es posible que, por un instante, NINGUNA sección esté
 * intersectando la región reducida que usaría un IO con `rootMargin` negativo, y
 * ese instante nunca se corrige porque no llega un evento de intersección
 * nuevo. Comprobar directamente qué sección cruzó la cabecera evita ese hueco.
 */
export function useScrollSpy(ids: readonly string[]): string | undefined {
  const [activeId, setActiveId] = useState<string | undefined>(ids[0]);

  useEffect(() => {
    let ticking = false;

    const recompute = () => {
      ticking = false;
      let current: string | undefined;
      for (const id of ids) {
        const el = document.getElementById(id);
        if (!el) continue;
        if (el.getBoundingClientRect().top <= HEADER_OFFSET + 1) {
          current = id;
        }
      }
      setActiveId(current ?? ids[0]);
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(recompute);
    };

    recompute();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
    // `ids` debe ser una constante estable en el caller (ver LandingScreen) — si
    // cambia de referencia en cada render, este efecto se reengancharía sin
    // necesidad.
  }, [ids]);

  return activeId;
}
